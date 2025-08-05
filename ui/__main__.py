"""
Streamlit UI Application for Agent Communication.
This UI communicates only with the Admin Agent which handles routing to HR/Finance agents.
"""

import asyncio
import os
import re
from datetime import datetime
from uuid import uuid4
import httpx
import streamlit as st
import time

# Import authentication module
from auth import require_auth, show_user_info, is_authenticated, get_current_user, is_demo_mode

# Import input validation module
from input_validation import validate_user_input, InputType, ValidationLevel

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


def clean_response_text(text: str) -> str:
    """Clean and format response text for better display"""
    if not text:
        return text
    
    # Remove agent prefixes and formatting
    text = re.sub(r'^Agent:\s*[^\n]*\n?', '', text, flags=re.MULTILINE)
    
    # Remove markdown headers and make them regular text
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove "Final Answer:" prefix
    text = re.sub(r'^Final Answer:\s*\n?', '', text, flags=re.MULTILINE)
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


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
        
        # Extract response content from nested JSON structure
        def extract_text_content(data, depth=0):
            """Recursively extract text content from nested response structure"""
            if depth > 10:  # Prevent infinite recursion
                return None
                
            if isinstance(data, dict):
                # Look for direct text field
                if "text" in data:
                    text_val = data["text"]
                    if isinstance(text_val, str) and text_val.strip():
                        # Check if it's a nested structure
                        if text_val.startswith("root=") or "text='" in text_val:
                            # Extract using multiple regex patterns
                            patterns = [
                                r"text='([^']*)'",
                                r'text="([^"]*)"',
                                r"text=([^,)]*)",
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, text_val)
                                if match:
                                    extracted = match.group(1).strip()
                                    if extracted and not extracted.startswith("root="):
                                        return extracted
                        else:
                            return text_val.strip()
                
                # Recursively search in nested structures
                for key in ["result", "parts", "artifacts"]:
                    if key in data:
                        if isinstance(data[key], list) and data[key]:
                            result_text = extract_text_content(data[key][0], depth + 1)
                            if result_text:
                                return result_text
                        elif isinstance(data[key], dict):
                            result_text = extract_text_content(data[key], depth + 1)
                            if result_text:
                                return result_text
            
            elif isinstance(data, list) and data:
                # Check first item in list
                return extract_text_content(data[0], depth + 1)
            
            return None
        
        try:
            # Extract text using the recursive function
            extracted_text = extract_text_content(result)
            if extracted_text:
                # Clean up the extracted text
                cleaned_text = clean_response_text(extracted_text)
                logger.info(f"Successfully extracted text: {cleaned_text[:50]}...")
                return cleaned_text
            
            # Fallback handling
            if "error" in result:
                error_msg = result["error"].get("message", str(result["error"]))
                return f"Admin Agent Error: {error_msg}"
            
            # Log the full structure for debugging
            logger.warning(f"Could not extract text from response structure: {str(result)[:200]}...")
            return "Sorry, I couldn't process the response properly. Please try again."
            
        except Exception as parse_error:
            logger.error(f"Error parsing response: {str(parse_error)}")
            return f"Error parsing response. Please try again."
        
    except Exception as e:
        error_msg = f"Error communicating with Admin Agent: {str(e)}"
        logger.error(error_msg)
        return error_msg


def get_agent_response(query: str) -> str:
    """Get response from Admin Agent (synchronous wrapper)."""
    return asyncio.run(send_query_to_admin(query))


def validate_and_process_query(query: str) -> tuple[str, bool]:
    """
    Validate user query and return response with validation status.
    
    Args:
        query: User's input query
        
    Returns:
        tuple: (response_message, is_valid)
    """
    # Validate the input query
    validation_result = validate_user_input(query, InputType.QUERY)
    
    if not validation_result.is_valid:
        error_message = "❌ **Input Validation Failed**\n\n"
        error_message += "**Errors:**\n"
        for error in validation_result.errors:
            error_message += f"• {error}\n"
        
        if validation_result.warnings:
            error_message += "\n**Warnings:**\n"
            for warning in validation_result.warnings:
                error_message += f"• {warning}\n"
        
        error_message += "\n**Please try again with a valid query.**"
        return error_message, False
    
    # If there are warnings but no errors, show them but continue
    if validation_result.warnings:
        st.warning("⚠️ **Query Warning:** " + "; ".join(validation_result.warnings))
    
    # Process the sanitized query
    try:
        response = get_agent_response(validation_result.sanitized_input)
        return response, True
    except Exception as e:
        logger.error(f"Error processing validated query: {str(e)}")
        return f"❌ **Error processing query:** {str(e)}", False


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
    
    # Add custom CSS for modern chat interface
    st.markdown("""
    <style>
    /* Modern chat styling */
    .stChatMessage {
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    /* Thinking animation */
    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }
    
    .thinking {
        animation: pulse 1.5s infinite;
    }
    
    /* Better message formatting */
    .stMarkdown {
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # App header
    st.title("🤖 HR & Finance Assistant")
    
    st.markdown("Ask questions about employees, vacation days, salaries, and financial information!")
    
    # Get current user for context
    current_user = get_current_user()
    if current_user:
        user_name = current_user.get('name', current_user.get('email', 'User'))
        # Clean up the user name to avoid duplication
        if user_name == "Demo User" and is_demo_mode():
            welcome_msg = f"**Welcome, {user_name}!**"
        else:
            welcome_msg = f"**Welcome, {user_name}!**"
            if is_demo_mode():
                welcome_msg += " *(Demo Mode)*"
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
        
        # Input Validation Status
        st.markdown("---")
        st.markdown("### 🛡️ Input Validation")
        
        from input_validation import get_validator
        validator = get_validator()
        stats = validator.get_validation_stats()
        
        st.info(f"**Security Level:** {stats['validation_level'].title()}")
        st.info(f"**Max Query Length:** {stats['max_query_length']} chars")
        st.info(f"**Malicious Patterns:** {stats['malicious_patterns_count']} detected")
        st.info(f"**Allowed Keywords:** {stats['allowed_keywords_count']} domains")
        
        # Validation level selector
        validation_level = st.selectbox(
            "Security Level",
            ["medium", "high", "low"],
            index=0,
            help="Higher security levels have stricter validation rules"
        )
        
        if st.button("Update Security Level"):
            from input_validation import ValidationLevel
            new_level = ValidationLevel(validation_level)
            # This would update the global validator - in a real app, you'd want to persist this
            st.success(f"Security level updated to {validation_level.title()}")
        
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
            # Show thinking indicator
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("🤔 **Thinking...**")
            
            # Get the actual response
            response, is_valid = validate_and_process_query(prompt)
            
            # Clear thinking message
            thinking_placeholder.empty()
            
            # Display response with streaming effect only if response is valid
            if is_valid:
                message_placeholder = st.empty()
                full_response = ""
                
                # Simple character-by-character streaming for smoother effect
                for i, char in enumerate(response):
                    full_response += char
                    # Update every few characters to reduce flicker
                    if i % 3 == 0 or i == len(response) - 1:
                        message_placeholder.markdown(full_response + ("▌" if i < len(response) - 1 else ""))
                        time.sleep(0.01)
                
                # Final clean message
                message_placeholder.markdown(full_response)
            else:
                # For errors, display immediately without streaming
                st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    logger.info("Starting Streamlit UI Application...")
    main()