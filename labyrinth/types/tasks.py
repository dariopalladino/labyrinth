"""
Task types for Labyrinth.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from a2a import types as a2a_types


class TaskState(str, Enum):
    """Task state enumeration."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """
    High-level task representation.
    """
    
    id: str = Field(..., description="Unique task identifier")
    agent_id: str = Field(..., description="Target agent ID")
    skill: str = Field(..., description="Skill/capability to invoke")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task parameters"
    )
    state: TaskState = Field(
        default=TaskState.PENDING,
        description="Current task state"
    )
    result: Optional[Any] = Field(
        None,
        description="Task result (when completed)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message (when failed)"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Task creation timestamp"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="Task start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Task completion timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata"
    )
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
    
    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.state == TaskState.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if task completed successfully."""
        return self.state == TaskState.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed."""
        return self.state == TaskState.FAILED
    
    @property
    def is_cancelled(self) -> bool:
        """Check if task was cancelled."""
        return self.state == TaskState.CANCELLED
    
    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds if started."""
        if not self.started_at:
            return None
            
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_a2a_task(self) -> a2a_types.Task:
        """
        Convert to A2A SDK Task format.
        
        Returns:
            A2A SDK Task instance
        """
        # Map our states to A2A states
        state_mapping = {
            TaskState.PENDING: a2a_types.TaskState.PENDING,
            TaskState.RUNNING: a2a_types.TaskState.RUNNING,
            TaskState.COMPLETED: a2a_types.TaskState.COMPLETED,
            TaskState.FAILED: a2a_types.TaskState.FAILED,
            TaskState.CANCELLED: a2a_types.TaskState.CANCELLED,
        }
        
        return a2a_types.Task(
            id=self.id,
            state=state_mapping[self.state],
            # Add other A2A task fields as needed
        )
    
    @classmethod
    def from_a2a_task(cls, a2a_task: a2a_types.Task, agent_id: str = "", skill: str = "") -> "Task":
        """
        Create Task from A2A SDK Task.
        
        Args:
            a2a_task: A2A SDK Task instance
            agent_id: Agent ID (may not be in A2A task)
            skill: Skill name (may not be in A2A task)
            
        Returns:
            Task instance
        """
        # Map A2A states to our states
        state_mapping = {
            a2a_types.TaskState.PENDING: TaskState.PENDING,
            a2a_types.TaskState.RUNNING: TaskState.RUNNING,
            a2a_types.TaskState.COMPLETED: TaskState.COMPLETED,
            a2a_types.TaskState.FAILED: TaskState.FAILED,
            a2a_types.TaskState.CANCELLED: TaskState.CANCELLED,
        }
        
        return cls(
            id=a2a_task.id,
            agent_id=agent_id,
            skill=skill,
            state=state_mapping.get(a2a_task.state, TaskState.PENDING),
        )


class TaskStatus(BaseModel):
    """
    Task status information.
    """
    
    task_id: str = Field(..., description="Task identifier")
    state: TaskState = Field(..., description="Current task state")
    progress: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Task progress (0.0 to 1.0)"
    )
    message: Optional[str] = Field(
        None,
        description="Status message"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Status update timestamp"
    )
    
    @property
    def is_complete(self) -> bool:
        """Check if task is complete (success or failure)."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
    
    @property
    def is_active(self) -> bool:
        """Check if task is actively running."""
        return self.state in [TaskState.PENDING, TaskState.RUNNING]


class TaskResult(BaseModel):
    """
    Task execution result.
    """
    
    task_id: str = Field(..., description="Task identifier")
    success: bool = Field(..., description="Whether task succeeded")
    result: Optional[Any] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: Optional[float] = Field(
        None,
        description="Execution time in seconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Result metadata"
    )
    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="Completion timestamp"
    )


class TaskProgress(BaseModel):
    """
    Task progress update.
    """
    
    task_id: str = Field(..., description="Task identifier")
    progress: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Progress percentage (0.0 to 1.0)"
    )
    message: Optional[str] = Field(
        None,
        description="Progress message"
    )
    current_step: Optional[str] = Field(
        None,
        description="Current processing step"
    )
    total_steps: Optional[int] = Field(
        None,
        description="Total number of steps"
    )
    current_step_index: Optional[int] = Field(
        None,
        description="Current step index"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Update timestamp"
    )


class TaskFilter(BaseModel):
    """
    Filter criteria for task queries.
    """
    
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    skill: Optional[str] = Field(None, description="Filter by skill")
    state: Optional[TaskState] = Field(None, description="Filter by state")
    created_after: Optional[datetime] = Field(
        None,
        description="Filter tasks created after this time"
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Filter tasks created before this time"
    )
    limit: Optional[int] = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results"
    )
