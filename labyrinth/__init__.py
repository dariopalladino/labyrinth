"""
Labyrinth - High-level Python API wrapper for Google's A2A SDK

Labyrinth simplifies agent-to-agent communication by providing an intuitive,
high-level interface around Google's A2A (Agent-to-Agent) SDK.
"""

__version__ = "0.1.0"
__author__ = "Labyrinth Team"
__email__ = "info@labyrinth.dev"
__description__ = "High-level Python API wrapper for Google's A2A SDK"

# Core imports for easy access
from labyrinth.client.agent_client import AgentClient
from labyrinth.server.agent import Agent
from labyrinth.types.messages import Message, MessageResponse
from labyrinth.types.tasks import Task, TaskStatus
from labyrinth.utils.config import Config
from labyrinth.utils.exceptions import LabyrinthError

__all__ = [
    # Core classes
    "Agent",
    "AgentClient",
    
    # Types
    "Message", 
    "MessageResponse",
    "Task",
    "TaskStatus",
    
    # Utils
    "Config",
    "LabyrinthError",
    
    # Version info
    "__version__",
]
