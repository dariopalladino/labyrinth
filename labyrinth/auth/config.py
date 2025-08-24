"""
Authentication configuration for Labyrinth.

This module provides configuration classes and utilities for setting up
authentication providers and validators from configuration files or
environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Any, Union
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from labyrinth.utils.config import Config, get_config
from .interfaces import AuthenticationProvider, TokenValidator, CredentialType
from .exceptions import ProviderConfigurationError

logger = structlog.get_logger(__name__)


class AuthProviderType(Enum):
    """Supported authentication provider types."""
    AZURE_ENTRA_ID = "azure_entra_id"
    SCOPE_ONLY = "scope_only"  # For development/testing
    CUSTOM = "custom"


class AuthConfig(BaseModel):
    """
    Authentication configuration.
    
    This configuration can be loaded from environment variables,
    configuration files, or created programmatically.
    """
    
    # General authentication settings
    enabled: bool = Field(default=True, description="Whether authentication is enabled")
    required_scope: str = Field(default="agentic_ai_solution", description="Default required scope")
    provider_type: AuthProviderType = Field(default=AuthProviderType.AZURE_ENTRA_ID, description="Authentication provider type")
    
    # Token settings
    token_cache_ttl: int = Field(default=3600, description="Token cache TTL in seconds")
    token_refresh_threshold: int = Field(default=300, description="Refresh threshold in seconds")
    allow_expired_grace_period: int = Field(default=60, description="Grace period for expired tokens")
    
    # Azure Entra ID settings
    azure_tenant_id: Optional[str] = Field(default=None, description="Azure tenant ID")
    azure_client_id: Optional[str] = Field(default=None, description="Azure client ID")
    azure_client_secret: Optional[str] = Field(default=None, description="Azure client secret")
    azure_authority_url: Optional[str] = Field(default=None, description="Azure authority URL")
    
    # Managed Identity settings
    use_managed_identity: bool = Field(default=False, description="Use managed identity")
    managed_identity_client_id: Optional[str] = Field(default=None, description="User-assigned managed identity client ID")
    
    # HTTPS settings
    require_https: bool = Field(default=False, description="Require HTTPS for authentication")
    
    # Registry-specific settings
    registry_auth_enabled: bool = Field(default=True, description="Enable authentication for registry")
    registry_protected_paths: List[str] = Field(default_factory=lambda: ["/agents/", "/stats"], description="Registry paths requiring authentication")
    registry_exclude_paths: List[str] = Field(default_factory=lambda: ["/", "/health", "/docs", "/redoc", "/openapi.json"], description="Registry paths excluded from authentication")
    
    # Agent-specific settings
    agent_auth_enabled: bool = Field(default=True, description="Enable authentication for agents")
    agent_protected_paths: List[str] = Field(default_factory=lambda: ["/messages/", "/tasks/"], description="Agent paths requiring authentication")
    
    @classmethod
    def from_env(cls, prefix: str = "LABYRINTH_AUTH_") -> "AuthConfig":
        """
        Create configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            
        Returns:
            AuthConfig instance
        """
        config_dict = {}
        
        # Map environment variables to config fields
        env_mapping = {
            "ENABLED": "enabled",
            "REQUIRED_SCOPE": "required_scope",
            "PROVIDER_TYPE": "provider_type",
            "TOKEN_CACHE_TTL": "token_cache_ttl",
            "TOKEN_REFRESH_THRESHOLD": "token_refresh_threshold",
            "ALLOW_EXPIRED_GRACE_PERIOD": "allow_expired_grace_period",
            "AZURE_TENANT_ID": "azure_tenant_id",
            "AZURE_CLIENT_ID": "azure_client_id",
            "AZURE_CLIENT_SECRET": "azure_client_secret",
            "AZURE_AUTHORITY_URL": "azure_authority_url",
            "USE_MANAGED_IDENTITY": "use_managed_identity",
            "MANAGED_IDENTITY_CLIENT_ID": "managed_identity_client_id",
            "REQUIRE_HTTPS": "require_https",
            "REGISTRY_AUTH_ENABLED": "registry_auth_enabled",
            "AGENT_AUTH_ENABLED": "agent_auth_enabled",
        }
        
        for env_key, config_key in env_mapping.items():
            env_var = f"{prefix}{env_key}"
            value = os.getenv(env_var)
            
            if value is not None:
                # Type conversion
                field_info = cls.model_fields.get(config_key)
                if field_info:
                    field_type = field_info.type_
                    if field_type == bool:
                        config_dict[config_key] = value.lower() in ("true", "1", "yes", "on")
                    elif field_type == int:
                        config_dict[config_key] = int(value)
                    elif field_type == AuthProviderType:
                        config_dict[config_key] = AuthProviderType(value)
                    else:
                        config_dict[config_key] = value
        
        return cls(**config_dict)
    
    def get_credentials(self) -> Optional["AuthenticationCredentials"]:
        """
        Get authentication credentials from configuration.
        
        Returns:
            AuthenticationCredentials if properly configured
        """
        from .interfaces import AuthenticationCredentials
        
        if not self.enabled:
            return None
        
        if self.use_managed_identity:
            return AuthenticationCredentials(
                credential_type=CredentialType.MANAGED_IDENTITY,
                client_id=self.managed_identity_client_id,
            )
        elif self.azure_client_id and self.azure_client_secret and self.azure_tenant_id:
            return AuthenticationCredentials(
                credential_type=CredentialType.CLIENT_CREDENTIALS,
                client_id=self.azure_client_id,
                client_secret=self.azure_client_secret,
                tenant_id=self.azure_tenant_id,
            )
        else:
            return None


class AuthConfigurationManager:
    """
    Manager for creating authentication providers and validators from configuration.
    
    This class provides factory methods for setting up authentication
    components based on configuration.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize configuration manager.
        
        Args:
            config: Base configuration object
        """
        self.config = config or get_config()
        self._logger = logger.bind(component="auth_config")
    
    def create_auth_provider(self, auth_config: AuthConfig) -> Optional[AuthenticationProvider]:
        """
        Create authentication provider from configuration.
        
        Args:
            auth_config: Authentication configuration
            
        Returns:
            Configured authentication provider or None if disabled
        """
        if not auth_config.enabled:
            return None
        
        try:
            if auth_config.provider_type == AuthProviderType.AZURE_ENTRA_ID:
                return self._create_azure_provider(auth_config)
            elif auth_config.provider_type == AuthProviderType.SCOPE_ONLY:
                return self._create_scope_only_provider(auth_config)
            else:
                raise ProviderConfigurationError(f"Unsupported provider type: {auth_config.provider_type}")
                
        except Exception as e:
            self._logger.error("Failed to create auth provider", error=str(e), provider_type=auth_config.provider_type.value)
            raise ProviderConfigurationError(f"Failed to create auth provider: {e}")
    
    def create_token_validator(self, auth_config: AuthConfig) -> Optional[TokenValidator]:
        """
        Create token validator from configuration.
        
        Args:
            auth_config: Authentication configuration
            
        Returns:
            Configured token validator or None if disabled
        """
        if not auth_config.enabled:
            return None
        
        auth_provider = self.create_auth_provider(auth_config)
        if not auth_provider:
            return None
        
        try:
            if auth_config.provider_type == AuthProviderType.AZURE_ENTRA_ID:
                from .validators import DefaultTokenValidator
                
                validator = DefaultTokenValidator(
                    auth_provider=auth_provider,
                    required_scope=auth_config.required_scope,
                    allow_expired_grace_period=auth_config.allow_expired_grace_period,
                )
                
                self._logger.info("Created default token validator")
                return validator
                
            elif auth_config.provider_type == AuthProviderType.SCOPE_ONLY:
                from .validators import ScopeOnlyValidator
                
                validator = ScopeOnlyValidator(
                    required_scope=auth_config.required_scope
                )
                
                self._logger.info("Created scope-only token validator")
                return validator
            else:
                raise ProviderConfigurationError(f"Unsupported provider type for validator: {auth_config.provider_type}")
                
        except Exception as e:
            self._logger.error("Failed to create token validator", error=str(e))
            raise ProviderConfigurationError(f"Failed to create token validator: {e}")
    
    def _create_azure_provider(self, auth_config: AuthConfig) -> AuthenticationProvider:
        """Create Azure Entra ID provider from configuration."""
        from .providers import AzureEntraAuthProvider
        
        if not auth_config.azure_tenant_id:
            raise ProviderConfigurationError("azure_tenant_id is required for Azure Entra ID provider")
        
        provider = AzureEntraAuthProvider(
            tenant_id=auth_config.azure_tenant_id,
            authority_url=auth_config.azure_authority_url,
            default_scope=auth_config.required_scope,
            token_cache_ttl=auth_config.token_cache_ttl,
        )
        
        self._logger.info("Created Azure Entra ID provider", tenant_id=auth_config.azure_tenant_id)
        return provider
    
    def _create_scope_only_provider(self, auth_config: AuthConfig) -> AuthenticationProvider:
        """Create scope-only provider for development/testing."""
        # Note: This is a placeholder - scope-only doesn't need a full provider
        # We'll use a mock provider that just validates scopes
        from .validators import ScopeOnlyValidator
        
        class MockProvider(AuthenticationProvider):
            @property
            def provider_name(self) -> str:
                return "Mock Scope-Only Provider"
            
            @property
            def default_scopes(self) -> List[str]:
                return [auth_config.required_scope]
            
            async def authenticate(self, credentials, scopes=None, resource=None):
                # This should not be called for scope-only validation
                raise NotImplementedError("Scope-only provider does not support authentication")
            
            async def refresh_token(self, token_info):
                raise NotImplementedError("Scope-only provider does not support token refresh")
            
            async def validate_token(self, access_token):
                # Delegate to scope-only validator
                validator = ScopeOnlyValidator(auth_config.required_scope)
                return await validator.validate(access_token)
            
            async def get_token_info(self, access_token):
                return None
        
        provider = MockProvider()
        self._logger.info("Created scope-only mock provider")
        return provider


def load_auth_config() -> AuthConfig:
    """
    Load authentication configuration from environment variables.
    
    Returns:
        AuthConfig instance
    """
    return AuthConfig.from_env()


def create_auth_components(auth_config: Optional[AuthConfig] = None) -> tuple[Optional[AuthenticationProvider], Optional[TokenValidator]]:
    """
    Create authentication provider and validator from configuration.
    
    Args:
        auth_config: Authentication configuration (loads from env if None)
        
    Returns:
        Tuple of (auth_provider, token_validator)
    """
    if auth_config is None:
        auth_config = load_auth_config()
    
    manager = AuthConfigurationManager()
    
    auth_provider = manager.create_auth_provider(auth_config)
    token_validator = manager.create_token_validator(auth_config)
    
    return auth_provider, token_validator
