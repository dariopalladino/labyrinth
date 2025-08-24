"""
Configuration management for Labyrinth.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from labyrinth.utils.exceptions import ConfigurationError


class Config(BaseModel):
    """
    Configuration class for Labyrinth with environment variable support.
    """
    
    # A2A SDK Configuration
    a2a_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for A2A services"
    )
    a2a_api_key: Optional[str] = Field(
        default=None,
        description="API key for A2A authentication"
    )
    a2a_project_id: Optional[str] = Field(
        default=None,
        description="Google Cloud Project ID"
    )
    
    # Agent Configuration
    agent_name: Optional[str] = Field(
        default=None,
        description="Default agent name"
    )
    agent_description: Optional[str] = Field(
        default=None,
        description="Default agent description"
    )
    agent_port: int = Field(
        default=8080,
        description="Default port for agent server"
    )
    agent_host: str = Field(
        default="localhost",
        description="Default host for agent server"
    )
    
    # Communication Settings
    default_timeout: int = Field(
        default=30,
        description="Default timeout for requests in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed requests"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retry attempts in seconds"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    
    # Task Management
    task_default_timeout: int = Field(
        default=300,
        description="Default timeout for tasks in seconds"
    )
    task_cleanup_interval: int = Field(
        default=3600,
        description="Interval for task cleanup in seconds"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "LABYRINTH_"
        case_sensitive = False

    @classmethod
    def load_from_env(cls, env_file: Optional[Union[str, Path]] = None) -> "Config":
        """
        Load configuration from environment variables and optional .env file.
        
        Args:
            env_file: Optional path to .env file to load
            
        Returns:
            Config instance
        """
        # Load .env file if specified
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to load default .env files
            for env_path in [".env", ".env.local"]:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
        
        # Load configuration from environment variables
        config_data = {}
        
        # Map environment variables to config fields
        env_mapping = {
            "LABYRINTH_A2A_BASE_URL": "a2a_base_url",
            "LABYRINTH_A2A_API_KEY": "a2a_api_key", 
            "LABYRINTH_A2A_PROJECT_ID": "a2a_project_id",
            "LABYRINTH_AGENT_NAME": "agent_name",
            "LABYRINTH_AGENT_DESCRIPTION": "agent_description",
            "LABYRINTH_AGENT_PORT": "agent_port",
            "LABYRINTH_AGENT_HOST": "agent_host",
            "LABYRINTH_DEFAULT_TIMEOUT": "default_timeout",
            "LABYRINTH_RETRY_ATTEMPTS": "retry_attempts",
            "LABYRINTH_RETRY_DELAY": "retry_delay",
            "LABYRINTH_LOG_LEVEL": "log_level",
            "LABYRINTH_LOG_FORMAT": "log_format",
            "LABYRINTH_TASK_DEFAULT_TIMEOUT": "task_default_timeout",
            "LABYRINTH_TASK_CLEANUP_INTERVAL": "task_cleanup_interval",
        }
        
        for env_var, config_field in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_field in ["agent_port", "default_timeout", "retry_attempts", 
                                   "task_default_timeout", "task_cleanup_interval"]:
                    try:
                        value = int(value)
                    except ValueError:
                        raise ConfigurationError(
                            f"Invalid integer value for {env_var}: {value}"
                        )
                elif config_field == "retry_delay":
                    try:
                        value = float(value)
                    except ValueError:
                        raise ConfigurationError(
                            f"Invalid float value for {env_var}: {value}"
                        )
                
                config_data[config_field] = value
        
        return cls(**config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """
        Create configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Config instance
        """
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.dict()
    
    def validate_required(self, required_fields: Optional[list] = None) -> None:
        """
        Validate that required configuration fields are set.
        
        Args:
            required_fields: List of required field names
            
        Raises:
            ConfigurationError: If required fields are missing
        """
        if not required_fields:
            required_fields = []
            
        missing_fields = []
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ConfigurationError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config.load_from_env()
    return _global_config


def set_config(config: Config) -> None:
    """
    Set the global configuration instance.
    
    Args:
        config: Config instance to set as global
    """
    global _global_config
    _global_config = config


def reset_config() -> None:
    """Reset the global configuration to None."""
    global _global_config
    _global_config = None
