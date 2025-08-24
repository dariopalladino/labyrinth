"""
AgentClient - Simplified client for agent-to-agent communication.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import structlog
from a2a.client.client import Client as A2AClient
from a2a.client.client_factory import ClientFactory, ClientConfig
from a2a import types as a2a_types

from labyrinth.client.discovery import AgentDiscoveryService, get_discovery_service

from labyrinth.types.messages import Message, MessageResponse
from labyrinth.types.tasks import Task, TaskStatus, TaskResult, TaskFilter
from labyrinth.utils.config import Config, get_config
from labyrinth.utils.exceptions import (
    LabyrinthError,
    CommunicationError,
    MessageDeliveryError,
    TaskError,
    TaskNotFoundError,
    TaskTimeoutError,
    ConfigurationError,
)

logger = structlog.get_logger(__name__)


class AgentClient:
    """
    High-level client for communicating with A2A agents.
    
    This class provides a simplified interface for:
    - Sending messages to agents
    - Creating and managing tasks
    - Discovering agent capabilities
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        a2a_client: Optional[A2AClient] = None,
        discovery_service: Optional[AgentDiscoveryService] = None,
    ):
        """
        Initialize AgentClient.
        
        Args:
            config: Configuration object (uses global config if None)
            a2a_client: Pre-configured A2A client (creates new if None)
            discovery_service: Agent discovery service (uses global if None)
        """
        self.config = config or get_config()
        self._a2a_client = a2a_client
        self.discovery_service = discovery_service or get_discovery_service()
        self._client_cache: Dict[str, A2AClient] = {}  # Cache A2A clients per agent
        self._logger = logger.bind(client_id=id(self))
        
    async def _get_a2a_client(self, agent_id: str) -> A2AClient:
        """
        Get or create A2A client for communicating with a specific agent.
        
        Args:
            agent_id: ID of the target agent
            
        Returns:
            A2A Client configured for the target agent
        """
        # Check if we have a cached client for this agent
        if agent_id in self._client_cache:
            return self._client_cache[agent_id]
        
        self._logger.info("Creating A2A client for agent", agent_id=agent_id)
        
        try:
            # 1. Discover the agent and get its card
            agent_card = await self.discovery_service.discover_agent(agent_id)
            
            # 2. Create client configuration
            client_config = ClientConfig(
                streaming=True,
                polling=False,
                use_client_preference=False,
                accepted_output_modes=["text"],
            )
            
            # 3. Create factory with config
            factory = ClientFactory(client_config)
            
            # 4. Create client with the agent card
            client = factory.create(agent_card)
            
            # 5. Cache the client
            self._client_cache[agent_id] = client
            
            self._logger.info(
                "Successfully created A2A client",
                agent_id=agent_id,
                agent_name=agent_card.name,
                agent_url=agent_card.url
            )
            
            return client
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create A2A client for agent {agent_id}: {e}",
                {"agent_id": agent_id}
            )
    
    async def send_message(
        self,
        to_agent: str,
        message: Union[str, Message],
        skill: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageResponse:
        """
        Send a message to another agent.
        
        Args:
            to_agent: Target agent identifier
            message: Message content (string or Message object)
            skill: Specific skill/capability to invoke
            timeout: Request timeout in seconds
            metadata: Additional metadata
            
        Returns:
            MessageResponse with delivery status and response
            
        Raises:
            MessageDeliveryError: If message cannot be delivered
            CommunicationError: For communication errors
        """
        timeout = timeout or self.config.default_timeout
        
        self._logger.info(
            "Sending message to agent",
            to_agent=to_agent,
            skill=skill,
            timeout=timeout
        )
        
        # Convert to Message object if needed
        if isinstance(message, str):
            message_obj = Message.text(message)
        else:
            message_obj = message
            
        # Add metadata if provided
        if metadata:
            message_obj.metadata.update(metadata)
        
        try:
            client = await self._get_a2a_client(to_agent)
            
            # Convert to A2A format
            a2a_message = message_obj.to_a2a_message()
            
            # Send message using A2A client
            response = await client.send_message(
                message=a2a_message,
                skill=skill,
            )
            
            # Convert response
            message_response = MessageResponse.from_a2a_response(response)
            
            self._logger.info(
                "Message sent successfully",
                message_id=message_response.message_id,
                status=message_response.status
            )
            
            return message_response
            
        except Exception as e:
            self._logger.error(
                "Failed to send message",
                error=str(e),
                to_agent=to_agent
            )
            
            if "timeout" in str(e).lower():
                raise MessageDeliveryError(f"Message timeout: {e}")
            elif "not found" in str(e).lower():
                raise MessageDeliveryError(f"Agent not found: {to_agent}")
            else:
                raise CommunicationError(f"Failed to send message: {e}")
    
    async def create_task(
        self,
        agent_id: str,
        skill: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task for an agent to execute.
        
        Args:
            agent_id: Target agent identifier
            skill: Skill/capability to invoke
            parameters: Task parameters
            timeout: Task timeout in seconds
            metadata: Additional metadata
            
        Returns:
            Task object with tracking information
            
        Raises:
            TaskError: If task creation fails
        """
        timeout = timeout or self.config.task_default_timeout
        parameters = parameters or {}
        metadata = metadata or {}
        
        self._logger.info(
            "Creating task",
            agent_id=agent_id,
            skill=skill,
            timeout=timeout
        )
        
        try:
            client = await self._get_a2a_client(agent_id)
            
            # Create task message with parameters
            import json
            task_content = json.dumps(parameters) if parameters else "{}"
            task_message = Message.text(task_content)
            
            # Send as message (A2A SDK handles this as a task)
            response = await client.send_message(
                message=task_message.to_a2a_message(),
                skill=skill,
            )
            
            # Create task object
            task = Task(
                id=response.message_id,  # Use message ID as task ID
                agent_id=agent_id,
                skill=skill,
                parameters=parameters,
                metadata=metadata,
            )
            
            self._logger.info("Task created successfully", task_id=task.id)
            return task
            
        except Exception as e:
            self._logger.error(
                "Failed to create task",
                error=str(e),
                agent_id=agent_id,
                skill=skill
            )
            raise TaskError(f"Failed to create task: {e}")
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Get the status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskStatus object
            
        Raises:
            TaskNotFoundError: If task is not found
        """
        self._logger.debug("Getting task status", task_id=task_id)
        
        try:
            # For now, we'll use a simple approach since A2A SDK client
            # doesn't have a direct get_task method in the current implementation
            # In a full system, this would query the agent's task store
            raise TaskNotFoundError(f"Task status tracking not yet implemented: {task_id}")
            
            # Convert to our task status format
            labyrinth_task = Task.from_a2a_task(a2a_task)
            
            return TaskStatus(
                task_id=task_id,
                state=labyrinth_task.state,
                message=f"Task {labyrinth_task.state.value}",
            )
            
        except Exception as e:
            if "not found" in str(e).lower():
                raise TaskNotFoundError(f"Task not found: {task_id}")
            else:
                raise TaskError(f"Failed to get task status: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled successfully
            
        Raises:
            TaskNotFoundError: If task is not found
        """
        self._logger.info("Cancelling task", task_id=task_id)
        
        try:
            # For now, return False since task cancellation requires
            # additional A2A SDK integration
            self._logger.warning("Task cancellation not yet implemented", task_id=task_id)
            return False
            
            success = getattr(result, 'success', False)
            
            if success:
                self._logger.info("Task cancelled successfully", task_id=task_id)
            else:
                self._logger.warning("Task cancellation failed", task_id=task_id)
            
            return success
            
        except Exception as e:
            if "not found" in str(e).lower():
                raise TaskNotFoundError(f"Task not found: {task_id}")
            else:
                raise TaskError(f"Failed to cancel task: {e}")
    
    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        poll_interval: float = 1.0,
    ) -> TaskResult:
        """
        Wait for a task to complete.
        
        Args:
            task_id: Task identifier
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            TaskResult when task completes
            
        Raises:
            TaskTimeoutError: If timeout is reached
            TaskNotFoundError: If task is not found
        """
        timeout = timeout or self.config.task_default_timeout
        start_time = asyncio.get_event_loop().time()
        
        self._logger.info(
            "Waiting for task completion",
            task_id=task_id,
            timeout=timeout,
            poll_interval=poll_interval
        )
        
        while True:
            # Check if timeout reached
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TaskTimeoutError(f"Task {task_id} timed out after {timeout}s")
            
            # Get current status
            try:
                status = await self.get_task_status(task_id)
                
                if status.is_complete:
                    # Task completed - return result
                    return TaskResult(
                        task_id=task_id,
                        success=status.state.value == "completed",
                        result=None,  # Would need to fetch actual result
                        error=None if status.state.value == "completed" else "Task failed",
                    )
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                
            except TaskNotFoundError:
                raise
            except Exception as e:
                self._logger.warning(
                    "Error polling task status",
                    task_id=task_id,
                    error=str(e)
                )
                await asyncio.sleep(poll_interval)
    
    async def discover_agents(
        self,
        skill_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover available agents and their capabilities.
        
        Args:
            skill_filter: Filter agents by skill/capability
            limit: Maximum number of agents to return
            
        Returns:
            List of agent information dictionaries
        """
        self._logger.info("Discovering agents", skill_filter=skill_filter, limit=limit)
        
        try:
            # Use discovery service to list available agents
            agents = await self.discovery_service.list_available_agents()
            
            # Filter by skill if specified
            if skill_filter:
                filtered_agents = []
                for agent in agents:
                    if "skills" in agent and skill_filter in agent["skills"]:
                        filtered_agents.append(agent)
                agents = filtered_agents
            
            # Apply limit if specified
            if limit and limit > 0:
                agents = agents[:limit]
            
            self._logger.info(
                "Discovered agents",
                count=len(agents),
                skill_filter=skill_filter
            )
            
            return agents
            
        except Exception as e:
            self._logger.error("Failed to discover agents", error=str(e))
            return []
    
    async def close(self) -> None:
        """Close the client and cleanup resources."""
        # Close all cached A2A clients
        for agent_id, client in self._client_cache.items():
            try:
                if hasattr(client, 'close'):
                    await client.close()
            except Exception as e:
                self._logger.warning(
                    "Error closing A2A client",
                    agent_id=agent_id,
                    error=str(e)
                )
        
        self._client_cache.clear()
        
        if self._a2a_client:
            # Close main A2A client if it has a close method
            if hasattr(self._a2a_client, 'close'):
                await self._a2a_client.close()
        
        self._logger.info("AgentClient closed")
    
    async def __aenter__(self) -> "AgentClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
