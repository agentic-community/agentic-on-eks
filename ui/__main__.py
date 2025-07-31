"""
Streamlit UI Application for Agent Communication.
This UI communicates only with the Admin Agent which handles routing to HR/Finance agents.
"""

import asyncio
import os
from datetime import datetime
from uuid import uuid4
import httpx
import streamlit as st

# Import authentication module
from auth import require_auth, show_user_info, is_authenticated, get_current_user, is_demo_mode

# Simple data structures for agent communication
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    capabilities: Dict[str, Any]
    skills: List[Dict[str, Any]]
    security: Optional[List[Dict[str, Any]]] = None
    securitySchemes: Optional[Dict[str, Any]] = None

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ui_app")

# Admin Agent configuration  
ADMIN_HOST = os.getenv("ADMIN_HOST", "admin-agent-service.default.svc.cluster.local")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8080"))

# Global variables
admin_agent_card = None


async def get_agent_card(host: str, port: int) -> AgentCard:
    """Fetch agent card from the specified host and port."""
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
            security=agent_config.get("security"),
            securitySchemes=agent_config.get("securitySchemes")
        )
        
        logger.info(f"Successfully fetched agent card for {agent_card.name}")
        return agent_card
        
    except Exception as e:
        logger.error(f"Failed to fetch agent card from {url}: {str(e)}")
        st.error(f"Failed to connect to Admin Agent at {url}: {str(e)}")
        return None


async def initialize_admin_client():
    """Initialize the Admin Agent connection (HTTP-based)."""
    global admin_agent_card
    
    try:
        # Fetch Admin agent card for display purposes
        admin_agent_card = await get_agent_card(ADMIN_HOST, ADMIN_PORT)
        
        if admin_agent_card:
            logger.info(f"Admin Agent connection verified for {ADMIN_HOST}:{ADMIN_PORT}")
            return True
        else:
            logger.error("Failed to connect to Admin Agent")
            return False
            
    except Exception as e:
        logger.error(f"Error connecting to Admin Agent: {str(e)}")
        st.error(f"Error connecting to Admin Agent: {str(e)}")
        return False


async def send_query_to_admin(query: str) -> str:
    """Send a query to the Admin Agent using HTTP requests."""
    try:
        # Create A2A message payload using HTTP-based approach
        task_id = str(uuid4())
        
        payload = {
            "id": str(uuid4()),
            "method": "message/send", 
            "params": {
                "task": {
                    "id": task_id,
                    "name": "admin_query",
                    "params": {},
                    "status": {
                        "state": "submitted",
                        "timestamp": datetime.now().isoformat()
                    }
                },
                "message": {
                    "messageId": str(uuid4()),
                    "id": str(uuid4()),
                    "role": "user",
                    "parts": [{"type": "text", "text": query}]
                }
            }
        }
        
        # Send HTTP request directly to Admin Agent
        url = f"http://{ADMIN_HOST}:{ADMIN_PORT}/"
        logger.info(f"Sending query to Admin Agent via HTTP: {query[:50]}...")
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
        
        logger.info(f"Received response from Admin Agent: {str(result)[:100]}...")
        
        # Extract response content
        if "result" in result:
            task_result = result["result"]
            if isinstance(task_result, dict) and "artifacts" in task_result:
                artifacts = task_result["artifacts"]
                if artifacts and len(artifacts) > 0:
                    artifact = artifacts[0]
                    if "parts" in artifact and len(artifact["parts"]) > 0:
                        content = artifact["parts"][0].get("text", "No text content")
                        logger.info("Successfully extracted response content")
                        return content
        
        # Fallback handling
        if "error" in result:
            error_msg = result["error"].get("message", str(result["error"]))
            return f"Admin Agent Error: {error_msg}"
        
        # Last resort - return string representation
        return f"Response: {str(result)}"
        
    except Exception as e:
        error_msg = f"Error communicating with Admin Agent: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_agent_response(query: str) -> str:
    """Get response from Admin Agent (synchronous wrapper)."""
    return asyncio.run(send_query_to_admin(query))


# Initialize Streamlit app
def main():
    """Main Streamlit application."""
    # Set page config
    st.set_page_config(
        page_title="HR & Finance Chatbot", 
        page_icon="💬",
        layout="centered"
    )
    
    # Require authentication
    require_auth()
    
    # App header
    st.title("🤖 HR & Finance Assistant")
    
    # Show demo mode banner if active
    if is_demo_mode():
        st.info("🧪 **Demo Mode Active** - Authentication is bypassed for testing purposes. Set `DEMO_MODE=false` in your .env file to enable OKTA authentication.")
    
    st.markdown("Ask questions about employees, vacation days, salaries, and financial information!")
    
    # Get current user for context
    current_user = get_current_user()
    if current_user:
        welcome_msg = f"**Welcome, {current_user.get('name', current_user.get('email', 'User'))}!**"
        if is_demo_mode():
            welcome_msg += " *(Demo User)*"
        st.markdown(welcome_msg)
    
    # Display Admin Agent status
    with st.sidebar:
        st.header("🔧 System Status")
        
        # Check Admin Agent connection
        if st.button("Check Admin Agent Connection"):
            with st.spinner("Connecting to Admin Agent..."):
                connected = asyncio.run(initialize_admin_client())
                if connected and admin_agent_card:
                    st.success(f"✅ Connected to {admin_agent_card.name}")
                    st.info(f"**URL:** {admin_agent_card.url}")
                    st.info(f"**Version:** {admin_agent_card.version}")
                    st.info(f"**Skills:** {len(admin_agent_card.skills)} available")
                else:
                    st.error("❌ Failed to connect to Admin Agent")
        
        st.markdown("---")
        st.markdown("### 💡 Example Queries")
        st.markdown("""
        **HR Questions:**
        - What is the name of employee EMP0002?
        - How many vacation days does EMP0001 have left?
        - What public holidays are there in the US in 2024?
        
        **Finance Questions:**
        - What is the annual salary of EMP0003?
        - Calculate leave deduction for EMP0002 for 5 days off
        - Submit a raise for EMP0001
        """)
        
        # Show user info and logout option
        show_user_info()
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Hello! I'm your HR & Finance assistant. I can help you with employee information, vacation days, salary calculations, and more. What would you like to know?"
        })
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get response from Admin Agent
        with st.chat_message("assistant"):
            with st.spinner("Processing your request... This may take up to 2 minutes for complex queries."):
                response = get_agent_response(prompt)
            st.write(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    logger.info("Starting Streamlit UI Application...")
    main()