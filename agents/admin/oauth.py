"""
Simple OAuth Client for Admin Agent A2A Communication
Gets fresh OKTA tokens for each request - no caching or refresh logic
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleOAuthClient:
    """Simple OAuth client that gets fresh tokens for each request."""
    
    def __init__(self):
        """Initialize OAuth client with environment variables."""
        self.domain = os.getenv("OKTA_DOMAIN")
        self.auth_server_id = os.getenv("OKTA_AUTH_SERVER_ID") 
        self.client_id = os.getenv("OKTA_CLIENT_ID")
        self.client_secret = os.getenv("OKTA_CLIENT_SECRET")
        self.scope = os.getenv("OKTA_SCOPE", "agent.access")
        
        # Validate configuration
        if not all([self.domain, self.auth_server_id, self.client_id, self.client_secret]):
            raise ValueError("Missing required OAuth configuration. Please set OKTA_DOMAIN, OKTA_AUTH_SERVER_ID, OKTA_CLIENT_ID, and OKTA_CLIENT_SECRET")
        
        # Build token URL
        self.token_url = f"https://{self.domain}/oauth2/{self.auth_server_id}/v1/token"
        
        logger.info(f"OAuth client initialized for domain: {self.domain}")
    
    def get_access_token(self) -> Optional[str]:
        """
        Get a fresh access token from OKTA using client credentials flow.
        Returns None if token acquisition fails.
        """
        try:
            # Prepare token request
            data = {
                "grant_type": "client_credentials",
                "scope": self.scope,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Request token from OKTA
            response = requests.post(self.token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if access_token:
                logger.info("Successfully obtained OAuth access token")
                return access_token
            else:
                logger.error("No access token in response")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get OAuth token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting OAuth token: {str(e)}")
            return None
    
    def get_auth_headers(self) -> dict:
        """
        Get authorization headers with fresh OAuth token.
        Returns empty dict if token acquisition fails.
        """
        token = self.get_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        else:
            logger.warning("Failed to get OAuth token, returning empty headers")
            return {}


# Global OAuth client instance
_oauth_client = None


def get_oauth_client() -> SimpleOAuthClient:
    """Get or create global OAuth client instance."""
    global _oauth_client
    if _oauth_client is None:
        _oauth_client = SimpleOAuthClient()
    return _oauth_client


def get_auth_headers() -> dict:
    """Convenience function to get auth headers with fresh token."""
    try:
        client = get_oauth_client()
        return client.get_auth_headers()
    except Exception as e:
        logger.error(f"Failed to get OAuth headers: {str(e)}")
        return {}