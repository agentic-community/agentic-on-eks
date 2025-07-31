"""Admin Agent Main Entry Point using latest A2A SDK."""

import logging
import os
import click

# Latest A2A SDK imports
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    # OAuth2SecurityScheme,  # Available for future OAuth implementation
    # SecurityScheme,        # Available for future OAuth implementation
)

# Admin agent components
from admin_agent import AdminAgent
from admin_agent_taskmanager import AdminAgentTaskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("admin_agent_main")


@click.command()
@click.option('--host', 'host', default='0.0.0.0')
@click.option('--port', 'port', default=8080)
@click.option('--agentservice', 'agentservice', default='admin-agent-service.default.svc.cluster.local')
@click.option('--agentport', 'agentport', default=8080)
def main(host: str, port: int, agentservice: str, agentport: int):
    """Start the Admin Agent server."""
    logger.info("Starting Admin Agent...")
    
    # Define agent capabilities
    capabilities = AgentCapabilities(streaming=False)
    
    # Define admin agent skill
    admin_skill = AgentSkill(
        id='admin_agent',
        name='Admin Agent',
        description='Intelligent routing agent that forwards queries to HR and Finance agents based on context analysis.',
        tags=['Admin', 'Router', 'Supervisor'],
        examples=[
            'What is the name of employee EMP0002?',
            'How many vacation days does employee EMP0001 have left?',
            'What is the annual salary of employee EMP0003?',
            'Calculate leave deduction for 5 days off for EMP0002',
            'What public holidays are there in the US in 2024?'
        ],
    )
    
    # No OAuth for now - use public authentication
    security_schemes = None
    security = None
    
    # Create agent card
    agent_card = AgentCard(
        name='Admin Agent',
        description='Intelligent routing agent that analyzes queries and forwards them to the appropriate HR or Finance agent. Enables true agent-to-agent communication via A2A protocol.',
        url=f'http://{agentservice}:{agentport}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=capabilities,
        skills=[admin_skill],
        security=security,
        securitySchemes=security_schemes,
    )
    
    # Create admin agent instance
    admin_agent = AdminAgent()
    
    # Create task manager
    task_manager = AdminAgentTaskManager(agent=admin_agent)
    
    # Create A2A server application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=task_manager,
    )
    
    logger.info(f"Admin Agent configured:")
    logger.info(f"  - Name: {agent_card.name}")
    logger.info(f"  - URL: {agent_card.url}")
    logger.info(f"  - Security: {agent_card.security}")
    logger.info(f"  - Skills: {len(agent_card.skills)}")
    
    # Build and run the application
    app = server.build()
    
    logger.info("Registered routes:")
    for route in app.routes:
        logger.info(f"  {route.path}")
    
    # Import uvicorn here to start the server
    import uvicorn
    
    logger.info(f"Starting Admin Agent on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()