"""
Tests for Labyrinth configuration.
"""

import os
import pytest
import tempfile
from pathlib import Path

from labyrinth.utils.config import Config, get_config, set_config, reset_config
from labyrinth.utils.exceptions import ConfigurationError


class TestConfig:
    """Tests for Config class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.agent_port == 8080
        assert config.agent_host == "localhost"
        assert config.default_timeout == 30
        assert config.retry_attempts == 3
        assert config.log_level == "INFO"
        assert config.log_format == "json"
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "a2a_api_key": "test_key",
            "agent_name": "test-agent",
            "agent_port": 9000,
            "log_level": "DEBUG"
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.a2a_api_key == "test_key"
        assert config.agent_name == "test-agent"
        assert config.agent_port == 9000
        assert config.log_level == "DEBUG"
        # Ensure defaults are still set
        assert config.retry_attempts == 3
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config(
            a2a_api_key="test_key",
            agent_name="test-agent"
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["a2a_api_key"] == "test_key"
        assert config_dict["agent_name"] == "test-agent"
        assert "agent_port" in config_dict
    
    def test_validate_required_fields(self):
        """Test validation of required fields."""
        config = Config()
        
        # Should not raise error for empty required fields list
        config.validate_required([])
        
        # Should raise error for missing required fields
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate_required(["a2a_api_key", "a2a_project_id"])
        
        assert "Missing required configuration fields" in str(exc_info.value)
        assert "a2a_api_key" in str(exc_info.value)
    
    def test_load_from_env_file(self):
        """Test loading configuration from environment file."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("LABYRINTH_A2A_API_KEY=env_test_key\n")
            f.write("LABYRINTH_AGENT_PORT=9999\n")
            f.write("LABYRINTH_LOG_LEVEL=DEBUG\n")
            env_file = f.name
        
        try:
            config = Config.load_from_env(env_file)
            
            assert config.a2a_api_key == "env_test_key"
            assert config.agent_port == 9999
            assert config.log_level == "DEBUG"
            
        finally:
            os.unlink(env_file)
    
    def test_load_from_env_variables(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        env_vars = {
            "LABYRINTH_A2A_BASE_URL": "http://test.example.com",
            "LABYRINTH_AGENT_NAME": "env-test-agent",
            "LABYRINTH_DEFAULT_TIMEOUT": "60",
            "LABYRINTH_RETRY_DELAY": "2.5"
        }
        
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config.load_from_env()
            
            assert config.a2a_base_url == "http://test.example.com"
            assert config.agent_name == "env-test-agent"
            assert config.default_timeout == 60
            assert config.retry_delay == 2.5
            
        finally:
            # Clean up environment variables
            for key in env_vars.keys():
                os.environ.pop(key, None)
    
    def test_invalid_env_values(self):
        """Test handling of invalid environment variable values."""
        os.environ["LABYRINTH_AGENT_PORT"] = "not_a_number"
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Config.load_from_env()
            
            assert "Invalid integer value" in str(exc_info.value)
            
        finally:
            os.environ.pop("LABYRINTH_AGENT_PORT", None)


class TestGlobalConfig:
    """Tests for global configuration management."""
    
    def test_get_config(self):
        """Test getting global configuration."""
        config = get_config()
        assert isinstance(config, Config)
    
    def test_set_config(self):
        """Test setting global configuration."""
        test_config = Config(agent_name="global-test-agent")
        set_config(test_config)
        
        retrieved_config = get_config()
        assert retrieved_config.agent_name == "global-test-agent"
    
    def test_reset_config(self):
        """Test resetting global configuration."""
        # Set a custom config
        test_config = Config(agent_name="reset-test-agent")
        set_config(test_config)
        
        # Verify it's set
        assert get_config().agent_name == "reset-test-agent"
        
        # Reset and verify new instance is created
        reset_config()
        new_config = get_config()
        assert new_config.agent_name is None  # Default value
