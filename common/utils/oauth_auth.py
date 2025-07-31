"""OAuth utilities for token validation and acquisition."""

import os
import json
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class OAuthConfig(BaseModel):
    """OAuth configuration model."""
    domain: str
    auth_server_id: str
    scope: str
    audience: str
    token_endpoint: str
    jwks_url: str
    issuer: str

async def validate_token(token: str, config: OAuthConfig) -> Dict[str, Any]:
    """Validate JWT token and return claims."""
    try:
        # Get JWKS for signature validation
        async with httpx.AsyncClient() as client:
            jwks_response = await client.get(config.jwks_url)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
        
        # Validate token
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=config.audience,
            issuer=config.issuer
        )
        
        return claims
        
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise

def load_oauth_config_from_env() -> OAuthConfig:
    """Load OAuth configuration from environment variables."""
    domain = os.getenv("OKTA_DOMAIN")
    auth_server_id = os.getenv("OKTA_AUTH_SERVER_ID")
    scope = os.getenv("OKTA_SCOPE", "agent.access")
    audience = os.getenv("OKTA_AUDIENCE", "api://a2a-agents")
    
    if not all([domain, auth_server_id]):
        raise ValueError("Missing required OAuth environment variables: OKTA_DOMAIN, OKTA_AUTH_SERVER_ID")
    
    return OAuthConfig(
        domain=domain,
        auth_server_id=auth_server_id,
        scope=scope,
        audience=audience,
        token_endpoint=f"https://{domain}/oauth2/{auth_server_id}/v1/token",
        jwks_url=f"https://{domain}/oauth2/{auth_server_id}/v1/keys",
        issuer=f"https://{domain}/oauth2/{auth_server_id}"
    )