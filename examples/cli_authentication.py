#!/usr/bin/env python3
"""
CLI Authentication Example for Labyrinth.

This example shows how to use the Labyrinth CLI authentication system
which implements OAuth 2.0 Device Code Flow for interactive user authentication.

The Device Code Flow is the modern standard for CLI tools because:
1. No need for local web server or redirect handling
2. Works in headless/SSH environments
3. Better security - no redirect URI interception risks
4. User completes authentication in their preferred browser
5. Simple polling-based implementation
"""

import asyncio
import os
from pathlib import Path

from labyrinth.auth.interactive import CLIAuthenticationManager, authenticate_cli
from labyrinth.auth.interfaces import AuthenticationError


async def example_direct_api_usage():
    """Example using the authentication API directly."""
    print("🔐 Direct API Authentication Example")
    print("-" * 40)
    
    # Configuration (normally from environment variables)
    client_id = "your-public-client-id"  # Azure app registration (public client)
    tenant_id = "your-tenant-id"         # Azure tenant ID
    scopes = ["agentic_ai_solution"]     # Required OAuth scopes
    cache_file = str(Path.home() / ".labyrinth" / "example_token_cache.json")
    
    try:
        # Create authentication manager
        auth_manager = CLIAuthenticationManager(
            client_id=client_id,
            tenant_id=tenant_id,
            scopes=scopes,
            token_cache_file=cache_file
        )
        
        print("📱 Starting interactive authentication...")
        print("   This will open your browser and ask you to enter a code")
        
        # Authenticate user (this handles the full device flow)
        token_info = await auth_manager.authenticate(auto_open_browser=True)
        
        print("✅ Authentication successful!")
        print(f"   Token expires in: {(token_info.expires_at - token_info.issued_at) // 3600} hours")
        print(f"   Granted scopes: {token_info.scope}")
        
        # Get access token for API calls
        access_token = await auth_manager.get_access_token()
        print(f"   Access token: {access_token[:20]}...")
        
        # Simulate some work
        print("\n🔄 Simulating authenticated API calls...")
        for i in range(3):
            # Each call automatically uses the cached token
            token = await auth_manager.get_access_token()
            print(f"   API call {i+1}: Token available ({'expired' if token_info.is_expired else 'valid'})")
            await asyncio.sleep(1)
        
        print("\n🔓 Logging out...")
        await auth_manager.logout()
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def example_convenience_function():
    """Example using the convenience authentication function."""
    print("\n🚀 Convenience Function Example")
    print("-" * 40)
    
    try:
        # Quick authentication using convenience function
        access_token = await authenticate_cli(
            client_id="your-public-client-id",
            tenant_id="your-tenant-id",
            scopes=["agentic_ai_solution"],
            cache_file=str(Path.home() / ".labyrinth" / "quick_token_cache.json")
        )
        
        print("✅ Quick authentication successful!")
        print(f"   Access token: {access_token[:20]}...")
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")


def show_cli_commands():
    """Show CLI command examples."""
    print("\n🖥️  CLI Commands Examples")
    print("-" * 40)
    
    print("1. Configuration setup:")
    print("   export LABYRINTH_CLI_CLIENT_ID=your-public-client-id")
    print("   export LABYRINTH_CLI_TENANT_ID=your-tenant-id")
    print("   export LABYRINTH_CLI_SCOPES=agentic_ai_solution")
    print()
    
    print("2. Interactive login:")
    print("   labyrinth auth login")
    print("   # Opens browser for authentication")
    print()
    
    print("3. Check authentication status:")
    print("   labyrinth auth status")
    print("   labyrinth auth status --show-claims  # Show detailed token info")
    print()
    
    print("4. Get token for scripting:")
    print("   TOKEN=$(labyrinth auth token)")
    print("   curl -H \"Authorization: Bearer $TOKEN\" https://api.example.com/")
    print()
    
    print("5. Logout:")
    print("   labyrinth auth logout")
    print()
    
    print("6. Configuration help:")
    print("   labyrinth auth config")


def show_azure_setup():
    """Show Azure app registration setup."""
    print("\n☁️  Azure App Registration Setup")
    print("-" * 40)
    
    print("1. Create App Registration:")
    print("   • Go to Azure Portal > Azure AD > App registrations")
    print("   • Click 'New registration'")
    print("   • Name: 'Labyrinth CLI'")
    print("   • Account types: 'Single tenant' or 'Multitenant' as needed")
    print("   • Redirect URI: Leave blank for now")
    print()
    
    print("2. Configure as Public Client:")
    print("   • Go to 'Authentication'")
    print("   • Add platform > 'Mobile and desktop applications'")
    print("   • Add redirect URI: https://login.microsoftonline.com/common/oauth2/nativeclient")
    print("   • Under 'Advanced settings', enable 'Allow public client flows'")
    print()
    
    print("3. Configure API Permissions:")
    print("   • Go to 'API permissions'")
    print("   • Add your custom scopes (e.g., 'agentic_ai_solution')")
    print("   • Grant admin consent if required")
    print()
    
    print("4. Get Configuration Values:")
    print("   • Application (client) ID: Use as LABYRINTH_CLI_CLIENT_ID")
    print("   • Directory (tenant) ID: Use as LABYRINTH_CLI_TENANT_ID")
    print("   • No client secret needed (public client)")


def show_security_considerations():
    """Show security best practices."""
    print("\n🔒 Security Considerations")
    print("-" * 40)
    
    print("✅ Best Practices:")
    print("   • Device Code Flow is secure for CLI tools")
    print("   • No client secrets needed (public client)")
    print("   • Tokens cached with user-only permissions (600)")
    print("   • Automatic token refresh before expiration")
    print("   • Secure token storage in user home directory")
    print()
    
    print("🚫 What NOT to do:")
    print("   • Don't share the client ID of confidential clients")
    print("   • Don't commit token cache files to version control")
    print("   • Don't use authorization code flow for CLI tools")
    print("   • Don't store tokens in insecure locations")
    print()
    
    print("🔧 Production Deployment:")
    print("   • Use separate app registrations per environment")
    print("   • Configure least-privilege scopes")
    print("   • Monitor authentication logs in Azure AD")
    print("   • Set appropriate token lifetimes")


def show_troubleshooting():
    """Show common troubleshooting steps."""
    print("\n🔧 Troubleshooting")
    print("-" * 40)
    
    print("Common Issues:")
    print()
    print("1. 'Client ID not found':")
    print("   • Set LABYRINTH_CLI_CLIENT_ID environment variable")
    print("   • Or use --client-id flag")
    print()
    
    print("2. 'AADSTS50020: User account from identity provider does not exist':")
    print("   • Check tenant ID is correct")
    print("   • Ensure user exists in the tenant")
    print()
    
    print("3. 'AADSTS65001: The user or administrator has not consented':")
    print("   • Grant admin consent for API permissions")
    print("   • Or configure user consent settings")
    print()
    
    print("4. 'AADSTS50011: The redirect URI specified in the request does not match':")
    print("   • Add https://login.microsoftonline.com/common/oauth2/nativeclient")
    print("   • As a redirect URI in your app registration")
    print()
    
    print("Debug Commands:")
    print("   labyrinth auth status --show-claims  # Show token details")
    print("   labyrinth auth logout && labyrinth auth login  # Clear and re-authenticate")


async def main():
    """Run all authentication examples."""
    print("🔐 Labyrinth CLI Authentication Examples")
    print("=" * 50)
    
    print("\nThis example demonstrates OAuth 2.0 Device Code Flow for CLI authentication.")
    print("Device Code Flow is the modern standard for command-line tools because:")
    print("• No local web server needed")
    print("• Works in headless environments (SSH, containers)")
    print("• Better security than auth code flow for public clients")
    print("• User completes auth in their preferred browser")
    print()
    
    # Show setup information
    show_azure_setup()
    show_cli_commands()
    show_security_considerations()
    show_troubleshooting()
    
    # Interactive examples (commented out to avoid requiring real credentials)
    print("\n⚠️  To run the interactive examples:")
    print("1. Set up an Azure app registration as shown above")
    print("2. Set environment variables:")
    print("   export LABYRINTH_CLI_CLIENT_ID=your-client-id")
    print("   export LABYRINTH_CLI_TENANT_ID=your-tenant-id")
    print("3. Uncomment the example function calls below")
    print()
    
    # Uncomment these lines to run interactive examples:
    # await example_direct_api_usage()
    # await example_convenience_function()
    
    print("🎉 CLI Authentication examples complete!")
    print("\nNext steps:")
    print("• Try: labyrinth auth config")
    print("• Try: labyrinth auth login")
    print("• Try: labyrinth auth status")


if __name__ == "__main__":
    asyncio.run(main())
