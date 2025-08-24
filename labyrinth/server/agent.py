"""
Agent - High-level class for creating and managing A2A agents.
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Union

import structlog
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPI
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a import types as a2a_types

from labyrinth.types.messages import Message, MessageResponse
from labyrinth.types.tasks import Task, TaskState
from labyrinth.utils.config import Config, get_config
from labyrinth.utils.exceptions import (
    LabyrinthError,
    AgentError,
    AgentStartupError,
    ConfigurationError,
)

logger = structlog.get_logger(__name__)


class LabyrinthAgentExecutor(AgentExecutor):
    """Custom AgentExecutor implementation for Labyrinth agents."""
    
    def __init__(self, agent: "Agent"):
        self.agent = agent
    
    async def execute(self, request) -> Any:
        """Execute a skill request."""
        # Extract skill name and message from A2A request
        skill_name = getattr(request, 'skill', None)
        message = getattr(request, 'message', None)
        
        if message and skill_name:
            return await self.agent._handle_message(message, skill_name)
        elif message:
            return await self.agent._handle_message(message)
        else:
            raise ValueError("No message provided in request")
    
    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        # For now, return False as we don't support task cancellation
        # In a full implementation, this would cancel the specific task
        return False


class Skill:
    """Represents an agent skill/capability."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.description = description or func.__doc__ or f"Skill: {name}"
        self.parameters_schema = parameters_schema or self._extract_schema()
        
    def _extract_schema(self) -> Dict[str, Any]:
        """Extract parameter schema from function signature."""
        sig = inspect.signature(self.func)
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name in ["self", "message", "context"]:
                continue
                
            param_info = {"type": "string"}  # Default type
            
            if param.annotation != inspect.Parameter.empty:
                # Map Python types to JSON schema types
                type_mapping = {
                    str: "string",
                    int: "integer", 
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                param_info["type"] = type_mapping.get(param.annotation, "string")
            
            schema["properties"][param_name] = param_info
            
            if param.default == inspect.Parameter.empty:
                schema["required"].append(param_name)
        
        return schema


class Agent:
    """
    High-level agent class for creating and managing A2A agents.
    
    This class provides a simplified interface for:
    - Defining agent capabilities (skills)
    - Handling incoming messages and requests
    - Managing agent lifecycle
    """
    
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        config: Optional[Config] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize Agent.
        
        Args:
            name: Agent name/identifier
            description: Agent description
            config: Configuration object (uses global config if None)
            host: Host to bind to (overrides config)
            port: Port to bind to (overrides config)
        """
        self.name = name
        self.id = name  # Use name as ID for simplicity
        self.description = description or f"Labyrinth agent: {name}"
        self.config = config or get_config()
        
        self.host = host or self.config.agent_host
        self.port = port or self.config.agent_port
        
        self._skills: Dict[str, Skill] = {}
        self._app: Optional[A2AFastAPI] = None
        self._request_handler: Optional[DefaultRequestHandler] = None
        self._agent_executor: Optional[AgentExecutor] = None
        self._task_store: Optional[InMemoryTaskStore] = None
        self._queue_manager: Optional[InMemoryQueueManager] = None
        self._running = False
        
        self._logger = logger.bind(agent_name=name)
        
    def skill(
        self,
        name: str,
        description: Optional[str] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """
        Decorator to register a skill/capability with the agent.
        
        Args:
            name: Skill name
            description: Skill description
            parameters_schema: JSON schema for parameters
            
        Returns:
            Decorator function
            
        Example:
            @agent.skill("greet")
            async def greet_user(name: str) -> str:
                return f"Hello, {name}!"
        """
        def decorator(func: Callable) -> Callable:
            skill = Skill(
                name=name,
                func=func,
                description=description,
                parameters_schema=parameters_schema,
            )
            self._skills[name] = skill
            self._logger.info(f"Registered skill: {name}")
            return func
        
        return decorator
    
    def add_skill(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a skill to the agent programmatically.
        
        Args:
            name: Skill name
            func: Skill function
            description: Skill description
            parameters_schema: JSON schema for parameters
        """
        skill = Skill(
            name=name,
            func=func,
            description=description,
            parameters_schema=parameters_schema,
        )
        self._skills[name] = skill
        self._logger.info(f"Added skill: {name}")
    
    def get_skills(self) -> Dict[str, Skill]:
        """Get all registered skills."""
        return self._skills.copy()
    
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """
        Get agent capabilities in A2A format.
        
        Returns:
            List of capability dictionaries
        """
        capabilities = []
        
        for skill in self._skills.values():
            capabilities.append({
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.parameters_schema,
            })
        
        return capabilities
    
    def get_agent_card(self) -> a2a_types.AgentCard:
        """Get the agent card for this agent."""
        return self._create_agent_card()
    
    async def _handle_message(
        self,
        message: a2a_types.Message,
        skill_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> a2a_types.Message:
        """
        Handle incoming message.
        
        Args:
            message: A2A message
            skill_name: Requested skill name
            context: Request context
            
        Returns:
            Response message
        """
        self._logger.info(
            "Handling message",
            skill=skill_name,
            parts_count=len(message.parts)
        )
        
        try:
            # Convert A2A message to Labyrinth format
            labyrinth_message = Message.from_a2a_message(message)
            
            # Find and execute skill
            if skill_name and skill_name in self._skills:
                skill = self._skills[skill_name]
                
                # Extract parameters from message
                parameters = {}
                if isinstance(labyrinth_message.content, str):
                    # Simple text message - try to parse as parameters
                    try:
                        import json
                        parameters = json.loads(labyrinth_message.content)
                    except:
                        parameters = {"input": labyrinth_message.content}
                elif isinstance(labyrinth_message.content, list):
                    # Multi-part message - extract structured data
                    for part in labyrinth_message.content:
                        if hasattr(part, 'data'):
                            parameters.update(part.data)
                
                # Execute skill
                if inspect.iscoroutinefunction(skill.func):
                    result = await skill.func(**parameters)
                else:
                    result = skill.func(**parameters)
                
                # Create response message
                response_text = str(result) if result is not None else "Success"
                response = Message.text(response_text, role=labyrinth_message.role)
                
            else:
                # No skill specified or skill not found
                available_skills = list(self._skills.keys())
                response_text = f"Available skills: {', '.join(available_skills)}"
                response = Message.text(response_text)
            
            return response.to_a2a_message()
            
        except Exception as e:
            self._logger.error(
                "Error handling message",
                error=str(e),
                skill=skill_name
            )
            
            error_response = Message.text(f"Error: {e}")
            return error_response.to_a2a_message()
    
    async def _setup_a2a_app(self) -> None:
        """Setup the underlying A2A application."""
        try:
            # Create required A2A components
            self._task_store = InMemoryTaskStore()
            self._queue_manager = InMemoryQueueManager()
            
            # Create our custom agent executor that handles Labyrinth skills
            self._agent_executor = LabyrinthAgentExecutor(self)
            
            # Create request handler with required dependencies
            self._request_handler = DefaultRequestHandler(
                agent_executor=self._agent_executor,
                task_store=self._task_store,
                queue_manager=self._queue_manager
            )
            
            # Create A2A FastAPI application
            self._app = A2AFastAPI(
                agent_card=self._create_agent_card(),
                request_handler=self._request_handler,
            )
            
        except Exception as e:
            raise AgentStartupError(f"Failed to setup A2A application: {e}")
    
    def _create_agent_card(self) -> a2a_types.AgentCard:
        """Create agent card for A2A registration."""
        # Convert skills to A2A capabilities format
        skills = []
        for skill in self._skills.values():
            a2a_skill = a2a_types.AgentSkill(
                id=f"{self.name}_{skill.name}",
                name=skill.name,
                description=skill.description,
                tags=["labyrinth", "agent"],  # Default tags
            )
            skills.append(a2a_skill)
        
        # Create agent capabilities
        capabilities = a2a_types.AgentCapabilities(
            skills=skills,
        )
        
        return a2a_types.AgentCard(
            name=self.name,
            description=self.description,
            version="1.0.0",
            url=f"http://{self.host}:{self.port}",
            skills=skills,
            capabilities=capabilities,
            default_input_modes=["text"],
            default_output_modes=["text"],
        )
    
    async def start(self) -> None:
        """
        Start the agent server.
        
        Raises:
            AgentStartupError: If agent fails to start
        """
        if self._running:
            self._logger.warning("Agent is already running")
            return
        
        self._logger.info(
            "Starting agent",
            host=self.host,
            port=self.port,
            skills=list(self._skills.keys())
        )
        
        try:
            # Setup A2A application
            await self._setup_a2a_app()
            
            # Start the server
            # Note: The exact startup method depends on A2A SDK implementation
            # This is a simplified example
            
            self._running = True
            self._logger.info("Agent started successfully")
            
        except Exception as e:
            self._running = False
            self._logger.error("Failed to start agent", error=str(e))
            raise AgentStartupError(f"Agent startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop the agent server."""
        if not self._running:
            self._logger.warning("Agent is not running")
            return
        
        self._logger.info("Stopping agent")
        
        try:
            # Stop the A2A application
            if self._app:
                # Stop method would depend on A2A SDK implementation
                pass
            
            self._running = False
            self._logger.info("Agent stopped successfully")
            
        except Exception as e:
            self._logger.error("Error stopping agent", error=str(e))
            raise AgentError(f"Agent stop failed: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running
    
    async def __aenter__(self) -> "Agent":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
