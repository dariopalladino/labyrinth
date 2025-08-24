"""
Authentication and authorization interfaces for Labyrinth.

This module defines the interfaces that authentication providers must implement,
allowing for swappable authentication backends through dependency injection.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Union
from enum import Enum


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class AuthenticationPendingError(AuthenticationError):
    """Exception raised when device flow authentication is pending."""
    pass


class AuthenticationTimeoutError(AuthenticationError):
    """Exception raised when authentication times out."""
    pass


class CredentialType(Enum):
    """Types of authentication credentials."""
    CLIENT_CREDENTIALS = "client_credentials"
    MANAGED_IDENTITY = "managed_identity"
    SERVICE_PRINCIPAL = "service_principal"
    AUTHORIZATION_CODE = "authorization_code"  # Interactive user flow
    DEVICE_CODE = "device_code"  # Device code flow for CLI


@dataclass
class AuthenticationCredentials:
    """Container for authentication credentials."""
    credential_type: CredentialType
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    resource_id: Optional[str] = None  # For managed identity
    certificate_path: Optional[str] = None  # For certificate-based auth
    
    def __post_init__(self):
        """Validate credentials based on type."""
        if self.credential_type == CredentialType.CLIENT_CREDENTIALS:
            if not self.client_id or not self.client_secret:
                raise ValueError("Client credentials require client_id and client_secret")
        elif self.credential_type == CredentialType.MANAGED_IDENTITY:
            if not self.client_id and not self.resource_id:
                raise ValueError("Managed identity requires either client_id or resource_id")


@dataclass
class TokenInfo:
    """Information about an access token."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    expires_at: Optional[float] = None
    scope: Optional[str] = None
    issued_at: Optional[float] = None
    
    def __post_init__(self):
        """Calculate expiration time if not provided."""
        if self.expires_in and not self.expires_at:
            self.expires_at = time.time() + self.expires_in
        if not self.issued_at:
            self.issued_at = time.time()
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return time.time() >= self.expires_at
    
    @property
    def scopes(self) -> Set[str]:
        """Get token scopes as a set."""
        if not self.scope:
            return set()
        return set(self.scope.split())
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope."""
        return required_scope in self.scopes


@dataclass
class ValidationResult:
    """Result of token validation."""
    is_valid: bool
    token_info: Optional[TokenInfo] = None
    principal_id: Optional[str] = None
    principal_name: Optional[str] = None
    error_message: Optional[str] = None
    scopes: Optional[Set[str]] = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if the request is authenticated."""
        return self.is_valid and self.token_info is not None
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if the validated token has a specific scope."""
        if not self.scopes:
            return False
        return required_scope in self.scopes


class AuthenticationProvider(ABC):
    """
    Abstract interface for authentication providers.
    
    This interface allows swapping between different identity providers
    (Azure Entra ID, Auth0, AWS Cognito, etc.) through dependency injection.
    """
    
    @abstractmethod
    async def authenticate(
        self,
        credentials: AuthenticationCredentials,
        scopes: Optional[List[str]] = None,
        resource: Optional[str] = None
    ) -> TokenInfo:
        """
        Authenticate and obtain an access token.
        
        Args:
            credentials: Authentication credentials
            scopes: Requested OAuth scopes
            resource: Target resource (for some providers)
            
        Returns:
            TokenInfo containing the access token and metadata
            
        Raises:
            AuthenticationError: When authentication fails
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, token_info: TokenInfo) -> TokenInfo:
        """
        Refresh an expired or expiring token.
        
        Args:
            token_info: Current token information
            
        Returns:
            New TokenInfo with refreshed token
            
        Raises:
            AuthenticationError: When refresh fails
        """
        pass
    
    @abstractmethod
    async def validate_token(self, access_token: str) -> ValidationResult:
        """
        Validate an access token.
        
        Args:
            access_token: The access token to validate
            
        Returns:
            ValidationResult with validation details
        """
        pass
    
    @abstractmethod
    async def get_token_info(self, access_token: str) -> Optional[TokenInfo]:
        """
        Get information about a token without full validation.
        
        Args:
            access_token: The access token to inspect
            
        Returns:
            TokenInfo if token can be parsed, None otherwise
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the authentication provider."""
        pass
    
    @property
    @abstractmethod
    def default_scopes(self) -> List[str]:
        """Default scopes for this provider."""
        pass


class TokenValidator(ABC):
    """
    Abstract interface for token validation.
    
    This allows for custom token validation logic beyond what the
    authentication provider offers.
    """
    
    @abstractmethod
    async def validate(
        self,
        access_token: str,
        required_scopes: Optional[Set[str]] = None,
        additional_claims: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Validate an access token with custom logic.
        
        Args:
            access_token: The token to validate
            required_scopes: Scopes that must be present
            additional_claims: Additional claims to verify
            
        Returns:
            ValidationResult with validation details
        """
        pass
    
    @abstractmethod
    async def extract_claims(self, access_token: str) -> Dict[str, Union[str, int, List[str]]]:
        """
        Extract claims from a token.
        
        Args:
            access_token: The token to parse
            
        Returns:
            Dictionary of token claims
        """
        pass


@dataclass
class InteractiveAuthResult:
    """Result of interactive authentication flow."""
    token_info: TokenInfo
    user_info: Optional[Dict[str, str]] = None
    refresh_token: Optional[str] = None
    

class InteractiveAuthenticationProvider(ABC):
    """
    Abstract interface for interactive authentication providers.
    
    This supports authorization code flow with PKCE and device code flow
    for CLI applications and user authentication.
    """
    
    @abstractmethod
    async def start_interactive_auth(
        self,
        client_id: str,
        tenant_id: str,
        scopes: List[str],
        redirect_uri: Optional[str] = None
    ) -> str:
        """
        Start interactive authentication flow.
        
        Args:
            client_id: OAuth client ID
            tenant_id: Azure tenant ID
            scopes: Requested OAuth scopes
            redirect_uri: Redirect URI for auth code flow
            
        Returns:
            Authorization URL for user to visit
        """
        pass
    
    @abstractmethod
    async def complete_interactive_auth(
        self,
        auth_code: Optional[str] = None,
        device_code: Optional[str] = None
    ) -> InteractiveAuthResult:
        """
        Complete interactive authentication flow.
        
        Args:
            auth_code: Authorization code from callback
            device_code: Device code for device flow
            
        Returns:
            InteractiveAuthResult with tokens and user info
        """
        pass
    
    @abstractmethod
    async def start_device_flow(
        self,
        client_id: str,
        tenant_id: str,
        scopes: List[str]
    ) -> Dict[str, str]:
        """
        Start device code flow for CLI authentication.
        
        Args:
            client_id: OAuth client ID
            tenant_id: Azure tenant ID
            scopes: Requested OAuth scopes
            
        Returns:
            Dictionary with device_code, user_code, verification_uri, etc.
        """
        pass
    
    @abstractmethod
    async def poll_device_flow(
        self,
        device_code: str,
        client_id: str,
        tenant_id: str
    ) -> InteractiveAuthResult:
        """
        Poll for device flow completion.
        
        Args:
            device_code: Device code from start_device_flow
            client_id: OAuth client ID
            tenant_id: Azure tenant ID
            
        Returns:
            InteractiveAuthResult when user completes authentication
            
        Raises:
            AuthenticationPendingError: When user hasn't completed auth yet
            AuthenticationError: When authentication fails
        """
        pass


class TokenCache(ABC):
    """
    Abstract interface for token caching.
    
    This allows for different caching strategies (in-memory, Redis, etc.)
    """
    
    @abstractmethod
    async def get_token(self, cache_key: str) -> Optional[TokenInfo]:
        """Get cached token by key."""
        pass
    
    @abstractmethod
    async def set_token(self, cache_key: str, token_info: TokenInfo, ttl: Optional[int] = None) -> None:
        """Cache token with optional TTL."""
        pass
    
    @abstractmethod
    async def remove_token(self, cache_key: str) -> None:
        """Remove token from cache."""
        pass
    
    @abstractmethod
    async def clear_expired_tokens(self) -> int:
        """Remove expired tokens, return count removed."""
        pass
