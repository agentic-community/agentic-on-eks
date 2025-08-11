#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Finance Agent for processing financial queries using LangGraph."""

import os
import json
import logging
import sqlite3
import pandas as pd
import boto3
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Annotated
from typing_extensions import TypedDict

# LLM imports
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, MessagesState, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

# LangSmith tracing import - this enables automatic tracing when environment variables are set
import langsmith

# Financial data tools
import yfinance as yf
import pandas as pd
import numpy as np

SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if Mem0 is available
try:
    from mem0.client import Mem0Client
    mem0_available = True
    logger.info("Mem0 client is available")
except ImportError:
    mem0_available = False
    logger.info("Mem0 client is not available")

# Import global configuration
from globals import (
    BEDROCK_MODEL_ID,
    AWS_REGION,
    MODEL_PARAMS,
    FINANCE_AGENT_CONFIG,
    FINANCE_SYSTEM_PROMPT
)

# Load environment variables
mem_api_key = os.getenv("MEM0_API_KEY")

# Database setup
def setup_database():
    """Set up the SQLite database with employee data."""
    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    
    # Create employee table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        name TEXT,
        start_date TEXT,
        hourly_rate REAL,
        performance TEXT
    )
    ''')
    
    # Insert sample data if table is empty
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        employees = [
            ('EMP0001', 'Jane Smith', '2020-01-15', 35.00, 'Excellent'),
            ('EMP0002', 'John Doe', '2019-05-20', 42.50, 'Good'),
            ('EMP0003', 'Alice Johnson', '2021-03-10', 28.75, 'Average'),
            ('EMP0004', 'Bob Williams', '2018-11-05', 50.00, 'Excellent'),
            ('EMP0005', 'Carol Davis', '2022-02-28', 31.25, 'Good')
        ]
        cursor.executemany('INSERT INTO employees VALUES (?, ?, ?, ?, ?)', employees)
    
    conn.commit()
    conn.close()

# Initialize database
setup_database()

# State definition for employee data
class HRState(TypedDict):
    """This represents the HR context for salary and leave calculations.

    Attributes:
        employee_id (str): The ID of the employee.
        days_off (int): The number of days off taken by the employee.
        current_salary (float): The current salary of the employee.
        proposed_new_salary (float): The proposed new salary for the employee.
        annual_salary (float): The annual salary of the employee.
        deduction (float): The deduction amount for the employee.
        raise_approved (bool): Whether the raise has been approved or not.
    """
    employee_id: Optional[str] = None
    days_off: Optional[int] = None
    current_salary: Optional[float] = None
    proposed_new_salary: Optional[float] = None
    annual_salary: Optional[float] = None
    deduction: Optional[float] = None
    raise_approved: Optional[bool] = None

# Helper functions for employee data
def get_performance_service(employee_id: str) -> Dict[str, Any]:
    """Get performance data for an employee."""
    try:
        conn = sqlite3.connect('employee.db')
        cursor = conn.cursor()
        cursor.execute("SELECT performance FROM employees WHERE employee_id = ?", (employee_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"employee_id": employee_id, "performance": result[0]}
        else:
            return {"error": f"Employee {employee_id} not found"}
    except Exception as e:
        logger.error(f"Error getting performance for {employee_id}: {str(e)}")
        return {"error": f"Error retrieving performance data: {str(e)}"}

def employee_directory_service(employee_id: str) -> Dict[str, Any]:
    """Fetch core employee info, including hourly_rate and performance.
    
    Returns a dict with keys:
      - employee_id
      - name
      - start_date
      - hourly_rate
      - performance
    """
    try:
        conn = sqlite3.connect('employee.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "employee_id": result[0],
                "name": result[1],
                "start_date": result[2],
                "hourly_rate": result[3],
                "performance": result[4]
            }
        else:
            return {"error": f"Employee {employee_id} not found"}
    except Exception as e:
        logger.error(f"Error getting employee data for {employee_id}: {str(e)}")
        return {"error": f"Error retrieving employee data: {str(e)}"}

# Financial tools
@tool
def calculate_annual_salary(employee_id: str) -> Dict[str, Any]:
    """Calculate the annual salary based on hourly rate.
    
    Args:
        employee_id (str): Represents the employee id provided by the user.
    """
    try:
        employee_data = employee_directory_service(employee_id)
        if "error" in employee_data:
            return employee_data
        
        hourly_rate = employee_data["hourly_rate"]
        annual_salary = hourly_rate * 40 * 52  # 40 hours per week, 52 weeks per year
        
        return {
            "employee_id": employee_id,
            "name": employee_data["name"],
            "hourly_rate": hourly_rate,
            "annual_salary": annual_salary
        }
    except Exception as e:
        logger.error(f"Error calculating annual salary for {employee_id}: {str(e)}")
        return {"error": f"Error calculating annual salary: {str(e)}"}

@tool
def calculate_leave_deduction(employee_id: str, days_off: int) -> Dict[str, Any]:
    """Compute pay deduction for leave days by fetching the employee's hourly rate.
    
    Args:
        employee_id (str): The ID of the employee.
        days_off (int): The number of leave days taken by the employee.
    Returns:
        float: The total deduction for the leave days.
    """
    try:
        employee_data = employee_directory_service(employee_id)
        if "error" in employee_data:
            return employee_data
        
        hourly_rate = employee_data["hourly_rate"]
        hours_per_day = 8  # Assuming 8-hour workday
        total_deduction = hourly_rate * hours_per_day * days_off
        
        return {
            "employee_id": employee_id,
            "name": employee_data["name"],
            "hourly_rate": hourly_rate,
            "days_off": days_off,
            "hours_deducted": hours_per_day * days_off,
            "total_deduction": total_deduction
        }
    except Exception as e:
        logger.error(f"Error calculating leave deduction for {employee_id}: {str(e)}")
        return {"error": f"Error calculating leave deduction: {str(e)}"}

def check_and_approve_raise(state: dict) -> Dict[str, Any]:
    """Human-in-the-loop approval for salary raises.
    
    This function will interrupt the agent flow and wait for human approval
    before proceeding with a raise.
    
    Args:
        state (dict): The current state containing employee information and proposed raise.
    
    Returns:
        dict: Updated state with approval status.
    """
    employee_id = state.get("employee_id")
    current_salary = state.get("current_salary")
    proposed_new_salary = state.get("proposed_new_salary")
    
    if not all([employee_id, current_salary, proposed_new_salary]):
        return {"error": "Missing required information for raise approval"}
    
    # This would interrupt the flow and wait for human approval
    # In this implementation, we'll auto-approve for demonstration
    return {"raise_approved": True}

@tool
def submit_raise_service(employee_id: str, raise_amount: float) -> Dict[str, Any]:
    """Submit a salary raise for the given employee by updating the database.
    
    Args:
        employee_id (str): The ID of the employee.
        raise_amount (float): The dollar amount to increase the employee's salary by.
    Returns:
        dict: {
            "employee_id": str,
            "old_salary": float,
            "new_salary": float,
            "status": "success"
        }
    Raises:
        ValueError: If the employee is not found.
    """
    try:
        # Get current employee data
        employee_data = employee_directory_service(employee_id)
        if "error" in employee_data:
            return employee_data
        
        hourly_rate = employee_data["hourly_rate"]
        new_hourly_rate = hourly_rate + (raise_amount / (40 * 52))  # Convert annual raise to hourly
        
        # Update the database
        conn = sqlite3.connect('employee.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE employees SET hourly_rate = ? WHERE employee_id = ?",
            (new_hourly_rate, employee_id)
        )
        conn.commit()
        conn.close()
        
        # Calculate annual values for reporting
        old_annual = hourly_rate * 40 * 52
        new_annual = new_hourly_rate * 40 * 52
        
        return {
            "employee_id": employee_id,
            "name": employee_data["name"],
            "old_salary": old_annual,
            "new_salary": new_annual,
            "raise_amount": raise_amount,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error submitting raise for {employee_id}: {str(e)}")
        return {"error": f"Error submitting raise: {str(e)}"}

# Define the system prompt to guide the assistant's behavior
primary_assistant_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a payroll finance assistant. Follow these rules exactly when deciding which tool to invoke:

1. If the user asks for an employee's annual salary, invoke:
   `calculate_annual_salary`
   in your answer, explain the calculations thoroughly to reach the response.
   Explain the hourly rate in the final response and how it led to an annual salary calculation.

2. If the user mentions leave days or time off, invoke:
   `calculate_leave_deduction`

3. If the user requests or approves a raise, invoke:
   `submit_raise_service(employee_id, raise_amount)`

4. After calling the tool, read its output and present a concise, human-friendly summary:
   – e.g. "EMP1001's annual salary is $ X.XX"  
   – or "Leave deduction for Y days off is $ Z.ZZ."  
   – or "Raise of $ R.RR submitted successfully (old: $ O.OO → new: $ N.NN)."

Do NOT invent numbers; always use the tool's returned values.  
""".strip()
    ),
    ("placeholder", "{messages}"),
])

# Define the list of tools available to the assistant for finance tasks
finance_tools = [calculate_annual_salary, 
                 calculate_leave_deduction, 
                 submit_raise_service]

# Initialize the Bedrock client
def get_bedrock_client():
    """Initialize the AWS Bedrock client"""
    aws_region = os.getenv("AWS_REGION", AWS_REGION)
    return boto3.client(service_name='bedrock-runtime', region_name=aws_region)

# Create the LLM instance
def get_llm():
    """Initialize the LLM with the specified model ID."""
    model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_MODEL_ID)
    bedrock_client = get_bedrock_client()
    
    llm = ChatBedrockConverse(
        model=model_id,
        temperature=0,
        max_tokens=None,
        client=bedrock_client
    )
    
    return llm

def create_finance_agent():
# Create the finance agent using ReAct pattern
    llm = get_llm()

    # Create a ReAct agent with our tools
    finance_agent = create_react_agent(
        llm,
        tools=finance_tools, 
        prompt=primary_assistant_prompt
    )

    # Create the state graph
    memory = MemorySaver()

    finance_graph = StateGraph(
        MessagesState,  # our wrapped state type
    )

    # Add nodes to the graph
    finance_graph.add_node("finance_agent", finance_agent)
    finance_graph.add_node("calc_annual", calculate_annual_salary)
    finance_graph.add_node("calc_deduction", calculate_leave_deduction)
    finance_graph.add_node("approval", check_and_approve_raise)
    finance_graph.add_node(
        "submit_raise",
        lambda state: {
            "submit_result": submit_raise_service(
                state.employee_id,
                state.current_salary * 0.10
            )
        }
    )

    # Wire up the graph
    finance_graph.add_edge(START, "finance_agent")

    # On approval, go to submit_raise; otherwise end
    finance_graph.add_conditional_edges(
        "approval",
        lambda state: state.raise_approved,
        { True: "submit_raise",
        False: END }
    )

    # Compile the graph
    final_finance_graph = finance_graph.compile(
        checkpointer=memory,
    )
    return final_finance_graph

# Function to process queries through the finance agent
def _invoke(query: str, final_finance_graph) -> Dict[str, Any]:
    """Process a query through the finance agent.
    
    Args:
        query (str): The user's query about financial information.
        
    Returns:
        Dict[str, Any]: The response from the finance agent.
    """
    try:
        logger.info(f"Processing query: {query}")
        
        # Generate a unique thread ID for this conversation
        thread_id = f"finance-{datetime.now().strftime('%Y%m%d%H%M%S')}" 
        
        # Configure the agent with the thread ID
        config = {"configurable": {"thread_id": thread_id}}
        
        # Process the query through the agent graph
        response = final_finance_graph.invoke(
            {"messages": [("user", query)]},
            config
        )
        
        # Extract the last message from the agent
        if response and "messages" in response and response["messages"]:
            last_message = response["messages"][-1]
            if hasattr(last_message, "content"):
                return {"response": last_message.content}
        
        return {"response": "I'm sorry, I couldn't process your request at this time."}
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {"error": f"Error processing query: {str(e)}"}
    
class FinanceAgent:
    def __init__(self):
        self.agent = None

    def invoke(self, query: str):
        """Process a user query using the Finance agent"""
        if not self.agent:
            self.agent = create_finance_agent()

        response = _invoke(query, self.agent)
        
        # Convert response to string format for A2A compatibility
        if isinstance(response, dict):
            if 'response' in response:
                return response['response']
            else:
                return str(response)
        elif isinstance(response, str):
            return response
        else:
            return str(response)


# Main entry point for testing
if __name__ == "__main__":
    # Test the agent
    test_query = "What is the current price of Apple stock and how has it performed over the last month?"
    response = _invoke(test_query)
    print(json.dumps(response, indent=2))
