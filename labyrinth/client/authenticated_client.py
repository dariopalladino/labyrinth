"""
Authenticated agent client for Labyrinth.

This module provides an authenticated client that automatically acquires
and uses OAuth/OpenID tokens for agent-to-agent communication.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set

import httpx
import structlog

from labyrinth.utils.config import Config, get_config
from labyrinth.utils.exceptions import LabyrinthError
from labyrinth.auth import (
    AuthenticationProvider,
    AuthenticationCredentials,
    TokenInfo,
    CredentialType,
    AuthenticationError,
)
from .base import AgentClient

logger = structlog.get_logger(__name__)


class AuthenticatedAgentClient(AgentClient):
    """
    Enhanced agent client with automatic authentication.
    
    This client automatically acquires and manages OAuth tokens
    for authenticated agent-to-agent communication.
    """
    
    def __init__(
        self,
        auth_provider: AuthenticationProvider,
        credentials: AuthenticationCredentials,
        config: Optional[Config] = None,
        default_scopes: Optional[List[str]] = None,
        token_refresh_threshold: int = 300,  # Refresh token 5 minutes before expiry
    ):
        """
        Initialize authenticated agent client.
        
        Args:
            auth_provider: Authentication provider for token management
            credentials: Authentication credentials
            config: Configuration object
            default_scopes: Default scopes for token requests
            token_refresh_threshold: Seconds before expiry to refresh token
        """
        super().__init__(config)
        
        self.auth_provider = auth_provider
        self.credentials = credentials
        self.default_scopes = default_scopes or ["agentic_ai_solution"]
        self.token_refresh_threshold = token_refresh_threshold
        
        # Token management
        self._current_token: Optional[TokenInfo] = None
        self._token_lock = asyncio.Lock()
        
        self._logger = logger.bind(
            client="authenticated",
            credential_type=credentials.credential_type.value
        )
    
    async def _get_valid_token(self, scopes: Optional[List[str]] = None) -> TokenInfo:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            scopes: Requested scopes (uses default if None)
            
        Returns:
            Valid TokenInfo
            
        Raises:
            AuthenticationError: If token acquisition fails
        """
        effective_scopes = scopes or self.default_scopes
        
        async with self._token_lock:
            # Check if current token is valid
            if self._current_token:
                if not self._current_token.is_expired:
                    # Check if token has required scopes
                    if set(effective_scopes).issubset(self._current_token.scopes):
                        # Check if token needs refresh soon
                        if (self._current_token.expires_at and 
                            time.time() + self.token_refresh_threshold < self._current_token.expires_at):
                            return self._current_token
                
                self._logger.debug("Current token expired or insufficient scopes, refreshing")
            
            # Acquire new token
            self._logger.info("Acquiring access token", scopes=effective_scopes)
            
            try:
                token_info = await self.auth_provider.authenticate(
                    credentials=self.credentials,
                    scopes=effective_scopes
                )
                
                self._current_token = token_info
                
                self._logger.info(
                    "Access token acquired",
                    expires_in=token_info.expires_in,
                    scopes=token_info.scope
                )
                
                return token_info
                
            except Exception as e:
                self._logger.error("Failed to acquire access token", error=str(e))
                raise AuthenticationError(f"Token acquisition failed: {e}")
    
    async def _make_authenticated_request(
        self,
        method: str,
        url: str,
        scopes: Optional[List[str]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an authenticated HTTP request.
        
        Args:
            method: HTTP method
            url: Request URL
            scopes: Required scopes for this request
            **kwargs: Additional request arguments
            
        Returns:
            HTTP response
        """
        # Get valid token
        token_info = await self._get_valid_token(scopes)
        
        # Add authorization header
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token_info.access_token}"
        kwargs["headers"] = headers
        
        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            # Handle authentication errors
            if response.status_code == 401:
                self._logger.warning("Request returned 401, token may be invalid")
                # Clear current token to force refresh on next request
                async with self._token_lock:
                    self._current_token = None
                raise AuthenticationError("Request authentication failed")
            
            return response
    
    async def send_message(
        self,
        to_agent: str,
        message: str,
        skill: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an authenticated message to another agent.
        
        Args:
            to_agent: Target agent ID
            message: Message content
            skill: Skill to invoke
            parameters: Additional parameters
            **kwargs: Additional arguments
            
        Returns:
            Response from target agent
        """
        # Discover target agent
        agent_info = await self.discover_agent(to_agent)
        if not agent_info:
            raise ValueError(f"Cannot discover agent: {to_agent}")
        
        # Prepare request payload
        payload = {
            "message": message,
            "from_agent": self.config.agent_id,
        }
        
        if skill:
            payload["skill"] = skill
        
        if parameters:
            payload["parameters"] = parameters
        
        # Make authenticated request
        response = await self._make_authenticated_request(
            method="POST",
            url=f"{agent_info['url']}/messages",
            json=payload,
            **kwargs
        )
        
        response.raise_for_status()
        return response.json()
    
    async def register_with_registry(
        self,
        registry_url: str,
        agent_card: Dict[str, Any],
        base_url: str,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Register with an authenticated registry.
        
        Args:
            registry_url: Registry server URL
            agent_card: Agent card information
            base_url: Agent's base URL
            agent_id: Agent identifier (uses config if None)
            **kwargs: Additional arguments
            
        Returns:
            Registration response
        """
        effective_agent_id = agent_id or self.config.agent_id
        
        registration_data = {
            "agent_card": agent_card,
            "base_url": base_url
        }
        
        response = await self._make_authenticated_request(
            method="POST",
            url=f"{registry_url}/agents/{effective_agent_id}/register",
            json=registration_data,
            **kwargs
        )
        
        response.raise_for_status()
        return response.json()
    
    async def send_heartbeat(
        self,
        registry_url: str,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send authenticated heartbeat to registry.
        
        Args:
            registry_url: Registry server URL
            agent_id: Agent identifier (uses config if None)
            **kwargs: Additional arguments
            
        Returns:
            Heartbeat response
        """
        effective_agent_id = agent_id or self.config.agent_id
        
        response = await self._make_authenticated_request(
            method="POST",
            url=f"{registry_url}/agents/{effective_agent_id}/heartbeat",
            **kwargs
        )
        
        response.raise_for_status()
        return response.json()
    
    async def list_agents(
        self,
        registry_url: str,
        skill_filter: Optional[str] = None,
        healthy_only: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List agents from authenticated registry.
        
        Args:
            registry_url: Registry server URL
            skill_filter: Filter by skill name
            healthy_only: Only return healthy agents
            **kwargs: Additional arguments
            
        Returns:
            List of agent information
        """
        params = {}
        if skill_filter:
            params["skill"] = skill_filter
        if not healthy_only:
            params["healthy_only"] = False
        
        response = await self._make_authenticated_request(
            method="GET",
            url=f"{registry_url}/agents",
            params=params,
            **kwargs
        )
        
        response.raise_for_status()
        data = response.json()
        return data.get("agents", [])
    
    async def get_registry_stats(
        self,
        registry_url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get authenticated registry statistics.
        
        Args:
            registry_url: Registry server URL
            **kwargs: Additional arguments
            
        Returns:
            Registry statistics
        """
        response = await self._make_authenticated_request(
            method="GET",
            url=f"{registry_url}/stats",
            **kwargs
        )
        
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Clean up client resources."""
        # Clear cached token
        async with self._token_lock:
            self._current_token = None
        
        await super().close()


class AuthenticatedClientManager:
    """
    Manager for creating authenticated clients with different credential types.
    
    This class provides factory methods for creating authenticated clients
    using various authentication methods.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize client manager.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self._logger = logger.bind(component="client_manager")
    
    async def create_client_credentials_client(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        scopes: Optional[List[str]] = None,
        auth_provider: Optional[AuthenticationProvider] = None,
    ) -> AuthenticatedAgentClient:
        """
        Create authenticated client using client credentials.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            tenant_id: Azure tenant ID
            scopes: Default scopes
            auth_provider: Custom authentication provider
            
        Returns:
            Configured authenticated client
        """
        # Create credentials
        credentials = AuthenticationCredentials(
            credential_type=CredentialType.CLIENT_CREDENTIALS,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
        )
        
        # Use provided auth provider or create Azure Entra ID provider
        if not auth_provider:
            from labyrinth.auth.providers import AzureEntraAuthProvider
            auth_provider = AzureEntraAuthProvider(tenant_id=tenant_id)
        
        client = AuthenticatedAgentClient(
            auth_provider=auth_provider,
            credentials=credentials,
            config=self.config,
            default_scopes=scopes or ["agentic_ai_solution"],
        )
        
        self._logger.info("Created client credentials client", client_id=client_id)
        return client
    
    async def create_managed_identity_client(
        self,
        client_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        auth_provider: Optional[AuthenticationProvider] = None,
    ) -> AuthenticatedAgentClient:
        """
        Create authenticated client using managed identity.
        
        Args:
            client_id: User-assigned managed identity client ID (None for system-assigned)
            scopes: Default scopes
            auth_provider: Custom authentication provider
            
        Returns:
            Configured authenticated client
        """
        # Create credentials
        credentials = AuthenticationCredentials(
            credential_type=CredentialType.MANAGED_IDENTITY,
            client_id=client_id,
        )
        
        # Use provided auth provider or create Azure Entra ID provider
        if not auth_provider:
            from labyrinth.auth.providers import AzureEntraAuthProvider
            auth_provider = AzureEntraAuthProvider()
        
        client = AuthenticatedAgentClient(
            auth_provider=auth_provider,
            credentials=credentials,
            config=self.config,
            default_scopes=scopes or ["agentic_ai_solution"],
        )
        
        identity_type = "user-assigned" if client_id else "system-assigned"
        self._logger.info(f"Created {identity_type} managed identity client", client_id=client_id)
        return client
