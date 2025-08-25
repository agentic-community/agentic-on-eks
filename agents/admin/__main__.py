import logging
import os
from strands import Agent
import click
from strands_tools.a2a_client import A2AClientToolProvider
from a2a.types import AgentSkill
from strands.multiagent.a2a import A2AServer


# Configure logging
logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Enable info logging for A2AClientToolProvider
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


    a2a_client_tool_provider = A2AClientToolProvider(known_agent_urls=[hr_url, finance_url])

    # Create a Strands agent
    admin_agent = Agent(
        name="Admin agent",
        description="An orchestrator agent",
        tools=[a2a_client_tool_provider.tools],
        callback_handler=None
    )

    # Create A2A server (streaming enabled by default)
    a2a_server = A2AServer(
        agent=admin_agent,
        host="0.0.0.0", port="8080",
        http_url="http://{agentservice}:{agentport}/" ,
        skills = admin_skills
     )

    # Start the server
    a2a_server.serve()

if __name__ == "__main__":
    main()