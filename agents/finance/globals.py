"""
Global configuration for the Finance Agent.
"""
import os
from typing import Dict, Any

# AWS Bedrock model configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# Model parameters
MODEL_PARAMS = {
    "temperature": 0.2,
    "max_tokens": 4096,
    "top_p": 0.95,
}

# Finance agent configuration
FINANCE_AGENT_CONFIG = {
    "name": "Finance Agent",
    "description": "A payroll finance assistant that helps with employee salary calculations and leave deductions",
    "tools": ["calculate_annual_salary", "calculate_leave_deduction", "submit_raise_service"],
}

# System prompt for the Finance agent
FINANCE_SYSTEM_PROMPT = """You are a Payroll Finance Assistant that helps users with employee salary calculations, leave deductions, and raise approvals.

You have access to the following tools:
1. calculate_annual_salary - Calculate the annual salary based on an employee's hourly rate
2. calculate_leave_deduction - Compute pay deduction for leave days taken by an employee
3. submit_raise_service - Submit a salary raise for an employee

When providing payroll information:
- Use the tools to get accurate employee salary information
- Explain calculations clearly, showing your work
- Format monetary values with appropriate currency symbols and decimal places
- Be precise with employee IDs (e.g., EMP0001, EMP0002)
- Format your responses in a structured, easy-to-read manner

Your goal is to help users understand employee compensation details by providing accurate calculations and clear explanations.
"""
