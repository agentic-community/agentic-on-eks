"""OAuth middleware for A2A server authentication."""

import logging
from typing import List, Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..utils.oauth_auth import validate_token, load_oauth_config_from_env, OAuthConfig

logger = logging.getLogger(__name__)

class OAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for OAuth token validation."""
    
    def __init__(self, app, config: OAuthConfig, public_paths: List[str] = None, required_scopes: List[str] = None):
        super().__init__(app)
        self.config = config
        self.public_paths = public_paths or ["/.well-known/agent.json", "/docs", "/openapi.json", "/health"]
        self.required_scopes = required_scopes or ["agent.access"]

    async def dispatch(self, request: Request, call_next):
        """Process request and validate OAuth token."""
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            logger.debug(f"Skipping OAuth validation for public path: {request.url.path}")
            return await call_next(request)
        
        # Extract authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            logger.warning("Missing authorization header")
            return JSONResponse(
                status_code=401,
                content={"error": "missing_authorization", "message": "Authorization header required"}
            )
        
        # Extract bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning("Invalid authorization header format")
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_authorization", "message": "Bearer token required"}
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Validate token
            logger.info("Validating OAuth token")
            claims = await validate_token(token, self.config)
            
            # Validate scopes
            if not self._validate_scopes(claims):
                logger.warning("Token has insufficient scopes")
                return JSONResponse(
                    status_code=403,
                    content={"error": "insufficient_scope", "message": "Required scopes not present"}
                )
            
            # Add claims to request state
            request.state.token_claims = claims
            logger.info("OAuth token validation successful")
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": "Token validation failed"}
            )

    def _validate_scopes(self, claims: Dict[str, Any]) -> bool:
        """Validate that token has required scopes."""
        # Extract scopes from token - check both 'scope' and 'scp' fields
        token_scopes = []
        
        # Check 'scope' field (space-delimited string)
        scope_value = claims.get('scope', '')
        if isinstance(scope_value, str):
            token_scopes = scope_value.split()
        elif isinstance(scope_value, list):
            token_scopes = scope_value
        
        # If no scopes found, try 'scp' field (used by Okta)
        if not token_scopes:
            scp_value = claims.get('scp', [])
            if isinstance(scp_value, list):
                token_scopes = scp_value
            elif isinstance(scp_value, str):
                token_scopes = scp_value.split()
        
        logger.info(f"Token scopes: {token_scopes}, Required scopes: {self.required_scopes}")
        
        # Check if token has all required scopes
        return all(scope in token_scopes for scope in self.required_scopes)

def configure_oauth_middleware(app, public_paths: List[str] = None, required_scopes: List[str] = None):
    """Configure OAuth middleware for the application."""
    try:
        config = load_oauth_config_from_env()
        logger.info(f"Configuring OAuth middleware with issuer: {config.issuer}")
        middleware = OAuthMiddleware(app, config, public_paths, required_scopes)
        return middleware
    except Exception as e:
        logger.error(f"Failed to configure OAuth middleware: {e}")
        # Return app without middleware if configuration fails
        return app