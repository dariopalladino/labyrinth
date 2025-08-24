#!/usr/bin/env python3
"""
Configuration examples for Labyrinth authentication setup.

This script shows different ways to configure authentication for various
deployment scenarios and authentication providers.
"""

import os
from typing import Dict, Any

from labyrinth.auth import AuthConfig, AuthProviderType, load_auth_config, create_auth_components
from labyrinth.auth.providers import AzureEntraAuthProvider
from labyrinth.auth.validators import DefaultTokenValidator, ScopeOnlyValidator
from labyrinth.auth.interfaces import AuthenticationCredentials, CredentialType


def example_azure_client_credentials_config():
    """Example configuration for Azure Entra ID with client credentials."""
    print("🔐 Azure Entra ID Client Credentials Configuration")
    print("-" * 50)
    
    # Create configuration programmatically
    config = AuthConfig(
        enabled=True,
        provider_type=AuthProviderType.AZURE_ENTRA_ID,
        azure_tenant_id="your-tenant-id-here",
        azure_client_id="your-client-id-here",
        azure_client_secret="your-client-secret-here",
        use_managed_identity=False,
        required_scope="agentic_ai_solution",
        require_https=True,
        token_cache_ttl=3600,
    )
    
    print("Configuration object:")
    print(f"  Provider: {config.provider_type.value}")
    print(f"  Tenant ID: {config.azure_tenant_id}")
    print(f"  Client ID: {config.azure_client_id}")
    print(f"  Required scope: {config.required_scope}")
    print(f"  Require HTTPS: {config.require_https}")
    print()
    
    # Show equivalent environment variables
    print("Equivalent environment variables:")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id")
    print(f"export LABYRINTH_AUTH_AZURE_TENANT_ID={config.azure_tenant_id}")
    print(f"export LABYRINTH_AUTH_AZURE_CLIENT_ID={config.azure_client_id}")
    print(f"export LABYRINTH_AUTH_AZURE_CLIENT_SECRET={config.azure_client_secret}")
    print(f"export LABYRINTH_AUTH_REQUIRED_SCOPE={config.required_scope}")
    print(f"export LABYRINTH_AUTH_REQUIRE_HTTPS={str(config.require_https).lower()}")
    print(f"export LABYRINTH_AUTH_TOKEN_CACHE_TTL={config.token_cache_ttl}")
    print()
    
    return config


def example_azure_managed_identity_config():
    """Example configuration for Azure Entra ID with managed identity."""
    print("🆔 Azure Entra ID Managed Identity Configuration")
    print("-" * 50)
    
    # System-assigned managed identity
    config_system = AuthConfig(
        enabled=True,
        provider_type=AuthProviderType.AZURE_ENTRA_ID,
        azure_tenant_id="your-tenant-id-here",
        use_managed_identity=True,
        managed_identity_client_id=None,  # System-assigned
        required_scope="agentic_ai_solution",
        require_https=True,
        token_cache_ttl=3600,
    )
    
    print("System-assigned managed identity:")
    print(f"  Provider: {config_system.provider_type.value}")
    print(f"  Tenant ID: {config_system.azure_tenant_id}")
    print(f"  Use managed identity: {config_system.use_managed_identity}")
    print(f"  MI Client ID: {config_system.managed_identity_client_id or 'System-assigned'}")
    print()
    
    print("Environment variables for system-assigned MI:")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id")
    print(f"export LABYRINTH_AUTH_AZURE_TENANT_ID={config_system.azure_tenant_id}")
    print("export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true")
    print(f"export LABYRINTH_AUTH_REQUIRED_SCOPE={config_system.required_scope}")
    print()
    
    # User-assigned managed identity
    config_user = AuthConfig(
        enabled=True,
        provider_type=AuthProviderType.AZURE_ENTRA_ID,
        azure_tenant_id="your-tenant-id-here",
        use_managed_identity=True,
        managed_identity_client_id="user-assigned-mi-client-id",
        required_scope="agentic_ai_solution",
        require_https=True,
        token_cache_ttl=3600,
    )
    
    print("User-assigned managed identity:")
    print(f"  Provider: {config_user.provider_type.value}")
    print(f"  Tenant ID: {config_user.azure_tenant_id}")
    print(f"  Use managed identity: {config_user.use_managed_identity}")
    print(f"  MI Client ID: {config_user.managed_identity_client_id}")
    print()
    
    print("Environment variables for user-assigned MI:")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id")
    print(f"export LABYRINTH_AUTH_AZURE_TENANT_ID={config_user.azure_tenant_id}")
    print("export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true")
    print(f"export LABYRINTH_AUTH_MANAGED_IDENTITY_CLIENT_ID={config_user.managed_identity_client_id}")
    print(f"export LABYRINTH_AUTH_REQUIRED_SCOPE={config_user.required_scope}")
    print()
    
    return config_system, config_user


def example_scope_only_config():
    """Example configuration for development with scope-only validation."""
    print("🔧 Scope-Only Authentication Configuration (Development)")
    print("-" * 50)
    
    config = AuthConfig(
        enabled=True,
        provider_type=AuthProviderType.SCOPE_ONLY,
        required_scope="agentic_ai_solution",
        require_https=False,  # Usually disabled in development
        token_cache_ttl=3600,
    )
    
    print("Configuration object:")
    print(f"  Provider: {config.provider_type.value}")
    print(f"  Required scope: {config.required_scope}")
    print(f"  Require HTTPS: {config.require_https}")
    print()
    
    print("Environment variables:")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=scope_only")
    print(f"export LABYRINTH_AUTH_REQUIRED_SCOPE={config.required_scope}")
    print("export LABYRINTH_AUTH_REQUIRE_HTTPS=false")
    print()
    
    print("⚠️  Note: Scope-only validation is for development only!")
    print("   It accepts any token containing the required scope.")
    print("   Use a proper authentication provider in production.")
    print()
    
    return config


def example_disabled_config():
    """Example configuration with authentication disabled."""
    print("❌ Authentication Disabled Configuration")
    print("-" * 50)
    
    config = AuthConfig(
        enabled=False,
        provider_type=AuthProviderType.SCOPE_ONLY,  # Ignored when disabled
    )
    
    print("Configuration object:")
    print(f"  Enabled: {config.enabled}")
    print()
    
    print("Environment variables:")
    print("export LABYRINTH_AUTH_ENABLED=false")
    print("# OR simply don't set LABYRINTH_AUTH_ENABLED (defaults to false)")
    print()
    
    print("⚠️  Warning: Disabling authentication removes all security!")
    print("   Only use this in isolated development environments.")
    print()
    
    return config


def example_production_config():
    """Example production configuration with best practices."""
    print("🏭 Production Configuration Best Practices")
    print("-" * 50)
    
    config = AuthConfig(
        enabled=True,
        provider_type=AuthProviderType.AZURE_ENTRA_ID,
        azure_tenant_id="production-tenant-id",
        use_managed_identity=True,  # Preferred in Azure
        managed_identity_client_id=None,  # System-assigned
        required_scope="agentic_ai_solution",
        require_https=True,  # REQUIRED in production
        token_cache_ttl=1800,  # Shorter cache for security
    )
    
    print("Production configuration:")
    print(f"  Provider: {config.provider_type.value}")
    print(f"  Tenant ID: {config.azure_tenant_id}")
    print(f"  Use managed identity: {config.use_managed_identity}")
    print(f"  Required scope: {config.required_scope}")
    print(f"  Require HTTPS: {config.require_https}")
    print(f"  Token cache TTL: {config.token_cache_ttl}s")
    print()
    
    print("Production environment variables:")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id")
    print(f"export LABYRINTH_AUTH_AZURE_TENANT_ID={config.azure_tenant_id}")
    print("export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true")
    print(f"export LABYRINTH_AUTH_REQUIRED_SCOPE={config.required_scope}")
    print("export LABYRINTH_AUTH_REQUIRE_HTTPS=true")
    print(f"export LABYRINTH_AUTH_TOKEN_CACHE_TTL={config.token_cache_ttl}")
    print()
    
    print("🔒 Production Security Checklist:")
    print("✅ Use managed identity (no secrets in code)")
    print("✅ Require HTTPS for all communications")
    print("✅ Use shorter token cache TTL")
    print("✅ Configure least-privilege scopes")
    print("✅ Enable logging and monitoring")
    print("✅ Regular rotation of client secrets (if used)")
    print("✅ Network security groups/firewalls")
    print("✅ Regular security audits")
    print()
    
    return config


def example_multi_environment_config():
    """Example showing environment-specific configuration."""
    print("🌍 Multi-Environment Configuration")
    print("-" * 50)
    
    # Load current environment
    env = os.getenv("ENVIRONMENT", "development").lower()
    print(f"Current environment: {env}")
    print()
    
    if env == "development":
        print("Development configuration:")
        config = AuthConfig(
            enabled=True,
            provider_type=AuthProviderType.SCOPE_ONLY,
            required_scope="agentic_ai_solution",
            require_https=False,
            token_cache_ttl=3600,
        )
    elif env == "staging":
        print("Staging configuration:")
        config = AuthConfig(
            enabled=True,
            provider_type=AuthProviderType.AZURE_ENTRA_ID,
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            azure_client_id=os.getenv("AZURE_CLIENT_ID"),
            azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
            required_scope="agentic_ai_solution",
            require_https=True,
            token_cache_ttl=1800,
        )
    elif env == "production":
        print("Production configuration:")
        config = AuthConfig(
            enabled=True,
            provider_type=AuthProviderType.AZURE_ENTRA_ID,
            azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
            use_managed_identity=True,
            managed_identity_client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID"),
            required_scope="agentic_ai_solution",
            require_https=True,
            token_cache_ttl=900,  # 15 minutes
        )
    else:
        print("Unknown environment, using default:")
        config = AuthConfig(enabled=False)
    
    print(f"  Enabled: {config.enabled}")
    print(f"  Provider: {config.provider_type.value}")
    print(f"  Require HTTPS: {config.require_https}")
    print()
    
    print("Environment variable setup:")
    print(f"export ENVIRONMENT={env}")
    print("# Set other variables based on environment needs")
    print()
    
    return config


async def example_runtime_config_validation():
    """Example showing how to validate configuration at runtime."""
    print("✅ Runtime Configuration Validation")
    print("-" * 50)
    
    try:
        # Load configuration
        config = load_auth_config()
        print(f"Loaded configuration: enabled={config.enabled}")
        
        if not config.enabled:
            print("⚠️  Authentication is disabled")
            return None, None
        
        # Create authentication components
        auth_provider, token_validator = create_auth_components(config)
        
        if auth_provider:
            print(f"✅ Created auth provider: {auth_provider.provider_name}")
            print(f"   Default scopes: {auth_provider.default_scopes}")
        
        if token_validator:
            print(f"✅ Created token validator: {token_validator.__class__.__name__}")
        
        # Validate configuration completeness
        validation_errors = []
        
        if config.provider_type == AuthProviderType.AZURE_ENTRA_ID:
            if not config.azure_tenant_id:
                validation_errors.append("Azure tenant ID is required")
            
            if not config.use_managed_identity:
                if not config.azure_client_id or not config.azure_client_secret:
                    validation_errors.append("Azure client credentials are required when not using managed identity")
        
        if config.require_https and not config.enabled:
            validation_errors.append("Cannot require HTTPS when authentication is disabled")
        
        if validation_errors:
            print("\n❌ Configuration validation errors:")
            for error in validation_errors:
                print(f"   • {error}")
        else:
            print("\n✅ Configuration validation passed")
        
        return auth_provider, token_validator
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return None, None


def example_custom_provider_config():
    """Example showing how to configure a custom authentication provider."""
    print("🔧 Custom Authentication Provider Configuration")
    print("-" * 50)
    
    print("To implement a custom provider:")
    print("1. Create a class implementing AuthenticationProvider interface")
    print("2. Create a TokenValidator for your provider")
    print("3. Add your provider type to AuthProviderType enum")
    print("4. Update create_auth_components() factory function")
    print()
    
    print("Example custom provider class structure:")
    print("""
class CustomAuthProvider(AuthenticationProvider):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @property
    def provider_name(self) -> str:
        return "Custom Provider"
    
    @property
    def default_scopes(self) -> List[str]:
        return self.config.get("default_scopes", [])
    
    async def authenticate(self, credentials, scopes=None, resource=None):
        # Implement authentication logic
        pass
    
    async def refresh_token(self, token_info):
        # Implement token refresh logic
        pass
    
    async def validate_token(self, access_token):
        # Implement token validation logic
        pass
""")
    
    print("Configuration usage:")
    print("""
# Add to AuthProviderType enum
class AuthProviderType(Enum):
    CUSTOM = "custom"
    
# Update AuthConfig to support custom settings
config = AuthConfig(
    enabled=True,
    provider_type=AuthProviderType.CUSTOM,
    custom_provider_config={
        "endpoint": "https://custom-auth.example.com",
        "client_id": "custom-client-id",
        "default_scopes": ["custom_scope"]
    }
)
""")


def main():
    """Run all configuration examples."""
    print("🔐 Labyrinth Authentication Configuration Examples")
    print("=" * 60)
    print()
    
    # Show different configuration approaches
    example_azure_client_credentials_config()
    print()
    
    example_azure_managed_identity_config()
    print()
    
    example_scope_only_config()
    print()
    
    example_disabled_config()
    print()
    
    example_production_config()
    print()
    
    example_multi_environment_config()
    print()
    
    # Runtime validation
    import asyncio
    asyncio.run(example_runtime_config_validation())
    print()
    
    example_custom_provider_config()
    print()
    
    print("📚 Additional Resources:")
    print("• Azure Entra ID App Registration: https://docs.microsoft.com/en-us/azure/active-directory/develop/")
    print("• Managed Identity Setup: https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/")
    print("• OAuth 2.0 Scopes: https://tools.ietf.org/html/rfc6749#section-3.3")
    print("• JWT Tokens: https://jwt.io/introduction/")


if __name__ == "__main__":
    main()
