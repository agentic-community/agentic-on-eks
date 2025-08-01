"""Admin Agent Task Manager using latest A2A SDK patterns."""

import logging
from collections.abc import AsyncIterable
from typing import Dict, Any
from datetime import datetime

# Latest A2A SDK imports
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    JSONRPCResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)

from admin_agent import SUPPORTED_CONTENT_TYPES

logger = logging.getLogger(__name__)


class AdminAgentTaskManager(DefaultRequestHandler):
    """Task Manager for Admin Agent using latest A2A SDK patterns."""

    def __init__(self, agent):
        task_store = InMemoryTaskStore()
        super().__init__(agent_executor=agent, task_store=task_store)
        self.agent = agent

    async def _validate_request(self, params: MessageSendParams) -> JSONRPCResponse | None:
        """Validate incoming request modalities."""
        # Skip modality validation for now since MessageSendParams doesn't have acceptedOutputModes
        logger.info("Request validation passed - skipping output mode validation")
        return None

    def _are_modalities_compatible(self, requested_modes, supported_modes):
        """Check if requested modalities are supported."""
        if not requested_modes:
            return True
        return any(mode in supported_modes for mode in requested_modes)

    def _new_incompatible_types_error(self, request_id: str) -> JSONRPCResponse:
        """Create error response for incompatible types."""
        return JSONRPCResponse(
            id=request_id,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Unsupported content type"
            }
        )

    async def on_message_send(
        self, params: MessageSendParams, context=None
    ) -> Message:
        """Handle incoming message requests from UI."""
        # Validate request
        await self._validate_request(params)
        
        # Extract query from message
        query = self._get_user_query(params)
        logger.info(f"Processing query: {query[:50]}...")
        
        try:
            # Process query through admin agent
            result = await self.agent.process_query(query, "default-user")
            logger.info(f"Admin agent response: {result[:100]}...")
            
            # Create response message
            import uuid
            response_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(kind='text', text=result))],
                contextId=getattr(params.message, 'contextId', None)
            )
            
            return response_message
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            
            # Create error response message
            import uuid
            error_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.agent,
                parts=[Part(root=TextPart(kind='text', text=f"Error processing request: {str(e)}"))],
                contextId=getattr(params.message, 'contextId', None)
            )
            
            return error_message

    async def on_message_send_stream(
        self, params: MessageSendParams, context=None
    ) -> AsyncIterable[Task]:
        """Handle streaming task requests (not implemented for now)."""
        raise NotImplementedError("Streaming not supported")

    async def _invoke(self, params: MessageSendParams, task: Task) -> Task:
        """Process the task by invoking the admin agent."""
        query = self._get_user_query(params)
        user_id = "default-user"
        
        try:
            # Process query through admin agent
            result = await self.agent.process_query(query, user_id)
            
            # Create successful response
            parts = [{'type': 'text', 'text': result}]
            
            # Update task status
            updated_task = await self._update_task_store(
                task.id,
                TaskStatus(state=TaskState.completed),
                [Artifact(parts=parts)],
            )
            
            logger.info(f"Admin agent processed query successfully: {query[:50]}...")
            return updated_task
            
        except Exception as e:
            logger.error('Error invoking admin agent: %s', e)
            
            # Create error response
            error_parts = [{'type': 'text', 'text': f"Error processing request: {str(e)}"}]
            
            # Update task with error status
            updated_task = await self._update_task_store(
                task.id,
                TaskStatus(
                    state=TaskState.failed
                ),
                [Artifact(parts=error_parts)],
            )
            
            return updated_task

    async def _update_task_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        """Update task in the store with new status and artifacts."""
        try:
            # Get existing task
            task = await self.task_store.get(task_id)
            if not task:
                raise ValueError(f'Task {task_id} not found')

            # Update status
            task.status = status

            # Add artifacts
            if artifacts:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            # Update in store
            await self.task_store.save(task_id, task)
            
            return task
            
        except Exception as e:
            logger.error('Error updating task store for task %s: %s', task_id, e)
            raise

    def _get_user_query(self, params: MessageSendParams) -> str:
        """Extract user query from message parameters."""
        if not params.message.parts:
            raise ValueError('No message parts found')
            
        part = params.message.parts[0]
        logger.info(f"Message part type: {type(part)}")
        
        # Handle A2A Part objects
        if hasattr(part, 'root'):
            # A2A Part object with root TextPart
            if hasattr(part.root, 'text'):
                logger.info(f"Extracted text from Part.root: {part.root.text}")
                return part.root.text
        elif hasattr(part, 'text'):
            # Direct TextPart object
            return part.text
        elif isinstance(part, dict):
            if 'text' in part:
                return part['text']
            elif 'content' in part:
                return part['content']
        elif isinstance(part, str):
            return part
        
        # If we get here, log for debugging
        logger.error(f"Unsupported part type: {type(part)}, content: {part}")
        if hasattr(part, '__dict__'):
            logger.error(f"Part attributes: {part.__dict__}")
        raise ValueError(f'Unsupported message part type: {type(part)}')

