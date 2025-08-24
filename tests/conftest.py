"""
Pytest configuration and fixtures for Labyrinth tests.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from labyrinth.utils.config import Config, reset_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        a2a_base_url="http://localhost:8080",
        a2a_api_key="test_api_key",
        a2a_project_id="test_project",
        agent_name="test-agent",
        agent_description="Test agent",
        agent_port=8080,
        agent_host="localhost",
        default_timeout=10,
        retry_attempts=2,
        retry_delay=0.1,
        log_level="DEBUG",
        log_format="text",
        task_default_timeout=60,
        task_cleanup_interval=300,
    )


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset global configuration after each test."""
    yield
    reset_config()


@pytest.fixture
def mock_a2a_client():
    """Create a mock A2A client."""
    mock = AsyncMock()
    mock.send_message = AsyncMock()
    mock.get_task = AsyncMock()
    mock.cancel_task = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def sample_message_data():
    """Sample message data for tests."""
    return {
        "content": "Hello, world!",
        "role": "user",
        "metadata": {"source": "test"},
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "id": "test-task-123",
        "agent_id": "test-agent", 
        "skill": "test_skill",
        "parameters": {"param1": "value1"},
        "state": "pending",
    }
