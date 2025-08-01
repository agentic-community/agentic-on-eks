"""Agent Task Manager."""

import logging

from collections.abc import AsyncIterable

from finance_agent import SUPPORTED_CONTENT_TYPES
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    TextPart,
)


logger = logging.getLogger(__name__)


class FinanceAgentTaskManager(DefaultRequestHandler):
    """Agent Task Manager using latest A2A SDK patterns."""

    def __init__(self, agent):
        task_store = InMemoryTaskStore()
        super().__init__(agent_executor=agent, task_store=task_store)
        self.agent = agent

    async def on_message_send_stream(
        self, params: MessageSendParams, context=None
    ) -> AsyncIterable[Message]:
        """Handle streaming message requests (not implemented)."""
        raise NotImplementedError("Streaming not supported")

    async def on_message_send(
        self, params: MessageSendParams, context=None
    ) -> Message:
        """Handle incoming message requests."""
        logger.info("Processing message send request for Finance agent")
        
        # Extract query from message
        query = self._get_user_query(params)
        
        try:
            # Process query through Finance agent
            result = self.agent.invoke(query)
            result_text = "Sorry, no result"
            if result:
                result_text = result['response']
                result_text = result_text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            
            # Create response message
            import uuid
            response_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(kind='text', text=result_text))],
                contextId=getattr(params.message, 'contextId', None)
            )
            
            logger.info(f"Finance agent processed query successfully: {query[:50]}...")
            return response_message
            
        except Exception as e:
            logger.error('Error invoking Finance agent: %s', e)
            
            # Create error response message
            import uuid
            error_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(kind='text', text=f"Error processing request: {str(e)}"))],
                contextId=getattr(params.message, 'contextId', None)
            )
            
            return error_message
    
    def _are_modalities_compatible(self, requested_modes, supported_modes):
        """Check if requested modalities are supported."""
        if not requested_modes:
            return True
        return any(mode in supported_modes for mode in requested_modes)



    def _get_user_query(self, params: MessageSendParams) -> str:
        part = params.message.parts[0]
        
        # Handle A2A Part objects
        if hasattr(part, 'root') and hasattr(part.root, 'text'):
            return part.root.text
        elif hasattr(part, 'text'):
            return part.text
        elif isinstance(part, dict) and 'text' in part:
            return part['text']
        else:
            raise ValueError('Only text parts are supported')
    
    