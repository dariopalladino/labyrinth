"""
Logging utilities for Labyrinth.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor

from labyrinth.utils.config import Config, get_config


def setup_logging(config: Optional[Config] = None) -> None:
    """
    Setup structured logging for Labyrinth.
    
    Args:
        config: Configuration object (uses global config if None)
    """
    config = config or get_config()
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Configure processors based on format
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if config.log_format.lower() == "json":
        processors.extend([
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ])
    else:
        processors.extend([
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer()
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """
    Get a configured logger with optional context.
    
    Args:
        name: Logger name
        **context: Additional context to bind
        
    Returns:
        Configured logger
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


def add_context(**context: Any) -> None:
    """
    Add context to all loggers in the current context.
    
    Args:
        **context: Context to add
    """
    for key, value in context.items():
        structlog.contextvars.bind_contextvars(**{key: value})


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = get_logger(self.__class__.__name__)
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get the logger for this instance."""
        return self._logger


# Setup logging on import
setup_logging()
