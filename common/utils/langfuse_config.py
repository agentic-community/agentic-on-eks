"""
LangFuse configuration and initialization utility for agents
"""
import os
import logging
from typing import Optional
from langfuse import Langfuse

logger = logging.getLogger(__name__)

class LangFuseConfig:
    """LangFuse configuration and client management"""
    
    def __init__(self):
        self.client: Optional[Langfuse] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize LangFuse client with environment variables"""
        try:
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            host = os.getenv("LANGFUSE_HOST", "http://langfuse-web.langfuse.svc.cluster.local:3000")
            
            if not public_key or not secret_key:
                logger.warning("LangFuse credentials not found. Observability disabled.")
                return
            
            self.client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host
            )
            
            logger.info(f"LangFuse client initialized successfully. Host: {host}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangFuse client: {e}")
            self.client = None
    
    def get_client(self) -> Optional[Langfuse]:
        """Get LangFuse client instance"""
        return self.client
    
    def is_enabled(self) -> bool:
        """Check if LangFuse is enabled and configured"""
        return self.client is not None

# Global instance
langfuse_config = LangFuseConfig()

def get_langfuse_client() -> Optional[Langfuse]:
    """Get the global LangFuse client instance"""
    return langfuse_config.get_client()

def is_langfuse_enabled() -> bool:
    """Check if LangFuse observability is enabled"""
    return langfuse_config.is_enabled()