"""
Tests for Labyrinth types.
"""

import pytest
from datetime import datetime

from labyrinth.types.messages import Message, MessageResponse, MessageRole, TextPart
from labyrinth.types.tasks import Task, TaskState, TaskStatus, TaskResult


class TestMessage:
    """Tests for Message class."""
    
    def test_create_text_message(self):
        """Test creating a simple text message."""
        message = Message.text("Hello, world!")
        
        assert message.content == "Hello, world!"
        assert message.role == MessageRole.USER
        assert isinstance(message.metadata, dict)
    
    def test_create_message_with_role(self):
        """Test creating a message with specific role."""
        message = Message.text("Assistant response", role=MessageRole.ASSISTANT)
        
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Assistant response"
    
    def test_message_with_parts(self):
        """Test creating a message with multiple parts."""
        parts = [TextPart(content="Hello"), TextPart(content="World")]
        message = Message(content=parts)
        
        assert len(message.content) == 2
        assert message.content[0].content == "Hello"
        assert message.content[1].content == "World"
    
    def test_file_message(self):
        """Test creating a file message."""
        message = Message.file(
            filename="test.txt",
            file_uri="http://example.com/test.txt",
            mime_type="text/plain"
        )
        
        assert len(message.content) == 1
        file_part = message.content[0]
        assert file_part.filename == "test.txt"
        assert file_part.file_uri == "http://example.com/test.txt"
        assert file_part.mime_type == "text/plain"


class TestMessageResponse:
    """Tests for MessageResponse class."""
    
    def test_success_response(self):
        """Test creating a successful message response."""
        response = MessageResponse(
            message_id="test-123",
            status="success",
            content="Response content"
        )
        
        assert response.message_id == "test-123"
        assert response.status == "success"
        assert response.content == "Response content"
        assert response.is_success
        assert not response.is_error
    
    def test_error_response(self):
        """Test creating an error message response."""
        response = MessageResponse(
            message_id="test-456",
            status="error",
            error="Something went wrong"
        )
        
        assert response.message_id == "test-456"
        assert response.status == "error"
        assert response.error == "Something went wrong"
        assert not response.is_success
        assert response.is_error


class TestTask:
    """Tests for Task class."""
    
    def test_create_task(self, sample_task_data):
        """Test creating a task."""
        task = Task(**sample_task_data)
        
        assert task.id == "test-task-123"
        assert task.agent_id == "test-agent"
        assert task.skill == "test_skill"
        assert task.state == TaskState.PENDING
        assert not task.is_terminal
        assert not task.is_running
    
    def test_task_properties(self):
        """Test task state properties."""
        task = Task(
            id="test-task",
            agent_id="test-agent",
            skill="test_skill",
            state=TaskState.COMPLETED
        )
        
        assert task.is_completed
        assert task.is_terminal
        assert not task.is_running
        assert not task.is_failed
    
    def test_task_with_timestamps(self):
        """Test task with start and completion timestamps."""
        started_at = datetime.now()
        task = Task(
            id="test-task",
            agent_id="test-agent", 
            skill="test_skill",
            state=TaskState.COMPLETED,
            started_at=started_at
        )
        
        assert task.started_at == started_at
        assert task.duration is not None
        assert task.duration >= 0


class TestTaskStatus:
    """Tests for TaskStatus class."""
    
    def test_task_status(self):
        """Test creating task status."""
        status = TaskStatus(
            task_id="test-task",
            state=TaskState.RUNNING,
            progress=0.5,
            message="Processing..."
        )
        
        assert status.task_id == "test-task"
        assert status.state == TaskState.RUNNING
        assert status.progress == 0.5
        assert status.message == "Processing..."
        assert not status.is_complete
        assert status.is_active
    
    def test_completed_task_status(self):
        """Test completed task status."""
        status = TaskStatus(
            task_id="test-task",
            state=TaskState.COMPLETED,
            progress=1.0
        )
        
        assert status.is_complete
        assert not status.is_active


class TestTaskResult:
    """Tests for TaskResult class."""
    
    def test_successful_result(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="test-task",
            success=True,
            result={"answer": 42},
            execution_time=1.5
        )
        
        assert result.task_id == "test-task"
        assert result.success
        assert result.result == {"answer": 42}
        assert result.execution_time == 1.5
        assert result.error is None
    
    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="test-task",
            success=False,
            error="Task failed",
            execution_time=0.5
        )
        
        assert result.task_id == "test-task"
        assert not result.success
        assert result.error == "Task failed"
        assert result.execution_time == 0.5
        assert result.result is None
