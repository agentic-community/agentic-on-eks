import os
import json
import logging
import asyncio
import boto3
import datetime
import math
from typing import Optional, Dict, Any, List

SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hr_agent")

# CrewAI imports
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from crewai.memory.external.external_memory import ExternalMemory

# MCP imports - wrapped in try/except to handle case when packages are not available
try:
    from mcp import StdioServerParameters
    from mcpadapt.core import MCPAdapt
    from mcpadapt.crewai_adapter import CrewAIAdapter
    mcp_available = True
    logger.info("MCP packages successfully imported")
except ImportError:
    logger.warning("MCP packages not available, will continue without MCP tools")
    mcp_available = False

# Import utilities for database operations
from utils import get_db_connection, close_db_connection, init_db, insert_sample_data, load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hr_agent")

# Load environment variables
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "./mcp_server")
PUBLIC_HOLIDAY_SERVER_FNAME = os.getenv("PUBLIC_HOLIDAY_SERVER_FNAME", "nager_mcp_server.py")
CONFIG_FPATH = os.getenv("CONFIG_PATH", "./config.yaml")

# Check if Mem0 is available (optional)
mem_api_key = os.getenv("MEM0_API_KEY")
mem0_available = False

# Only try to import Mem0 if the API key is set
if mem_api_key:
    try:
        from mem0ai import MemoryClient
        mem0_client = MemoryClient()
        mem0_available = True
        logger.info("Mem0 client initialized successfully")
    except ImportError:
        logger.warning("Mem0ai package not available, continuing without external memory")
        mem0_available = False
else:
    logger.info("MEM0_API_KEY not set, continuing without external memory")

# Initialize AWS Bedrock client for LLM
def get_bedrock_client():
    """Initialize the AWS Bedrock client"""
    aws_region = os.getenv("AWS_REGION", "us-west-2")
    logger.info(f"Using AWS region: {aws_region}")
    return boto3.client(service_name='bedrock-runtime', region_name=aws_region)

def initialize_database():
    """Initialize the database and insert sample data if needed"""
    try:
        # Initialize the database schema
        init_db()
        
        # Insert sample data
        conn = get_db_connection()
        insert_sample_data(conn, num_employees=30)
        close_db_connection(conn)
        
        logger.info("Database initialized successfully with sample data")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Define the tools that will be used by the agent
@tool("EmployeeDirectoryService")
def employee_directory_service(employee_id: str) -> dict:
    """
    Fetch an existing employee in the local SQLite database.

    Args:
        employee_id (str): Unique identifier for the employee.

    Returns:
        dict: {
            "employee_id": str,
            "name": str,
            "start_date": str (ISO YYYY-MM-DD)
        }

    Raises:
        ValueError: If `employee_id` is empty or if the user is not registered.
        sqlite3.Error: On any database error.
    """
    # 1) Validate input
    if not employee_id or not employee_id.strip():
        logger.error("Empty employee_id provided")
        raise ValueError("Employee ID must be a non-empty string.")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT employee_id, name, start_date FROM employees WHERE employee_id = ?",
            (employee_id,)
        )
        row = cur.fetchone()

        if row:
            logger.info("Found existing employee: %s", employee_id)
            return {
                "employee_id": row[0],
                "name": row[1],
                "start_date": row[2],
            }
        else:
            logger.warning("Employee %s not found", employee_id)
            # Instead of auto‐onboarding, we signal an error:
            raise ValueError(f"Employee '{employee_id}' is not registered.")

    finally:
        close_db_connection(conn)

@tool("LeavePolicyService")
def leave_policy_service(employee_id: str) -> dict:
    """
    Fetch the leave policy for the given employee from the database.
    If no specific assignment is found, then return the company default policy.
    Args:
        employee_id (str): Unique identifier for the employee.
    Returns:
        dict: {
            "employee_id": str,
            "policy_name": str,
            "leave_days": int
        }
    """
    # connect to the database using the utils function
    conn = get_db_connection()
    logger.info(f"Connected to the database: {conn}")
    try:
        cur = conn.cursor()
        # Now, we will find the employee's leave policy based on the hiring date and the 
        # effective ranges
        cur.execute("""
                    SELECT p.policy_name, p.annual_days, p.max_carryover_days, p.probation_period_days
                    FROM leave_policies p
                    JOIN employee_policies ep
                    ON p.policy_id = ep.policy_id
                    WHERE ep.employee_id = ?
                    AND DATE('now') BETWEEN ep.effective_from AND ep.effective_to
                    ORDER BY ep.effective_from DESC
                    LIMIT 1
                    """, (employee_id,))
        row = cur.fetchone()
        if row:
            name, annual, carry, probation = row
        else:
            # Fallback to the policy with the latest effective_from date
            cur.execute("""
                SELECT policy_name, annual_days, max_carryover_days, probation_period_days
                FROM leave_policies
                ORDER BY effective_from DESC
                LIMIT 1
            """)
            name, annual, carry, probation = cur.fetchone()

        return {
            "policy_name": name,
            "annual_days": annual,
            "max_carryover": carry,
            "probation_days": probation
        }
    finally:
        close_db_connection(conn)

@tool("RemainingVacationDays")
def remaining_vacation_days(employee_id: str, policy: dict) -> dict:
    """
    Calculate remaining vacation days based on:
      - accrued_days + carryover - used_days
      - if no record exists for this year, start at policy['annual_days']
    Then round up to the next integer.

    Args:
        employee_id (str): Unique identifier for the employee.
        policy (dict): Leave policy details for the employee.

    Returns:
        dict: {"remainingDays": int}

    Raises:
        sqlite3.Error: On any database error.
    """
    year = datetime.date.today().year
    logger.info("Calculating remaining vacation days for employee_id=%s, year=%d",
                employee_id, year)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT accrued_days, used_days, carryover
              FROM leave_balances
             WHERE employee_id = ? AND year = ?
            """,
            (employee_id, year)
        )
        row = cur.fetchone()

        if row:
            accrued, used, carry = row
            raw_remaining = accrued + carry - used
            logger.info(
                "Raw remaining = accrued + carryover - used = %s + %s - %s = %s",
                accrued, carry, used, raw_remaining
            )
        else:
            raw_remaining = policy["annual_days"]
            logger.info(
                "No record found; defaulting raw_remaining to policy['annual_days'] = %s",
                raw_remaining
            )

        # Round up to the nearest integer
        rounded = math.ceil(raw_remaining)
        logger.info("Rounded up remainingDays = math.ceil(%s) = %s", raw_remaining, rounded)

        return {"remainingDays": rounded}

    finally:
        close_db_connection(conn)

def create_hr_agent():
    """Create and configure the HR agent with all necessary tools"""
    # Initialize the database
    initialize_database()
    
    # Load configuration
    try:
        if os.path.exists(CONFIG_FPATH):
            config_data = load_config(CONFIG_FPATH)
            logger.info(f"Loaded config from: {CONFIG_FPATH}")
            hr_agent_model_id = config_data['model_information']['crewAI_model_info'].get('model_id')
            inference_parameters = config_data['model_information']['crewAI_model_info'].get('inference_parameters')
        else:
            logger.warning(f"Config file not found at {CONFIG_FPATH}. Using default values.")
            hr_agent_model_id = os.getenv("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
            inference_parameters = {
                "temperature": 0.7,
                "max_tokens": 4096,
                "top_p": 0.9
            }
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        hr_agent_model_id = os.getenv("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        inference_parameters = {
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 0.9
        }
    
    logger.info(f"Using model ID: {hr_agent_model_id}")
    logger.info(f"Using inference parameters: {json.dumps(inference_parameters, indent=2)}")
    
    # Set up LLM
    llm_instance = LLM(
        model=hr_agent_model_id,
        temperature=inference_parameters.get("temperature", 0.7),
        max_tokens=inference_parameters.get("max_tokens", 4096),
        top_p=inference_parameters.get("top_p", 0.9)
    )
    
    # Set up MCPAdapt to connect to the public holiday MCP server
    public_holiday_tools = []
    
    if mcp_available:
        try:
            # Only attempt to create the MCP adapter if the server file exists
            server_path = os.path.join(MCP_SERVER_PATH, PUBLIC_HOLIDAY_SERVER_FNAME)
            if os.path.exists(server_path):
                # We'll use the requests library directly to call the Nager.Date API
                # This is more reliable than trying to use the MCP server
                import requests
                
                # Define the function that will be wrapped as a tool
                def get_public_holidays_func(year: int = 2025, country_code: str = "US"):
                    """
                    Get public holidays for a specific year and country using the Nager.Date API.
                    
                    Args:
                        year: The year to get holidays for (default: 2025)
                        country_code: The ISO country code (default: US)
                        
                    Returns:
                        dict: Information about public holidays
                    """
                    try:
                        # Call the Nager.Date API directly
                        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        
                        # Process the response
                        holidays = response.json()
                        count = len(holidays)
                        
                        # Build a summary of the holidays
                        entries = [f"{item['date']} ({item['localName']})" for item in holidays]
                        summary = f"{count} holidays: " + ", ".join(entries)
                        
                        logger.info(f"Successfully retrieved {count} public holidays for {country_code} in {year}")
                        return {"summary": summary, "count": count, "holidays": holidays}
                    except Exception as e:
                        logger.error(f"Error getting public holidays: {str(e)}")
                        return {"error": str(e), "summary": "Unable to retrieve public holidays", "count": 0}
                
                # Create a proper CrewAI tool
                public_holiday_tool = Tool(
                    name="GetPublicHolidays",
                    description="Get public holidays for a specific year and country. Use this to find out how many public holidays there are in a given year and country.",
                    func=get_public_holidays_func
                )
                
                # Add the tool to our list
                public_holiday_tools = [public_holiday_tool]
                logger.info(f"Successfully initialized public holiday tool")
            else:
                logger.warning(f"MCP server file not found at {server_path}. Public holiday information will not be available.")
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {str(e)}")
            logger.warning("Public holiday information will not be available.")
    else:
        logger.warning("MCP not available. Public holiday information will not be available.")
    
    # Define the HR agent with all tools
    hr_agent = Agent(
        role="HR Specialist",
        goal="Manage employee leave and vacation tracking accurately and efficiently",
        backstory=(
            "You are a seasoned HR professional with 10+ years of experience "
            "in workforce planning and benefits administration."
        ),
        max_iter=5,
        max_retry_limit=2,
        tools=[
            employee_directory_service,
            leave_policy_service,
            remaining_vacation_days,
            *public_holiday_tools,  # Add the holiday API tools if available
        ],
        verbose=True,
        llm=llm_instance,
    )
    
    return hr_agent

def _invoke(query: str, agent: Agent, employee_id: Optional[str] = None, user_id: str = "default-user"):
    """Process a user query using the HR agent"""
    logger.info(f"Processing query: {query} for employee_id: {employee_id}")
    
    # Create the HR agent
    hr_agent = agent
    
    # Prepare the task description
    task_description = f"""
    Follow these steps carefully to answer the user's query:
    
    1. Use the employee_directory_service tool to fetch the employee information
    2. Use the leave_policy_service tool to get the leave policy for the employee
    3. Use the remaining_vacation_days tool to calculate the remaining vacation days
    4. If the query is about public holidays or if you need to calculate vacation days accounting for holidays:
       - Use the GetPublicHolidays tool to get public holidays for the relevant year and country
       - The GetPublicHolidays tool takes parameters: year (e.g., 2024, 2025) and country_code (e.g., "US")
    
    If the user is not registered, then use the employee_directory_service tool and then stop. Do not execute further.
    
    When providing the final answer, make sure to include the following:
    - The employee's name
    - The employee's start date
    - The leave policy name
    - The number of vacation days remaining
    - The public holidays for the year (if available)
    - The number of vacation days remaining after accounting for public holidays (if available)

    Here is the query: '{query}'
    """
    
    if employee_id:
        task_description += f"\n\nThe employee ID is: {employee_id}"
    
    # Define the task
    hr_agent_task = Task(
        description=task_description,
        expected_output="Answer to the user's query about the number of vacation days remaining for the employee.",
        agent=hr_agent,
        output_format="string"
    )
    
    # Create the crew
    external_memory = None
    
    # Only try to use Mem0 if it's available
    if mem0_available and mem_api_key:
        try:
            external_memory = ExternalMemory(
                embedder_config={"provider": "mem0", "config": {"user_id": user_id}}
            )
            logger.info(f"Initialized external memory for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize external memory: {str(e)}")
            logger.info("Continuing without external memory")
    
    crew = Crew(
        agents=[hr_agent],
        tasks=[hr_agent_task],
        verbose=True,
        external_memory=external_memory,
        process=Process.sequential
    )
    
    # Run the crew
    try:
        result = crew.kickoff(inputs={"query": query})
        logger.info("Successfully processed query")
        
        # Format the response in the desired format
        if hasattr(result, 'raw'):
            formatted_result = f"# Agent: HR Specialist\n## Final Answer: \n{result.raw}"
        elif isinstance(result, dict) and 'raw' in result:
            formatted_result = f"# Agent: HR Specialist\n## Final Answer: \n{result['raw']}"
        else:
            formatted_result = f"# Agent: HR Specialist\n## Final Answer: \n{str(result)}"
            
        return formatted_result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        # Return a formatted error message
        return f"# Agent: HR Specialist\n## Final Answer: \nError processing your request: {str(e)}"
    
class HRAgent:
    def __init__(self):
        self.agent = None

    def invoke(self, query: str, employee_id: Optional[str] = None, user_id: str = "default-user"):
        """Process a user query using the HR agent"""
        if not self.agent:
            self.agent = create_hr_agent()

        response = _invoke(query, self.agent, employee_id, user_id)
        return response
