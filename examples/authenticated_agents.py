#!/usr/bin/env python3
"""
Example showing how to use Labyrinth with Azure Entra ID authentication.

This script demonstrates:
1. Setting up authenticated agents and registry
2. Using client credentials and managed identity
3. Secure agent-to-agent communication
4. Token-based authorization with scopes
"""

import asyncio
import os
from typing import Dict, Any

from labyrinth.server import Agent
from labyrinth.server.authenticated_registry import AuthenticatedRegistryServer, RegistryAuthenticationManager
from labyrinth.client.authenticated_client import AuthenticatedClientManager
from labyrinth.auth import AuthConfig, load_auth_config, create_auth_components
from labyrinth.auth.providers import AzureEntraAuthProvider
from labyrinth.auth.validators import DefaultTokenValidator, ScopeOnlyValidator
from labyrinth.auth.interfaces import AuthenticationCredentials, CredentialType


async def setup_authenticated_registry():
    """Set up an authenticated registry server."""
    print("🔐 Setting up authenticated registry...")
    
    # Load authentication configuration from environment
    auth_config = load_auth_config()
    
    # For demo purposes, use scope-only validation if no Azure config
    if not auth_config.azure_tenant_id:
        print("⚠️  No Azure configuration found, using scope-only validation for demo")
        auth_config.provider_type = "scope_only"
        auth_config.enabled = True
    
    # Create authentication components
    auth_provider, token_validator = create_auth_components(auth_config)
    
    if not token_validator:
        print("❌ Authentication disabled, creating unauthenticated registry")
        from labyrinth.server.registry import RegistryServer, AgentRegistry
        registry = AgentRegistry()
        server = RegistryServer(registry, host="localhost", port=8888)
    else:
        print("✅ Authentication enabled, creating authenticated registry")
        from labyrinth.server.registry import AgentRegistry
        registry = AgentRegistry()
        server = AuthenticatedRegistryServer(
            registry=registry,
            token_validator=token_validator,
            host="localhost",
            port=8888,
            require_https=auth_config.require_https,
            default_scope=auth_config.required_scope,
        )
    
    # Start registry in background
    registry_task = asyncio.create_task(server.start())
    await asyncio.sleep(2)  # Give time to start
    
    print(f"🏪 Authenticated registry running on http://localhost:8888")
    return registry_task, auth_config


async def create_authenticated_agent():
    """Create an authenticated agent."""
    print("\n🤖 Creating authenticated agent...")
    
    # Create agent
    agent = Agent(
        name="Authenticated Agent",
        description="A secure agent with authentication",
        host="localhost",
        port=8081
    )
    
    # Add authenticated skills
    @agent.skill("secure_echo")
    async def secure_echo(message: str) -> str:
        """Secure echo that requires authentication."""
        return f"🔐 Authenticated echo: {message}"
    
    @agent.skill("calculate")
    async def calculate(expression: str) -> str:
        """Secure calculation service."""
        try:
            # Simple math evaluation (don't do this in production!)
            result = eval(expression)
            return f"🧮 Calculation result: {expression} = {result}"
        except Exception as e:
            return f"❌ Calculation error: {e}"
    
    # TODO: Add authentication middleware to agent
    # For now, the agent runs without authentication middleware
    # In a full implementation, you would add:
    # agent.add_middleware(AuthenticationMiddleware(...))
    
    # Start agent
    await agent.start()
    print(f"✅ Agent started on http://{agent.host}:{agent.port}")
    
    return agent


async def demo_client_credentials():
    """Demonstrate client credentials authentication."""
    print("\n🔑 Demo: Client Credentials Authentication")
    
    # Check if we have Azure credentials
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET") 
    tenant_id = os.getenv("AZURE_TENANT_ID")
    
    if not all([client_id, client_secret, tenant_id]):
        print("⚠️  Azure credentials not found in environment variables")
        print("   Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID to test")
        return await demo_scope_only_client()
    
    try:
        # Create authenticated client manager
        client_manager = AuthenticatedClientManager()
        
        # Create client with credentials
        client = await client_manager.create_client_credentials_client(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            scopes=["agentic_ai_solution"]
        )
        
        print("✅ Created authenticated client with client credentials")
        
        # Test registry operations
        await test_authenticated_registry_operations(client)
        
        # Clean up
        await client.close()
        
    except Exception as e:
        print(f"❌ Client credentials demo failed: {e}")
        return await demo_scope_only_client()


async def demo_managed_identity():
    """Demonstrate managed identity authentication."""
    print("\n🆔 Demo: Managed Identity Authentication")
    
    try:
        # Create authenticated client manager
        client_manager = AuthenticatedClientManager()
        
        # Try to create managed identity client
        # This will only work in Azure environment with managed identity enabled
        client = await client_manager.create_managed_identity_client(
            # client_id=None,  # Use system-assigned managed identity
            scopes=["agentic_ai_solution"]
        )
        
        print("✅ Created authenticated client with managed identity")
        
        # Test registry operations
        await test_authenticated_registry_operations(client)
        
        # Clean up
        await client.close()
        
    except Exception as e:
        print(f"⚠️  Managed identity not available (expected outside Azure): {e}")
        print("   This is normal when running outside Azure environment")


async def demo_scope_only_client():
    """Demonstrate scope-only authentication for development."""
    print("\n🔧 Demo: Scope-Only Authentication (Development)")
    
    try:
        from labyrinth.auth.validators import ScopeOnlyValidator
        from labyrinth.client.authenticated_client import AuthenticatedAgentClient
        from labyrinth.auth.interfaces import AuthenticationCredentials, CredentialType
        
        # Create a mock provider for scope-only validation
        class MockProvider:
            @property
            def provider_name(self):
                return "Mock Provider"
            
            @property 
            def default_scopes(self):
                return ["agentic_ai_solution"]
            
            async def authenticate(self, credentials, scopes=None, resource=None):
                from labyrinth.auth.interfaces import TokenInfo
                import time
                
                # Create a mock token with required scope
                return TokenInfo(
                    access_token="mock_token_with_agentic_ai_solution_scope",
                    token_type="Bearer",
                    expires_at=time.time() + 3600,
                    scope="agentic_ai_solution",
                )
            
            async def refresh_token(self, token_info):
                return await self.authenticate(None)
            
            async def validate_token(self, access_token):
                from labyrinth.auth.interfaces import ValidationResult, TokenInfo
                import time
                
                token_info = TokenInfo(
                    access_token=access_token,
                    scope="agentic_ai_solution",
                    expires_at=time.time() + 3600
                )
                
                return ValidationResult(
                    is_valid=True,
                    token_info=token_info,
                    principal_id="mock_user",
                    principal_name="Mock User",
                    scopes={"agentic_ai_solution"}
                )
            
            async def get_token_info(self, access_token):
                return None
        
        # Create mock credentials
        credentials = AuthenticationCredentials(
            credential_type=CredentialType.CLIENT_CREDENTIALS,
            client_id="mock_client",
            client_secret="mock_secret",
            tenant_id="mock_tenant"
        )
        
        # Create authenticated client with mock provider
        client = AuthenticatedAgentClient(
            auth_provider=MockProvider(),
            credentials=credentials,
            default_scopes=["agentic_ai_solution"]
        )
        
        print("✅ Created mock authenticated client for development")
        
        # Test registry operations
        await test_authenticated_registry_operations(client)
        
        # Clean up
        await client.close()
        
    except Exception as e:
        print(f"❌ Scope-only demo failed: {e}")


async def test_authenticated_registry_operations(client):
    """Test authenticated operations with the registry."""
    print("\n📋 Testing authenticated registry operations...")
    
    try:
        # Get registry stats
        stats = await client.get_registry_stats("http://localhost:8888")
        print("✅ Got authenticated registry stats:")
        print(f"   Total agents: {stats.get('total_agents', 0)}")
        print(f"   Healthy agents: {stats.get('healthy_agents', 0)}")
        
        if "authenticated_as" in stats:
            auth_info = stats["authenticated_as"]
            print(f"   Authenticated as: {auth_info.get('principal_name', 'Unknown')}")
            print(f"   Scopes: {', '.join(auth_info.get('scopes', []))}")
        
        # List agents
        agents = await client.list_agents("http://localhost:8888")
        print(f"✅ Found {len(agents)} registered agents")
        
        # Register a mock agent
        agent_card = {
            "name": "Test Authenticated Agent",
            "description": "A test agent for authentication demo",
            "version": "1.0.0",
            "skills": [],
            "capabilities": {"skills": []},
            "default_input_modes": ["text"],
            "default_output_modes": ["text"],
        }
        
        result = await client.register_with_registry(
            registry_url="http://localhost:8888",
            agent_card=agent_card,
            base_url="http://localhost:8082",
            agent_id="test-auth-agent"
        )
        print(f"✅ Registered test agent: {result}")
        
        # Send heartbeat
        heartbeat_result = await client.send_heartbeat(
            registry_url="http://localhost:8888",
            agent_id="test-auth-agent"
        )
        print(f"✅ Sent heartbeat: {heartbeat_result}")
        
    except Exception as e:
        print(f"❌ Registry operations failed: {e}")


async def demo_environment_setup():
    """Show how to set up authentication via environment variables."""
    print("\n🌍 Authentication Environment Setup")
    print("=" * 50)
    print("To use Azure Entra ID authentication, set these environment variables:")
    print()
    print("# Required for Azure Entra ID")
    print("export LABYRINTH_AUTH_ENABLED=true")
    print("export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id")
    print("export LABYRINTH_AUTH_AZURE_TENANT_ID=your-tenant-id")
    print("export LABYRINTH_AUTH_REQUIRED_SCOPE=agentic_ai_solution")
    print()
    print("# For client credentials flow")
    print("export LABYRINTH_AUTH_AZURE_CLIENT_ID=your-client-id")
    print("export LABYRINTH_AUTH_AZURE_CLIENT_SECRET=your-client-secret")
    print()
    print("# For managed identity (Azure environments)")
    print("export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true")
    print("# export LABYRINTH_AUTH_MANAGED_IDENTITY_CLIENT_ID=user-assigned-mi-client-id")
    print()
    print("# Optional settings")
    print("export LABYRINTH_AUTH_REQUIRE_HTTPS=true")
    print("export LABYRINTH_AUTH_TOKEN_CACHE_TTL=3600")
    print()
    
    # Show current configuration
    auth_config = load_auth_config()
    print("Current authentication configuration:")
    print(f"  Enabled: {auth_config.enabled}")
    print(f"  Provider: {auth_config.provider_type.value}")
    print(f"  Required scope: {auth_config.required_scope}")
    print(f"  Azure tenant: {auth_config.azure_tenant_id or 'Not set'}")
    print(f"  Use managed identity: {auth_config.use_managed_identity}")
    print(f"  Require HTTPS: {auth_config.require_https}")


async def main():
    """Run the authentication examples."""
    print("🔐 Labyrinth Authentication Examples")
    print("=" * 50)
    
    # Show environment setup
    await demo_environment_setup()
    
    try:
        # Start authenticated registry
        registry_task, auth_config = await setup_authenticated_registry()
        
        # Create authenticated agent
        agent = await create_authenticated_agent()
        
        # Demo different authentication methods
        await demo_client_credentials()
        await demo_managed_identity()
        
        print("\n🎉 Authentication examples completed!")
        print("\nKey takeaways:")
        print("✅ Labyrinth supports multiple authentication providers")
        print("✅ Azure Entra ID integration with client credentials and managed identity")
        print("✅ Automatic token management and refresh")
        print("✅ Scope-based authorization for fine-grained access control")
        print("✅ Swappable authentication providers via dependency injection")
        
        print("\n🔧 Next steps:")
        print("1. Set up your Azure Entra ID application registration")
        print("2. Configure the required scope 'agentic_ai_solution'")
        print("3. Set environment variables for your deployment")
        print("4. Enable HTTPS in production environments")
        print("5. Implement custom authentication providers as needed")
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'registry_task' in locals():
            registry_task.cancel()
            try:
                await registry_task
            except asyncio.CancelledError:
                pass
        
        if 'agent' in locals():
            await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
