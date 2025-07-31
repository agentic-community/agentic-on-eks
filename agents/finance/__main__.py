# Define request and response models
import os
import json
import logging
import asyncio
from pydantic import BaseModel
from typing import Optional, Dict, Any
import click
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import OAuth middleware
from common.server.oauth_middleware import configure_oauth_middleware

# [OKTA] Skipped loading Okta environment variables and OAuth config
# try:
#     okta_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".okta.env")
#     if os.path.exists(okta_env_path):
#         with open(okta_env_path) as f:
#             for line in f:
#                 line = line.strip()
#                 if not line or line.startswith("#"):
#                     continue
#                 key, value = line.split("=", 1)
#                 os.environ[key] = value
#         print("Successfully loaded variables from .okta.env")
# except Exception as e:
#     print(f"Error loading .okta.env: {e}")

# def load_oauth_env():
#     """Load OAuth environment variables with proper defaults for Finance agent."""
#     env_vars = {}
#     # ... Okta env logic skipped ...
#     return env_vars

# load_oauth_env()

from a2a.server.apps import A2AStarletteApplication
from finance_agent_taskmanager import FinanceAgentTaskManager
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    OAuth2SecurityScheme,
    SecurityScheme,
)

# Import Finance agent components
from finance_agent import FinanceAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("finance_agent_api")



@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8888)
@click.option('--agentservice', 'agentservice', default='finance-agent-service.default.svc.cluster.local')
@click.option('--agentport', 'agentport', default=80)
@click.option('--enable-oauth/--disable-oauth', 'enable_oauth', is_flag=True, default=True, help='Enable OAuth authentication')
def main(host: str, port: int, agentservice: str, agentport: int, enable_oauth: bool):
    try:
        import sqlite3
        sqlite_available = True
    except ImportError:
        logging.warning("SQLite not available, using mock data")
        sqlite_available = False
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id='finance_agent',
        name='Finance Agent',
        description='A simple Finance agent, i can help you with salary , deductions, and other finance related queries',
        tags=['Finance Agent'],
        examples=['What is the annual salary of EMP0001?', 'What is the total deduction for EMP0002 if she takes next 4 days off?'],
    )

    # Check for demo mode environment variable
    demo_mode_env = os.getenv("DEMO_MODE", "false")
    logger.info(f"DEMO_MODE environment variable: '{demo_mode_env}'")
    demo_mode = demo_mode_env.lower() == "true"
    logger.info(f"Demo mode detected: {demo_mode}, enable_oauth from CLI: {enable_oauth}")
    
    if demo_mode:
        enable_oauth = False
        logger.info("Demo mode enabled - OAuth authentication disabled")
    else:
        logger.info(f"Demo mode not enabled, keeping OAuth enabled: {enable_oauth}")
    
    # Set up authentication if enabled
    if enable_oauth:
        logger.info(f"Configuring Finance agent with OAuth authentication (enable_oauth={enable_oauth})")
        
        # Get OAuth configuration from environment
        okta_domain = os.getenv("OKTA_DOMAIN", "")
        auth_server_id = os.getenv("OKTA_AUTH_SERVER_ID", "")
        
        # Validate required OAuth environment variables
        if not okta_domain or not auth_server_id:
            logger.error("Missing required OAuth environment variables: OKTA_DOMAIN, OKTA_AUTH_SERVER_ID")
            raise ValueError("OAuth configuration incomplete - check environment variables")
        
        # Define OAuth2 security scheme
        oauth2_scheme = OAuth2SecurityScheme(
            type="oauth2",
            flows={
                "clientCredentials": {
                    "tokenUrl": f"https://{okta_domain}/oauth2/{auth_server_id}/v1/token",
                    "scopes": {
                        "agent.access": "Access to agent API"
                    }
                }
            }
        )
        
        # Security schemes dictionary
        security_schemes = {
            "oauth2": oauth2_scheme
        }
        
        # Security requirements - require oauth2 with agent.access scope
        security = [{"oauth2": ["agent.access"]}]
        
        logger.info("OAuth security schemes configured for Finance agent")
    else:
        logger.info("Using public authentication (OAuth disabled)")
        security_schemes = None
        security = None

    agent_card = AgentCard(
        name='Finance Agent',
        description='A simple Finance agent',
        url=f'http://{agentservice}:{agentport}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=[skill],
        security=security,
        securitySchemes=security_schemes,
    )



    # Create task manager
    task_manager = FinanceAgentTaskManager(
        agent=FinanceAgent(),
    )
    
    # Create A2A server application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=task_manager,
    )
    
    # Build and run the application
    app = server.build()
    
    # Log routes before adding middleware
    logger.info("Registered routes:")
    for route in app.routes:
        logger.info(f"  {route.path}")
    
    # Add OAuth middleware if enabled
    if enable_oauth:
        logger.info("Configuring OAuth middleware for Finance agent")
        try:
            app = configure_oauth_middleware(
                app, 
                public_paths=["/.well-known/agent.json", "/docs", "/openapi.json", "/health"],
                required_scopes=["agent.access"]
            )
            logger.info("OAuth middleware configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure OAuth middleware: {e}")
            # Continue without middleware
    
    # Import uvicorn to start the server
    import uvicorn
    
    logger.info(f"Starting Finance Agent on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()


