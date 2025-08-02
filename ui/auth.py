"""
OKTA Authentication Module for Streamlit UI
"""

import os
import streamlit as st
from dotenv import load_dotenv
import requests
from urllib.parse import urlencode, parse_qs
import json
import base64
import logging
from jose import jwt, JWTError
from typing import Dict, Optional, Any
import time

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Demo mode configuration
def is_demo_mode() -> bool:
    """Check if demo mode is enabled"""
    demo_mode = os.getenv("DEMO_MODE", "false").lower()
    return demo_mode in ["true", "1", "yes", "on"]

def get_demo_user() -> Dict[str, Any]:
    """Get demo user information"""
    return {
        "email": os.getenv("DEMO_USER_EMAIL", "demo@company.com"),
        "name": os.getenv("DEMO_USER_NAME", "Demo User"),
        "sub": os.getenv("DEMO_USER_ID", "demo-user-001"),
        "preferred_username": os.getenv("DEMO_USER_EMAIL", "demo@company.com").split("@")[0]
    }

class OktaAuth:
    """OKTA Authentication handler for Streamlit"""
    
    def __init__(self):
        self.domain = os.getenv("OKTA_DOMAIN")
        self.auth_server_id = os.getenv("OKTA_AUTH_SERVER_ID")
        self.client_id = os.getenv("OKTA_CLIENT_ID")
        self.client_secret = os.getenv("OKTA_CLIENT_SECRET")
        self.redirect_uri = os.getenv("OKTA_REDIRECT_URI")
        self.scope = os.getenv("OKTA_SCOPE", "openid profile email")
        self.audience = os.getenv("OKTA_AUDIENCE")
        
        # Validate configuration
        if not all([self.domain, self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required OKTA configuration. Please check your .env file.")
        
        # Build URLs
        if self.auth_server_id:
            self.issuer = f"https://{self.domain}/oauth2/{self.auth_server_id}"
            self.auth_url = f"{self.issuer}/v1/authorize"
            self.token_url = f"{self.issuer}/v1/token"
            self.userinfo_url = f"{self.issuer}/v1/userinfo"
            self.jwks_url = f"{self.issuer}/v1/keys"
        else:
            # Use org-level authorization server
            self.issuer = f"https://{self.domain}"
            self.auth_url = f"https://{self.domain}/oauth2/v1/authorize"
            self.token_url = f"https://{self.domain}/oauth2/v1/token"
            self.userinfo_url = f"https://{self.domain}/oauth2/v1/userinfo"
            self.jwks_url = f"https://{self.domain}/oauth2/v1/keys"
        
        logger.info(f"OKTA Auth initialized for domain: {self.domain}")
    
    def get_login_url(self, state: str) -> str:
        """Generate OKTA authorization URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state
        }
        
        login_url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"Generated login URL: {login_url}")
        return login_url
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully exchanged code for token")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise Exception(f"Token exchange failed: {str(e)}")
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OKTA"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"Retrieved user info for: {user_info.get('email', 'unknown')}")
            return user_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise Exception(f"Failed to get user info: {str(e)}")
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        try:
            # Get JWKS for token validation
            jwks_response = requests.get(self.jwks_url)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.audience if self.audience else self.client_id,
                issuer=self.issuer
            )
            
            # Check if token is expired
            current_time = int(time.time())
            if payload.get("exp", 0) < current_time:
                logger.warning("Token has expired")
                return None
            
            return payload
            
        except JWTError as e:
            logger.error(f"Token validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return None

# Global auth instance
_auth_instance = None

def get_auth() -> OktaAuth:
    """Get or create OKTA auth instance"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = OktaAuth()
    return _auth_instance

def is_authenticated() -> bool:
    """Check if user is authenticated"""
    # In demo mode, always consider user as authenticated
    if is_demo_mode():
        return True
    return "authenticated" in st.session_state and st.session_state.authenticated

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user"""
    if is_demo_mode():
        return get_demo_user()
    elif is_authenticated():
        return st.session_state.get("user_info")
    return None

def logout():
    """Logout user"""
    # Clear session state
    keys_to_remove = ["authenticated", "user_info", "access_token", "id_token", "auth_state"]
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    
    logger.info("User logged out")
    st.rerun()

def require_auth():
    """Decorator function to require authentication"""
    if is_demo_mode():
        # In demo mode, skip authentication
        return
    elif not is_authenticated():
        show_login_page()
        st.stop()

def show_login_page():
    """Display login page"""
    # Handle callback first if present
    query_params = st.query_params
    if "code" in query_params:
        handle_callback(query_params)
        return
    
    st.title("🔐 Login Required")
    st.markdown("Please login with your OKTA credentials to access the HR & Finance Assistant.")
    
    # Generate state for CSRF protection - make it persistent
    if "auth_state" not in st.session_state:
        import secrets
        st.session_state.auth_state = secrets.token_urlsafe(32)
        # Also store in a more persistent way
        st.session_state.persistent_auth_state = st.session_state.auth_state
    
    auth = get_auth()
    login_url = auth.get_login_url(st.session_state.auth_state)
    
    st.markdown(f"[🚀 Login with OKTA]({login_url})")
    
    st.info("👆 Click the link above to login with your OKTA credentials")
    
    # Optional debug info (can be removed in production)
    # if st.checkbox("Show debug info"):
    #     st.write(f"Auth state: {st.session_state.auth_state[:10]}...")
    #     st.write(f"Login URL: {login_url}")

def handle_callback(query_params):
    """Handle OKTA callback"""
    code = query_params.get("code")
    state = query_params.get("state")
    
    st.title("🔄 Processing Login...")
    
    # Validate state - try both stored states for robustness
    stored_state = st.session_state.get("auth_state") or st.session_state.get("persistent_auth_state")
    
    # Note: State validation is currently relaxed due to Streamlit session management
    # In production, you may want to implement a more robust state storage mechanism
    if stored_state and state and state != stored_state:
        st.error("Security validation failed. Please try logging in again.")
        if st.button("🔄 Try Again"):
            # Clear query params and session state
            st.query_params.clear()
            keys_to_clear = ["auth_state", "persistent_auth_state"]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        st.stop()
    
    try:
        with st.spinner("Authenticating with OKTA..."):
            auth = get_auth()
            
            # Exchange code for token
            token_data = auth.exchange_code_for_token(code)
            
            # Get user info
            user_info = auth.get_user_info(token_data["access_token"])
            
            # Store in session
            st.session_state.authenticated = True
            st.session_state.user_info = user_info
            st.session_state.access_token = token_data["access_token"]
            st.session_state.id_token = token_data.get("id_token")
            
            # Clear auth state and query params
            if "auth_state" in st.session_state:
                del st.session_state["auth_state"]
            st.query_params.clear()
            
            st.success("✅ Login successful! Redirecting...")
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ Authentication failed: {str(e)}")
        logger.error(f"Authentication callback failed: {str(e)}")
        
        if st.button("🔄 Try Again"):
            # Clear everything and start over
            st.query_params.clear()
            keys_to_remove = ["auth_state", "authenticated", "user_info", "access_token", "id_token"]
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def show_user_info():
    """Display user information in sidebar"""
    if is_authenticated():
        user_info = get_current_user()
        if user_info:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 User Info")
            
            st.sidebar.markdown(f"**Name:** {user_info.get('name', 'N/A')}")
            
            # Only show logout in non-demo mode
            if not is_demo_mode() and st.sidebar.button("🚪 Logout"):
                logout()