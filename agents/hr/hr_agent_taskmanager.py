"""Agent Task Manager."""

import logging

from collections.abc import AsyncIterable

from hr_agent import SUPPORTED_CONTENT_TYPES
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


class HRAgentTaskManager(DefaultRequestHandler):
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
        logger.info("Processing message send request for HR agent")
        
        # Extract query from message
        query = self._get_user_query(params)
        employee_id = self._get_employee_id(params)
        employee_name = self._get_employee_name(params)
        
        try:
            # Process query through HR agent
            result = self.agent.invoke(query, employee_id, employee_name)
            
            # Create response message
            import uuid
            response_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(kind='text', text=result if result else "Sorry, no result"))],
                contextId=getattr(params.message, 'contextId', None)
            )
            
            logger.info(f"HR agent processed query successfully: {query[:50]}...")
            return response_message
            
        except Exception as e:
            logger.error('Error invoking HR agent: %s', e)
            
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
    
    def _get_employee_id(self, params: MessageSendParams) -> str:

        if len(params.message.parts) < 2:
            return None
            
        part = params.message.parts[1]
        if not isinstance(part, TextPart):
            raise ValueError('Only text parts are supported')

        return part.text
    
    def _get_employee_name(self, params: MessageSendParams) -> str:

        if len(params.message.parts) < 3:
            return None
            
        part = params.message.parts[2]
        if not isinstance(part, TextPart):
            raise ValueError('Only text parts are supported')

        return part.text
