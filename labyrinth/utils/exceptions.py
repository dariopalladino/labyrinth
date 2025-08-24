"""
Labyrinth exception classes for better error handling.
"""

from typing import Any, Dict, Optional


class LabyrinthError(Exception):
    """Base exception for all Labyrinth errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(LabyrinthError):
    """Raised when there's a configuration problem."""
    pass


class AgentError(LabyrinthError):
    """Base class for agent-related errors."""
    pass


class AgentNotFoundError(AgentError):
    """Raised when an agent cannot be found."""
    pass


class AgentStartupError(AgentError):
    """Raised when an agent fails to start."""
    pass


class CommunicationError(LabyrinthError):
    """Base class for communication-related errors."""
    pass


class MessageDeliveryError(CommunicationError):
    """Raised when a message cannot be delivered."""
    pass


class TaskError(LabyrinthError):
    """Base class for task-related errors."""
    pass


class TaskNotFoundError(TaskError):
    """Raised when a task cannot be found."""
    pass


class TaskTimeoutError(TaskError):
    """Raised when a task times out."""
    pass


class TaskCancellationError(TaskError):
    """Raised when a task cannot be cancelled."""
    pass


class AuthenticationError(LabyrinthError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(LabyrinthError):
    """Raised when authorization fails."""
    pass
