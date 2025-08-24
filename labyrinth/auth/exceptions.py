"""
Authentication and authorization exceptions.
"""

from labyrinth.utils.exceptions import LabyrinthError


class AuthenticationError(LabyrinthError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(LabyrinthError):
    """Raised when authorization fails (e.g., insufficient permissions)."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid or malformed."""
    pass


class InvalidScopeError(AuthorizationError):
    """Raised when required scopes are not present in the token."""
    pass


class ProviderConfigurationError(AuthenticationError):
    """Raised when authentication provider is misconfigured."""
    pass


class ManagedIdentityError(AuthenticationError):
    """Raised when managed identity authentication fails."""
    pass
