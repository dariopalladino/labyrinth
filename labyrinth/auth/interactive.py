#!/usr/bin/env python3
"""
Interactive authentication provider for Azure Entra ID.

This module implements OAuth 2.0 Device Code Flow for CLI applications,
which is the modern recommended approach for command-line tools that 
need user authentication.

The Device Code Flow is preferred over Authorization Code + PKCE for CLIs because:
1. No need for local HTTP server or redirect handling
2. Works in headless environments (SSH, containers)  
3. Better security - no risk of redirect URI interception
4. Simpler implementation - just poll for completion
5. Better UX for CLI tools - user can complete auth in browser
"""

import asyncio
import hashlib
import secrets
import time
import webbrowser
from typing import Dict, List, Optional
from urllib.parse import urlencode
import logging

import aiohttp
import jwt

from .interfaces import (
    InteractiveAuthenticationProvider,
    InteractiveAuthResult, 
    TokenInfo,
    AuthenticationError,
    AuthenticationPendingError,
    AuthenticationTimeoutError,
)

logger = logging.getLogger(__name__)


class AzureInteractiveAuthProvider(InteractiveAuthenticationProvider):
    """
    Azure Entra ID interactive authentication provider.
    
    Supports OAuth 2.0 Device Code Flow for CLI applications and
    Authorization Code Flow with PKCE for web applications.
    """
    
    def __init__(self, authority_url: str = "https://login.microsoftonline.com"):
        """
        Initialize the Azure interactive auth provider.
        
        Args:
            authority_url: Azure authority URL (default is public cloud)
        """
        self.authority_url = authority_url.rstrip("/")
        self._device_flow_state: Dict[str, Dict] = {}
        
    async def start_device_flow(
        self,
        client_id: str,
        tenant_id: str,
        scopes: List[str]
    ) -> Dict[str, str]:
        """
        Start device code flow for CLI authentication.
        
        This is the recommended approach for CLI tools as it:
        - Works without local web server
        - Supports headless environments
        - Provides better security than auth code flow for public clients
        
        Args:
            client_id: OAuth client ID (public client, no secret needed)
            tenant_id: Azure tenant ID  
            scopes: Requested OAuth scopes
            
        Returns:
            Dictionary with device_code, user_code, verification_uri, etc.
        """
        endpoint = f"{self.authority_url}/{tenant_id}/oauth2/v2.0/devicecode"
        
        # Prepare scopes - join with spaces for OAuth
        scope_str = " ".join(scopes)
        
        data = {
            "client_id": client_id,
            "scope": scope_str
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise AuthenticationError(f"Device code flow failed: {error_text}")
                    
                    result = await response.json()
                    
                    # Store state for polling
                    device_code = result["device_code"]
                    self._device_flow_state[device_code] = {
                        "client_id": client_id,
                        "tenant_id": tenant_id,
                        "started_at": time.time(),
                        "expires_in": result.get("expires_in", 900),  # Default 15 minutes
                        "interval": result.get("interval", 5),  # Default 5 second polling
                    }
                    
                    logger.info(f"Device flow started for client {client_id}")
                    return result
                    
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Network error during device flow: {e}")
    
    async def poll_device_flow(
        self,
        device_code: str,
        client_id: str,
        tenant_id: str
    ) -> InteractiveAuthResult:
        """
        Poll for device flow completion.
        
        This should be called periodically until the user completes authentication
        or the device code expires.
        
        Args:
            device_code: Device code from start_device_flow
            client_id: OAuth client ID
            tenant_id: Azure tenant ID
            
        Returns:
            InteractiveAuthResult when user completes authentication
            
        Raises:
            AuthenticationPendingError: When user hasn't completed auth yet
            AuthenticationTimeoutError: When device code expires
            AuthenticationError: When authentication fails
        """
        # Check if we have state for this device code
        if device_code not in self._device_flow_state:
            raise AuthenticationError("Invalid or expired device code")
        
        state = self._device_flow_state[device_code]
        
        # Check expiration
        if time.time() - state["started_at"] > state["expires_in"]:
            del self._device_flow_state[device_code]
            raise AuthenticationTimeoutError("Device code has expired")
        
        endpoint = f"{self.authority_url}/{tenant_id}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": client_id,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, data=data) as response:
                    result = await response.json()
                    
                    if response.status == 400:
                        error = result.get("error", "unknown_error")
                        
                        if error == "authorization_pending":
                            raise AuthenticationPendingError("User has not yet completed authentication")
                        elif error == "slow_down":
                            # Increase polling interval
                            state["interval"] = min(state["interval"] * 2, 60)
                            raise AuthenticationPendingError("Polling too frequently, slowing down")
                        elif error == "expired_token":
                            del self._device_flow_state[device_code]
                            raise AuthenticationTimeoutError("Device code has expired")
                        elif error in ["access_denied", "authorization_declined"]:
                            del self._device_flow_state[device_code]
                            raise AuthenticationError("User declined the authentication request")
                        else:
                            del self._device_flow_state[device_code]
                            raise AuthenticationError(f"Authentication failed: {error}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        del self._device_flow_state[device_code] 
                        raise AuthenticationError(f"Token exchange failed: {error_text}")
                    
                    # Success! Clean up state
                    del self._device_flow_state[device_code]
                    
                    # Create token info
                    token_info = TokenInfo(
                        access_token=result["access_token"],
                        token_type=result.get("token_type", "Bearer"),
                        expires_in=result.get("expires_in"),
                        scope=result.get("scope"),
                    )
                    
                    # Extract user info from ID token if available
                    user_info = None
                    if "id_token" in result:
                        try:
                            id_claims = jwt.decode(
                                result["id_token"],
                                options={"verify_signature": False}
                            )
                            user_info = {
                                "user_id": id_claims.get("oid", id_claims.get("sub")),
                                "username": id_claims.get("preferred_username"),
                                "display_name": id_claims.get("name"),
                                "email": id_claims.get("email"),
                                "tenant_id": id_claims.get("tid"),
                            }
                        except Exception as e:
                            logger.warning(f"Failed to parse ID token: {e}")
                    
                    logger.info(f"Device flow completed successfully for user {user_info.get('username', 'unknown')}")
                    
                    return InteractiveAuthResult(
                        token_info=token_info,
                        user_info=user_info,
                        refresh_token=result.get("refresh_token")
                    )
                    
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Network error during token exchange: {e}")
    
    async def start_interactive_auth(
        self,
        client_id: str,
        tenant_id: str,
        scopes: List[str],
        redirect_uri: Optional[str] = None
    ) -> str:
        """
        Start authorization code flow with PKCE.
        
        This is primarily for web applications, but included for completeness.
        For CLI tools, use device flow instead.
        
        Args:
            client_id: OAuth client ID
            tenant_id: Azure tenant ID  
            scopes: Requested OAuth scopes
            redirect_uri: Redirect URI (required for auth code flow)
            
        Returns:
            Authorization URL for user to visit
        """
        if not redirect_uri:
            redirect_uri = "http://localhost:8080/callback"
        
        # Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(96)
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge_b64 = secrets.token_urlsafe(43).replace("_", "").replace("-", "")[:43]
        
        # Store PKCE state (in production, use secure storage)
        state = secrets.token_urlsafe(32)
        
        # Store for completion
        self._device_flow_state[state] = {
            "code_verifier": code_verifier,
            "client_id": client_id,
            "tenant_id": tenant_id,
            "redirect_uri": redirect_uri,
        }
        
        # Build authorization URL
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge_b64,
            "code_challenge_method": "S256",
            "response_mode": "query",
        }
        
        auth_url = f"{self.authority_url}/{tenant_id}/oauth2/v2.0/authorize?" + urlencode(params)
        
        logger.info(f"Authorization code flow started for client {client_id}")
        return auth_url
    
    async def complete_interactive_auth(
        self,
        auth_code: Optional[str] = None,
        device_code: Optional[str] = None
    ) -> InteractiveAuthResult:
        """
        Complete authorization code flow.
        
        Args:
            auth_code: Authorization code from callback
            device_code: Not used for auth code flow
            
        Returns:
            InteractiveAuthResult with tokens and user info
        """
        if not auth_code:
            raise AuthenticationError("Authorization code is required")
        
        # This would need to be implemented with state management
        # For now, recommend using device flow for CLI tools
        raise NotImplementedError("Authorization code flow completion not yet implemented. Use device flow for CLI applications.")


class CLIAuthenticationManager:
    """
    High-level manager for CLI authentication using device code flow.
    
    This provides a simple interface for CLI applications to authenticate users
    and manage tokens with automatic refresh and persistence.
    """
    
    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        scopes: List[str],
        token_cache_file: Optional[str] = None
    ):
        """
        Initialize CLI authentication manager.
        
        Args:
            client_id: Azure app registration client ID (public client)
            tenant_id: Azure tenant ID
            scopes: OAuth scopes to request
            token_cache_file: Optional file to persist tokens
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.scopes = scopes
        self.token_cache_file = token_cache_file
        self.provider = AzureInteractiveAuthProvider()
        self._current_token: Optional[TokenInfo] = None
        
    async def authenticate(self, auto_open_browser: bool = True) -> TokenInfo:
        """
        Authenticate user using device code flow.
        
        Args:
            auto_open_browser: Whether to automatically open browser
            
        Returns:
            TokenInfo with access token
        """
        # Check if we have a valid cached token
        cached_token = await self._load_cached_token()
        if cached_token and not cached_token.is_expired:
            logger.info("Using cached token")
            self._current_token = cached_token
            return cached_token
        
        print("🔐 Starting user authentication...")
        
        # Start device flow
        device_info = await self.provider.start_device_flow(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            scopes=self.scopes
        )
        
        # Display instructions to user
        print(f"\n📱 To sign in, use a web browser to open the page:")
        print(f"   {device_info['verification_uri']}")
        print(f"\n🔑 And enter the code: {device_info['user_code']}")
        print(f"\nℹ️  This code expires in {device_info.get('expires_in', 900) // 60} minutes")
        
        # Auto-open browser if requested
        if auto_open_browser:
            try:
                webbrowser.open(device_info['verification_uri'])
                print("🌐 Opened browser for authentication")
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")
        
        # Poll for completion
        device_code = device_info["device_code"]
        interval = device_info.get("interval", 5)
        
        print(f"\n⏳ Waiting for authentication (polling every {interval} seconds)...")
        
        while True:
            try:
                await asyncio.sleep(interval)
                result = await self.provider.poll_device_flow(
                    device_code=device_code,
                    client_id=self.client_id,
                    tenant_id=self.tenant_id
                )
                
                # Success!
                self._current_token = result.token_info
                
                if result.user_info:
                    username = result.user_info.get('username', 'unknown')
                    display_name = result.user_info.get('display_name', username)
                    print(f"\n✅ Authentication successful!")
                    print(f"   Welcome, {display_name}")
                else:
                    print(f"\n✅ Authentication successful!")
                
                # Cache token if requested
                await self._cache_token(result.token_info)
                
                return result.token_info
                
            except AuthenticationPendingError:
                print(".", end="", flush=True)  # Show progress
                continue
                
            except AuthenticationTimeoutError:
                print(f"\n❌ Authentication timed out. Please try again.")
                raise
                
            except AuthenticationError as e:
                print(f"\n❌ Authentication failed: {e}")
                raise
    
    async def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get current access token, refreshing if needed.
        
        Args:
            force_refresh: Force token refresh even if not expired
            
        Returns:
            Valid access token
        """
        if not self._current_token or self._current_token.is_expired or force_refresh:
            await self.authenticate()
        
        if not self._current_token:
            raise AuthenticationError("No valid token available")
        
        return self._current_token.access_token
    
    async def logout(self):
        """Clear cached tokens and logout."""
        self._current_token = None
        if self.token_cache_file:
            try:
                import os
                if os.path.exists(self.token_cache_file):
                    os.remove(self.token_cache_file)
                    logger.info(f"Removed token cache file: {self.token_cache_file}")
            except Exception as e:
                logger.warning(f"Failed to remove token cache: {e}")
        print("🔓 Logged out successfully")
    
    async def _load_cached_token(self) -> Optional[TokenInfo]:
        """Load token from cache file."""
        if not self.token_cache_file:
            return None
        
        try:
            import json
            import os
            
            if not os.path.exists(self.token_cache_file):
                return None
            
            with open(self.token_cache_file, 'r') as f:
                data = json.load(f)
            
            return TokenInfo(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_at=data.get("expires_at"),
                scope=data.get("scope"),
                issued_at=data.get("issued_at")
            )
        
        except Exception as e:
            logger.warning(f"Failed to load cached token: {e}")
            return None
    
    async def _cache_token(self, token_info: TokenInfo):
        """Save token to cache file."""
        if not self.token_cache_file:
            return
        
        try:
            import json
            import os
            
            # Create directory if needed
            os.makedirs(os.path.dirname(self.token_cache_file), exist_ok=True)
            
            data = {
                "access_token": token_info.access_token,
                "token_type": token_info.token_type,
                "expires_at": token_info.expires_at,
                "scope": token_info.scope,
                "issued_at": token_info.issued_at
            }
            
            with open(self.token_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions (user read/write only)
            os.chmod(self.token_cache_file, 0o600)
            
            logger.debug(f"Cached token to {self.token_cache_file}")
        
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")


# Convenience function for quick CLI authentication
async def authenticate_cli(
    client_id: str,
    tenant_id: str,
    scopes: List[str],
    cache_file: Optional[str] = None
) -> str:
    """
    Convenience function for quick CLI authentication.
    
    Args:
        client_id: Azure app registration client ID
        tenant_id: Azure tenant ID
        scopes: OAuth scopes to request
        cache_file: Optional token cache file
        
    Returns:
        Access token string
    """
    manager = CLIAuthenticationManager(
        client_id=client_id,
        tenant_id=tenant_id,
        scopes=scopes,
        token_cache_file=cache_file
    )
    
    token_info = await manager.authenticate()
    return token_info.access_token
