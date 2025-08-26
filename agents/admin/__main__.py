import logging
import os
from strands import Agent
import click
from a2a.types import AgentSkill
from strands.multiagent.a2a import A2AServer
from oauth_a2a_client import OAuthA2AClientToolProvider


# Configure logging
logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Enable info logging for A2A clients
a2a_logger = logging.getLogger('strands_tools.a2a_client')
a2a_logger.setLevel(logging.INFO)

SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']


@click.command()
@click.option('--host', 'host', default='0.0.0.0')
@click.option('--port', 'port', default=8080)
@click.option('--agentservice', 'agentservice', default='admin-agent-service.default.svc.cluster.local')
@click.option('--agentport', 'agentport', default=8080)
def main(host: str, port: int, agentservice: str, agentport: int):

    admin_skills = [AgentSkill(
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
        )]

    hr_host = os.getenv("HR_HOST", "hr-agent-service.default.svc.cluster.local")
    logger.info(f"agent:mainhr_host is: {hr_host}")
    hr_port = int(os.getenv("HR_PORT", "80"))
    hr_url = f"http://{hr_host}:{hr_port}"

    finance_host = os.getenv("FINANCE_HOST", "finance-agent-service.default.svc.cluster.local")
    logger.info(f"finance_host is: {finance_host}")
    finance_port = int(os.getenv("FINANCE_PORT", "80"))
    finance_url = f"http://{finance_host}:{finance_port}"
    logger.info(f"HR URL: {hr_url}")
    logger.info(f"Finance URL: {finance_url}")

    known_agent_urls=[hr_url, finance_url]

    a2a_client_tool_provider = OAuthA2AClientToolProvider(known_agent_urls=known_agent_urls)
    

    # Create a Strands agent
    admin_agent = Agent(
        name="Admin agent",
        system_prompt=("""
        You are a orchestrator agent for this agentic system, for simple prompts, you pass the users prompt to the right agent.
        for complex prompts that need coordination across multiple agents , you use workflows to manage that.
        Use tools to gather the information and agent cards about the available a2a servers and send the requests to the appropriate a2a
        server"""
    ),
        description="An orchestrator agent",
        tools=[a2a_client_tool_provider.tools],
        callback_handler=None
    )

    # Create A2A server (streaming enabled by default)
    a2a_server = A2AServer(
        agent=admin_agent,
        host=host, 
        port=port,
        http_url=f"http://{agentservice}:{agentport}/",
        skills=admin_skills
    )

    logger.info(f"Starting admin agent server on {host}:{port}")
    logger.info("OAuth authentication enabled for A2A requests")
    
    # Start the server
    a2a_server.serve()

if __name__ == "__main__":
    main()