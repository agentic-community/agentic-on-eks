"""OAuth-enabled A2A client tool provider."""

import logging
import httpx
from typing import List, Dict, Any
from strands_tools.a2a_client import A2AClientToolProvider
from oauth import get_auth_headers

logger = logging.getLogger(__name__)


class OAuthA2AClientToolProvider(A2AClientToolProvider):
    """A2A client tool provider with OAuth authentication support."""
    
    def __init__(self, known_agent_urls: List[str]):
        """Initialize with OAuth support."""
        super().__init__(known_agent_urls=known_agent_urls)
        
    def _get_fresh_oauth_headers(self) -> Dict[str, str]:
        """Get fresh OAuth headers for requests."""
        oauth_headers = get_auth_headers()
        if oauth_headers:
            logger.info("Successfully obtained OAuth headers for A2A request")
            return oauth_headers
        else:
            logger.warning("Failed to obtain OAuth headers, proceeding without authentication")
            return {}
    
    async def _ensure_httpx_client(self) -> httpx.AsyncClient:
        """Ensure the shared HTTP client is initialized with OAuth headers."""
        # First call the parent implementation to handle client creation
        client = await super()._ensure_httpx_client()
        
        # Then add fresh OAuth headers
        oauth_headers = self._get_fresh_oauth_headers()
        if oauth_headers:
            logger.info("Adding fresh OAuth headers to httpx client")
            client.headers.update(oauth_headers)
        else:
            logger.warning("No OAuth headers available for httpx client")
        
        return client