#!/usr/bin/env python3
"""
CLI commands for authentication with Labyrinth.

This module provides commands for user authentication, token management,
and configuration for CLI tools using OAuth 2.0 Device Code Flow.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
import jwt

from labyrinth.auth.interactive import CLIAuthenticationManager, authenticate_cli
from labyrinth.auth.interfaces import AuthenticationError


def get_default_cache_path() -> str:
    """Get default token cache file path."""
    home = Path.home()
    cache_dir = home / ".labyrinth"
    cache_dir.mkdir(exist_ok=True)
    return str(cache_dir / "token_cache.json")


def get_config_from_env() -> tuple[str, str, list[str]]:
    """Get authentication config from environment variables."""
    client_id = os.getenv("LABYRINTH_CLI_CLIENT_ID")
    tenant_id = os.getenv("LABYRINTH_CLI_TENANT_ID", os.getenv("LABYRINTH_AUTH_AZURE_TENANT_ID"))
    scopes_str = os.getenv("LABYRINTH_CLI_SCOPES", "agentic_ai_solution")
    
    if not client_id:
        raise click.ClickException(
            "Client ID not found. Set LABYRINTH_CLI_CLIENT_ID environment variable "
            "or use --client-id option."
        )
    
    if not tenant_id:
        raise click.ClickException(
            "Tenant ID not found. Set LABYRINTH_CLI_TENANT_ID or LABYRINTH_AUTH_AZURE_TENANT_ID "
            "environment variable or use --tenant-id option."
        )
    
    scopes = [s.strip() for s in scopes_str.split(",")]
    
    return client_id, tenant_id, scopes


@click.group(name="auth")
def auth_cli():
    """Authentication commands for Labyrinth CLI."""
    pass


@auth_cli.command()
@click.option(
    "--client-id",
    envvar="LABYRINTH_CLI_CLIENT_ID",
    help="Azure app registration client ID"
)
@click.option(
    "--tenant-id",
    envvar=["LABYRINTH_CLI_TENANT_ID", "LABYRINTH_AUTH_AZURE_TENANT_ID"],
    help="Azure tenant ID"
)
@click.option(
    "--scopes",
    envvar="LABYRINTH_CLI_SCOPES",
    default="agentic_ai_solution",
    help="Comma-separated list of OAuth scopes"
)
@click.option(
    "--cache-file",
    default=None,
    help="Token cache file path (default: ~/.labyrinth/token_cache.json)"
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't automatically open browser"
)
def login(client_id: str, tenant_id: str, scopes: str, cache_file: Optional[str], no_browser: bool):
    """Authenticate with Azure Entra ID using device code flow."""
    
    if not cache_file:
        cache_file = get_default_cache_path()
    
    if not client_id or not tenant_id:
        try:
            client_id, tenant_id, scope_list = get_config_from_env()
        except click.ClickException:
            raise
    else:
        scope_list = [s.strip() for s in scopes.split(",")]
    
    async def do_login():
        try:
            manager = CLIAuthenticationManager(
                client_id=client_id,
                tenant_id=tenant_id,
                scopes=scope_list,
                token_cache_file=cache_file
            )
            
            token_info = await manager.authenticate(auto_open_browser=not no_browser)
            
            click.echo("\n🎉 Authentication completed successfully!")
            click.echo(f"📁 Token cached to: {cache_file}")
            
            # Show token info
            if token_info.scope:
                click.echo(f"🔑 Granted scopes: {token_info.scope}")
            
            expires_in = int(token_info.expires_at - token_info.issued_at) if token_info.expires_at and token_info.issued_at else None
            if expires_in:
                click.echo(f"⏰ Token expires in: {expires_in // 3600} hours")
            
        except AuthenticationError as e:
            click.echo(f"❌ Authentication failed: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(do_login())


@auth_cli.command()
@click.option(
    "--cache-file",
    default=None,
    help="Token cache file path (default: ~/.labyrinth/token_cache.json)"
)
def logout(cache_file: Optional[str]):
    """Clear cached authentication tokens."""
    
    if not cache_file:
        cache_file = get_default_cache_path()
    
    async def do_logout():
        try:
            # We don't need full config for logout, just create a dummy manager
            manager = CLIAuthenticationManager(
                client_id="dummy",
                tenant_id="dummy", 
                scopes=["dummy"],
                token_cache_file=cache_file
            )
            
            await manager.logout()
            
        except Exception as e:
            click.echo(f"❌ Error during logout: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(do_logout())


@auth_cli.command()
@click.option(
    "--cache-file",
    default=None,
    help="Token cache file path (default: ~/.labyrinth/token_cache.json)"
)
@click.option(
    "--show-claims",
    is_flag=True,
    help="Show detailed token claims"
)
def status(cache_file: Optional[str], show_claims: bool):
    """Show current authentication status and token information."""
    
    if not cache_file:
        cache_file = get_default_cache_path()
    
    async def do_status():
        try:
            # Create dummy manager to load token
            manager = CLIAuthenticationManager(
                client_id="dummy",
                tenant_id="dummy",
                scopes=["dummy"],
                token_cache_file=cache_file
            )
            
            # Try to load cached token
            cached_token = await manager._load_cached_token()
            
            if not cached_token:
                click.echo("❌ Not authenticated")
                click.echo(f"💡 Run 'labyrinth auth login' to authenticate")
                return
            
            # Show basic status
            click.echo("✅ Authenticated")
            
            if cached_token.is_expired:
                click.echo("⚠️  Token is expired")
                click.echo("💡 Run 'labyrinth auth login' to refresh")
            else:
                import time
                expires_in = int(cached_token.expires_at - time.time()) if cached_token.expires_at else None
                if expires_in:
                    hours = expires_in // 3600
                    minutes = (expires_in % 3600) // 60
                    click.echo(f"⏰ Token expires in: {hours}h {minutes}m")
            
            if cached_token.scope:
                click.echo(f"🔑 Scopes: {cached_token.scope}")
            
            click.echo(f"📁 Cache file: {cache_file}")
            
            # Show detailed claims if requested
            if show_claims and cached_token.access_token:
                try:
                    claims = jwt.decode(
                        cached_token.access_token,
                        options={"verify_signature": False}
                    )
                    
                    click.echo("\n📋 Token Claims:")
                    for key, value in claims.items():
                        if key in ["aud", "iss", "sub", "oid", "tid", "preferred_username", "name", "scp"]:
                            click.echo(f"   {key}: {value}")
                            
                except Exception as e:
                    click.echo(f"⚠️  Could not parse token claims: {e}")
            
        except Exception as e:
            click.echo(f"❌ Error checking status: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(do_status())


@auth_cli.command()
@click.option(
    "--client-id",
    envvar="LABYRINTH_CLI_CLIENT_ID",
    help="Azure app registration client ID"
)
@click.option(
    "--tenant-id",
    envvar=["LABYRINTH_CLI_TENANT_ID", "LABYRINTH_AUTH_AZURE_TENANT_ID"],
    help="Azure tenant ID"
)
@click.option(
    "--scopes",
    envvar="LABYRINTH_CLI_SCOPES",
    default="agentic_ai_solution",
    help="Comma-separated list of OAuth scopes"
)
@click.option(
    "--cache-file",
    default=None,
    help="Token cache file path (default: ~/.labyrinth/token_cache.json)"
)
def token(client_id: str, tenant_id: str, scopes: str, cache_file: Optional[str]):
    """Get current access token (for use in scripts)."""
    
    if not cache_file:
        cache_file = get_default_cache_path()
    
    if not client_id or not tenant_id:
        try:
            client_id, tenant_id, scope_list = get_config_from_env()
        except click.ClickException:
            raise
    else:
        scope_list = [s.strip() for s in scopes.split(",")]
    
    async def do_get_token():
        try:
            manager = CLIAuthenticationManager(
                client_id=client_id,
                tenant_id=tenant_id,
                scopes=scope_list,
                token_cache_file=cache_file
            )
            
            access_token = await manager.get_access_token()
            
            # Just print the token (for scripting)
            click.echo(access_token)
            
        except AuthenticationError as e:
            click.echo(f"❌ Failed to get token: {e}", err=True)
            click.echo("💡 Try running 'labyrinth auth login' first", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(do_get_token())


@auth_cli.command()
def config():
    """Show authentication configuration help."""
    
    click.echo("🔐 Labyrinth CLI Authentication Configuration")
    click.echo("=" * 50)
    click.echo()
    click.echo("Environment Variables:")
    click.echo("  LABYRINTH_CLI_CLIENT_ID       - Azure app registration client ID (required)")
    click.echo("  LABYRINTH_CLI_TENANT_ID       - Azure tenant ID (required)")
    click.echo("  LABYRINTH_CLI_SCOPES          - Comma-separated OAuth scopes (default: agentic_ai_solution)")
    click.echo()
    click.echo("Azure App Registration Setup:")
    click.echo("  1. Go to Azure Portal > Azure Active Directory > App registrations")
    click.echo("  2. Create a new registration or use existing one")
    click.echo("  3. Set as 'Public client' (no client secret needed)")
    click.echo("  4. Add 'Mobile and desktop applications' platform")
    click.echo("  5. Add redirect URI: https://login.microsoftonline.com/common/oauth2/nativeclient")
    click.echo("  6. Configure API permissions and scopes as needed")
    click.echo()
    click.echo("Example Usage:")
    click.echo("  export LABYRINTH_CLI_CLIENT_ID=your-client-id")
    click.echo("  export LABYRINTH_CLI_TENANT_ID=your-tenant-id")
    click.echo("  labyrinth auth login")
    click.echo("  labyrinth auth status")
    click.echo("  labyrinth auth token  # Get token for scripting")
    click.echo()
    click.echo("Token Cache:")
    click.echo(f"  Default location: {get_default_cache_path()}")
    click.echo("  Tokens are cached securely with user-only permissions")
    click.echo("  Use 'labyrinth auth logout' to clear cached tokens")


if __name__ == "__main__":
    auth_cli()
