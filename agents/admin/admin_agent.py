#!/usr/bin/env python3
"""
Admin/Supervisor Agent - Routes queries to HR and Finance agents using A2A protocol.
"""

import os
import json
import logging
import asyncio
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

# Latest A2A SDK imports
from a2a.client import A2AClient
from a2a.types import AgentCard, Task, TaskStatus, TextPart, SendMessageRequest, MessageSendParams
import httpx

# LangChain for LLM-based routing
from langchain_aws import ChatBedrockConverse

# LangSmith monitoring setup - only enable when using LangChain operations
import os
# Disable LangChain playground mode to prevent route conflicts
os.environ["LANGCHAIN_DISABLE_PLAYGROUND"] = "true"
# Don't set these globally to avoid LangChain playground conflicts
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_ENDPOINT"] = "http://langsmith-service:8000"
# os.environ["LANGCHAIN_API_KEY"] = "dev-api-key"
# os.environ["LANGCHAIN_PROJECT"] = "agentic-on-eks"

# OAuth client for A2A authentication
from oauth import get_auth_headers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

class AdminAgent:
    """
    Admin/Supervisor Agent that routes queries to HR and Finance agents.
    Acts as both A2A server (for UI) and A2A client (for HR/Finance communication).
    """
    
    def __init__(self):
        self.hr_client = None
        self.finance_client = None
        self.hr_agent_card = None
        self.finance_agent_card = None
        self.llm = None
        self.httpx_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the admin agent with A2A clients for HR and Finance agents."""
        if self._initialized:
            return
            
        logger.info("Initializing Admin Agent...")
        
        # Initialize LLM for routing decisions
        self.llm = self._get_llm()
        
        # Fetch agent cards and create A2A clients
        await self._initialize_agent_clients()
        
        self._initialized = True
        logger.info("Admin Agent initialized successfully")
    
    async def _initialize_agent_clients(self):
        """Fetch agent cards and create A2A clients for HR and Finance agents."""
        try:
            # Initialize httpx client with extended timeout for HR/Finance agent processing
            self.httpx_client = httpx.AsyncClient(timeout=120.0)
            
            # Fetch HR agent card
            hr_host = os.getenv("HR_HOST", "hr-agent-service.default.svc.cluster.local")
            hr_port = int(os.getenv("HR_PORT", "80"))
            self.hr_agent_card = await self._get_agent_card(hr_host, hr_port)
            
            if self.hr_agent_card:
                self.hr_client = A2AClient(
                    httpx_client=self.httpx_client,
                    agent_card=self.hr_agent_card
                )
                logger.info(f"HR A2A client initialized for {hr_host}:{hr_port}")
            else:
                logger.error("Failed to initialize HR A2A client - no agent card")
            
            # Fetch Finance agent card
            finance_host = os.getenv("FINANCE_HOST", "finance-agent-service.default.svc.cluster.local")
            finance_port = int(os.getenv("FINANCE_PORT", "80"))
            self.finance_agent_card = await self._get_agent_card(finance_host, finance_port)
            
            if self.finance_agent_card:
                self.finance_client = A2AClient(
                    httpx_client=self.httpx_client,
                    agent_card=self.finance_agent_card
                )
                logger.info(f"Finance A2A client initialized for {finance_host}:{finance_port}")
            else:
                logger.error("Failed to initialize Finance A2A client - no agent card")
                
        except Exception as e:
            logger.error(f"Error initializing agent clients: {str(e)}")
            raise
    
    async def _get_agent_card(self, host: str, port: int) -> Optional[AgentCard]:
        """Fetch agent card from the specified host and port."""
        import httpx
        
        url = f"http://{host}:{port}/.well-known/agent.json"
        logger.info(f"Fetching agent card from {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                agent_config = response.json()
            
            # Create AgentCard from the response
            agent_card = AgentCard(
                name=agent_config["name"],
                description=agent_config["description"],
                url=agent_config["url"],
                version=agent_config["version"],
                defaultInputModes=agent_config["defaultInputModes"],
                defaultOutputModes=agent_config["defaultOutputModes"],
                capabilities=agent_config["capabilities"],
                skills=agent_config["skills"],
                authentication=agent_config.get("authentication")
            )
            
            logger.info(f"Successfully fetched agent card for {agent_card.name}")
            return agent_card
            
        except Exception as e:
            logger.error(f"Failed to fetch agent card from {url}: {str(e)}")
            return None
    
    def _get_llm(self):
        """Initialize the LLM for routing decisions."""
        # Import LangChain only when needed to avoid playground conflicts
        from langchain_aws import ChatBedrockConverse
        
        model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        aws_region = os.getenv("AWS_REGION", "us-west-2")
        
        # Enable LangSmith tracing only for this LLM instance
        # Use environment variables set by Kubernetes deployment
        os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "agentic-on-eks")
        
        bedrock_client = boto3.client(
            service_name='bedrock-runtime', 
            region_name=aws_region
        )
        
        llm = ChatBedrockConverse(
            model=model_id,
            temperature=0,
            max_tokens=None,
            client=bedrock_client
        )
        
        logger.info(f"LLM initialized with model: {model_id}")
        return llm
    
    def _route_query(self, query: str) -> str:
        """Use LLM to determine which agent should handle the query."""
        try:
            # Build agent descriptions for routing
            agent_descriptions = {
                "HR": "employee information, vacation days, leave policies, public holidays, employee directory, time off",
                "Finance": "salary calculations, pay deductions, raises, financial data, payroll, annual salary"
            }
            
            routing_prompt = f"""
            Analyze the following user query and determine which agent should handle it.
            
            Available agents:
            - HR Agent: Handles {agent_descriptions["HR"]}
            - Finance Agent: Handles {agent_descriptions["Finance"]}
            
            User query: "{query}"
            
            Respond with exactly one word: either "HR" or "Finance"
            """
            
            response = self.llm.invoke(routing_prompt)
            
            # Extract the routing decision
            if hasattr(response, 'content'):
                decision = response.content.strip().upper()
            else:
                decision = str(response).strip().upper()
            
            if decision in ["HR", "FINANCE"]:
                logger.info(f"Query routed to {decision} agent: {query[:50]}...")
                return decision
            else:
                # Default to HR if unclear
                logger.warning(f"Unclear routing decision '{decision}', defaulting to HR")
                return "HR"
                
        except Exception as e:
            logger.error(f"Error in routing decision: {str(e)}")
            # Default to HR on error
            return "HR"
    
    async def process_query(self, query: str, user_id: str = "default-user") -> str:
        """Process a query by routing it to the appropriate agent."""
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Processing query: {query[:100]}...")
        
        try:
            # Route the query
            target_agent = self._route_query(query)
            
            # Select the appropriate client
            if target_agent == "HR":
                client = self.hr_client
                agent_name = "HR Agent"
            else:
                client = self.finance_client
                agent_name = "Finance Agent"
            
            if not client:
                error_msg = f"{agent_name} is not available"
                logger.error(error_msg)
                return f"Error: {error_msg}"
            
            # Create A2A message request
            from a2a.types import Message, Part, Role
            
            message = Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(kind='text', text=query))]
            )
            
            # Create SendMessageRequest
            request = SendMessageRequest(
                id=str(uuid4()),
                method="message/send",
                params=MessageSendParams(message=message)
            )
            
            # Get fresh OAuth headers for this request
            oauth_headers = get_auth_headers()
            if oauth_headers:
                logger.info(f"Forwarding query to {agent_name} with OAuth authentication")
                # Update httpx client headers with fresh OAuth token
                self.httpx_client.headers.update(oauth_headers)
            else:
                logger.warning(f"Forwarding query to {agent_name} without OAuth (token acquisition failed)")
            
            # Send message to the selected agent
            response = await client.send_message(request)
            
            # Extract response content from SendMessageResponse
            if hasattr(response, 'result'):
                result = response.result
                if hasattr(result, 'parts') and result.parts:
                    # Message response
                    part = result.parts[0]
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        content = part.root.text
                        logger.info(f"Received response from {agent_name}: {content[:100]}...")
                        return content
                elif hasattr(result, 'artifacts') and result.artifacts:
                    # Task response with artifacts
                    artifact = result.artifacts[0]
                    if hasattr(artifact, 'parts') and artifact.parts:
                        part = artifact.parts[0]
                        if isinstance(part, dict) and 'text' in part:
                            content = part['text']
                            logger.info(f"Received response from {agent_name}: {content[:100]}...")
                            return content
            
            # Handle dictionary responses (like from Finance agent)
            if isinstance(response, dict):
                if 'response' in response:
                    content = response['response']
                    logger.info(f"Received dictionary response from {agent_name}: {content[:100]}...")
                    return content
                else:
                    # Convert dictionary to readable string
                    content = str(response)
                    logger.info(f"Received dictionary response from {agent_name} (converted): {content[:100]}...")
                    return content
            
            # Handle A2A response objects
            if hasattr(response, 'result') and hasattr(response.result, 'parts'):
                # Try to extract text from the response parts
                try:
                    parts = response.result.parts
                    if parts and hasattr(parts[0], 'root') and hasattr(parts[0].root, 'text'):
                        content = parts[0].root.text
                        logger.info(f"Received A2A response from {agent_name}: {content[:100]}...")
                        return content
                except Exception as e:
                    logger.warning(f"Could not extract text from A2A response: {str(e)}")
            
            # Fallback to string representation
            result = str(response)
            logger.info(f"Received response from {agent_name} (fallback format)")
            return result
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def invoke(self, query: str, user_id: str = "default-user") -> str:
        """Synchronous wrapper for process_query."""
        return asyncio.run(self.process_query(query, user_id))