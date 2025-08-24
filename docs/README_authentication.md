# Labyrinth Authentication Examples

This directory contains comprehensive examples and guides for implementing authentication in Labyrinth agent systems.

## Overview

Labyrinth provides a flexible authentication framework that supports multiple identity providers and deployment scenarios. The system is built on OAuth 2.0 and OpenID Connect standards, with support for:

- **Azure Entra ID (Azure AD)** - Full OAuth 2.0 implementation with JWT tokens
- **Scope-only validation** - Simplified development/testing mode
- **Custom providers** - Pluggable architecture for any OAuth provider

## Quick Start

1. **Run the main example**:
   ```bash
   python examples/authenticated_agents.py
   ```

2. **Explore configuration options**:
   ```bash
   python examples/auth_config_examples.py
   ```

3. **Follow the Azure setup guide**: 

## Files in This Directory

### Core Examples

- **`authenticated_agents.py`** - Complete working example showing:
  - Authenticated registry setup
  - Client credentials flow
  - Managed identity authentication
  - Agent-to-agent communication
  - Development mode with mock tokens

- **`auth_config_examples.py`** - Configuration examples for:
  - Azure Entra ID with client credentials
  - Azure Entra ID with managed identity
  - Scope-only validation (development)
  - Production best practices
  - Multi-environment configuration

### Setup Guides

- **`azure_setup_guide.md`** - Step-by-step Azure setup including:
  - App registration creation
  - Client secret and managed identity setup
  - Scope configuration
  - Azure deployment examples
  - Troubleshooting guide

- **`README_authentication.md`** - This overview document

## Authentication Architecture

### Core Components

```python
# Authentication Provider Interface
from labyrinth.auth.interfaces import AuthenticationProvider

# Token Validator Interface  
from labyrinth.auth.interfaces import TokenValidator

# Azure Entra ID Implementation
from labyrinth.auth.providers import AzureEntraAuthProvider

# Configuration Management
from labyrinth.auth import AuthConfig, load_auth_config
```

### Flow Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent Client  │    │   Registry      │    │  Identity       │
│                 │    │   Server        │    │  Provider       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. Get Token          │                       │
         │──────────────────────────────────────────────▶│
         │                       │                       │
         │ 2. Return JWT Token   │                       │
         │◀──────────────────────────────────────────────│
         │                       │                       │
         │ 3. API Call + Token   │                       │
         │──────────────────────▶│                       │
         │                       │                       │
         │                       │ 4. Validate Token    │
         │                       │──────────────────────▶│
         │                       │                       │
         │                       │ 5. Token Valid       │
         │                       │◀──────────────────────│
         │                       │                       │
         │ 6. API Response       │                       │
         │◀──────────────────────│                       │
```

## Environment Variables

### Required for Azure Entra ID

```bash
# Basic configuration
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="your-tenant-id"
export LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution"

# Client credentials flow
export LABYRINTH_AUTH_AZURE_CLIENT_ID="your-client-id"
export LABYRINTH_AUTH_AZURE_CLIENT_SECRET="your-client-secret"

# Managed identity flow (Azure deployments)
export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true
export LABYRINTH_AUTH_MANAGED_IDENTITY_CLIENT_ID="optional-user-assigned-mi-id"
```

### Optional Settings

```bash
# Security settings
export LABYRINTH_AUTH_REQUIRE_HTTPS=true
export LABYRINTH_AUTH_TOKEN_CACHE_TTL=3600

# Development mode
export LABYRINTH_AUTH_PROVIDER_TYPE=scope_only
export LABYRINTH_AUTH_REQUIRE_HTTPS=false
```

## Usage Patterns

### 1. Authenticated Registry Server

```python
from labyrinth.server.authenticated_registry import AuthenticatedRegistryServer
from labyrinth.auth import load_auth_config, create_auth_components

# Load configuration
config = load_auth_config()
auth_provider, token_validator = create_auth_components(config)

# Create authenticated registry
registry = AgentRegistry()
server = AuthenticatedRegistryServer(
    registry=registry,
    token_validator=token_validator,
    host="localhost",
    port=8888,
    require_https=config.require_https,
    default_scope=config.required_scope,
)

await server.start()
```

### 2. Authenticated Agent Client

```python
from labyrinth.client.authenticated_client import AuthenticatedClientManager

# Create client manager
client_manager = AuthenticatedClientManager()

# Client credentials flow
client = await client_manager.create_client_credentials_client(
    client_id="your-client-id",
    client_secret="your-client-secret", 
    tenant_id="your-tenant-id",
    scopes=["agentic_ai_solution"]
)

# Use client for authenticated requests
agents = await client.list_agents("https://registry.example.com")
```

### 3. Managed Identity Client

```python
# Managed identity (Azure deployments)
client = await client_manager.create_managed_identity_client(
    scopes=["agentic_ai_solution"]
)

# Automatic token refresh and management
result = await client.register_with_registry(
    registry_url="https://registry.example.com",
    agent_card=agent_card,
    base_url="https://myagent.example.com"
)
```

## Deployment Scenarios

### Development Environment

- Use **scope-only validation** for easy testing
- Disable HTTPS requirement
- Mock tokens with required scopes
- Fast iteration without Azure setup

```bash
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=scope_only
export LABYRINTH_AUTH_REQUIRED_SCOPE=agentic_ai_solution
export LABYRINTH_AUTH_REQUIRE_HTTPS=false
```

### Staging Environment

- Use **client credentials** with Azure Entra ID
- Enable HTTPS requirement
- Real token validation
- Separate Azure app registration

```bash
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="staging-tenant"
export LABYRINTH_AUTH_AZURE_CLIENT_ID="staging-client-id"
export LABYRINTH_AUTH_AZURE_CLIENT_SECRET="staging-secret"
export LABYRINTH_AUTH_REQUIRED_SCOPE=agentic_ai_solution
export LABYRINTH_AUTH_REQUIRE_HTTPS=true
```

### Production Environment

- Use **managed identity** (no secrets in code)
- Strict HTTPS requirement  
- Shorter token cache TTL
- Comprehensive monitoring

```bash
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="production-tenant"
export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true
export LABYRINTH_AUTH_REQUIRED_SCOPE=agentic_ai_solution
export LABYRINTH_AUTH_REQUIRE_HTTPS=true
export LABYRINTH_AUTH_TOKEN_CACHE_TTL=1800
```

## Security Considerations

### Production Checklist

- ✅ Use HTTPS for all communications
- ✅ Prefer managed identity over client secrets
- ✅ Implement least-privilege scopes
- ✅ Enable comprehensive logging
- ✅ Regular security audits
- ✅ Network-level security (firewalls, NSGs)
- ✅ Token rotation and lifecycle management

### Token Security

- Tokens are **cached in memory** only (not persisted)
- Automatic **token refresh** before expiration
- **Short-lived tokens** with configurable TTL
- **Secure transmission** over HTTPS only in production

### Scope-Based Authorization

- **Fine-grained access control** through OAuth scopes
- **Per-endpoint authorization** with configurable requirements
- **Extensible scope model** for custom permissions
- **Default scope** fallback for simplified configuration

## Extending Authentication

### Custom Provider Implementation

To implement a custom authentication provider:

1. **Implement interfaces**:
   ```python
   from labyrinth.auth.interfaces import AuthenticationProvider, TokenValidator
   
   class CustomProvider(AuthenticationProvider):
       # Implement required methods
       pass
   
   class CustomValidator(TokenValidator):
       # Implement token validation
       pass
   ```

2. **Add to configuration**:
   ```python
   from labyrinth.auth import AuthProviderType
   
   class AuthProviderType(Enum):
       CUSTOM = "custom"
   ```

3. **Update factory function**:
   ```python
   def create_auth_components(config):
       if config.provider_type == AuthProviderType.CUSTOM:
           return CustomProvider(config), CustomValidator(config)
   ```

### Custom Scopes

Define custom scopes for your application:

```python
# Define application-specific scopes
AGENT_READ_SCOPE = "agent:read"
AGENT_WRITE_SCOPE = "agent:write"  
REGISTRY_ADMIN_SCOPE = "registry:admin"

# Configure per-endpoint authorization
@require_scope(AGENT_WRITE_SCOPE)
async def register_agent(agent_data):
    # Only clients with agent:write scope can access
    pass
```

## Troubleshooting

### Common Issues

1. **Authentication disabled**: Check `LABYRINTH_AUTH_ENABLED=true`
2. **Invalid tenant ID**: Verify Azure tenant configuration
3. **Missing client secret**: Ensure secret is set and not expired
4. **Scope mismatch**: Check required vs. provided scopes
5. **HTTPS required**: Enable HTTPS or disable requirement for development

### Debug Mode

Enable detailed authentication logging:

```python
import logging
logging.getLogger('labyrinth.auth').setLevel(logging.DEBUG)
```

### Token Inspection

Decode JWT tokens for debugging:

```python
import jwt

# Decode without signature verification (development only)
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Scopes: {decoded.get('scp', [])}")
print(f"Expires: {decoded.get('exp')}")
```

## Additional Resources

- **Azure Entra ID Documentation**: https://docs.microsoft.com/en-us/azure/active-directory/
- **OAuth 2.0 Specification**: https://tools.ietf.org/html/rfc6749
- **JWT Tokens**: https://jwt.io/introduction/
- **Managed Identity Guide**: https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/

## Support

For questions about authentication implementation:

1. Check the troubleshooting section above
2. Review the example code and configuration
3. Consult the Azure setup guide for deployment issues
4. Enable debug logging for detailed error information

---

**Next Steps**: Run `python examples/authenticated_agents.py` to see authentication in action!
