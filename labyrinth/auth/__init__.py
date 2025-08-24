"""
Authentication and authorization module for Labyrinth.

This module provides swappable authentication interfaces and implementations
for securing agent-to-agent communication and registry access.
"""

from .interfaces import (
    AuthenticationProvider,
    TokenValidator,
    AuthenticationCredentials,
    TokenInfo,
    ValidationResult,
)

from .providers.azure_entra import AzureEntraAuthProvider
from .validators import DefaultTokenValidator
from .middleware import AuthenticationMiddleware
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    InvalidScopeError,
)

__all__ = [
    # Interfaces
    "AuthenticationProvider",
    "TokenValidator", 
    "AuthenticationCredentials",
    "TokenInfo",
    "ValidationResult",
    
    # Implementations
    "AzureEntraAuthProvider",
    "DefaultTokenValidator",
    "AuthenticationMiddleware",
    
    # Exceptions
    "AuthenticationError",
    "AuthorizationError", 
    "TokenExpiredError",
    "InvalidScopeError",
]
