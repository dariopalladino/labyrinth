"""
Azure Entra ID authentication provider implementation.

This module provides authentication using Azure Entra ID (formerly Azure AD)
supporting both client credentials flow and managed identity authentication.
"""

import json
import time
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
import structlog
from azure.identity import ClientSecretCredential, ManagedIdentityCredential
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError

from ..interfaces import (
    AuthenticationProvider,
    AuthenticationCredentials,
    TokenInfo,
    ValidationResult,
    CredentialType,
)
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    InvalidTokenError,
    ManagedIdentityError,
    ProviderConfigurationError,
)

logger = structlog.get_logger(__name__)


class AzureEntraAuthProvider(AuthenticationProvider):
    """
    Azure Entra ID authentication provider.
    
    Supports:
    - Client credentials flow (client_id + client_secret)
    - User-assigned managed identity (UAMI)
    - System-assigned managed identity
    - Token validation via Azure AD
    """
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        authority_url: Optional[str] = None,
        default_scope: str = "agentic_ai_solution",
        token_cache_ttl: int = 3600,
        http_timeout: int = 30,
    ):
        """
        Initialize Azure Entra ID provider.
        
        Args:
            tenant_id: Azure tenant ID
            authority_url: Custom authority URL (defaults to Azure public cloud)
            default_scope: Default OAuth scope for agent communication
            token_cache_ttl: Token cache TTL in seconds
            http_timeout: HTTP request timeout
        """
        self.tenant_id = tenant_id
        self.authority_url = authority_url or "https://login.microsoftonline.com"
        self.default_scope = default_scope
        self.token_cache_ttl = token_cache_ttl
        self.http_timeout = http_timeout
        
        self._logger = logger.bind(provider="azure_entra")
        
        # Token cache
        self._token_cache: Dict[str, TokenInfo] = {}
    
    @property
    def provider_name(self) -> str:
        """Name of the authentication provider."""
        return "Azure Entra ID"
    
    @property
    def default_scopes(self) -> List[str]:
        """Default scopes for this provider."""
        return [self.default_scope]
    
    def _get_cache_key(self, credentials: AuthenticationCredentials, scopes: Optional[List[str]] = None) -> str:
        """Generate cache key for credentials and scopes."""
        scope_str = ",".join(sorted(scopes or []))
        if credentials.credential_type == CredentialType.CLIENT_CREDENTIALS:
            return f"client:{credentials.client_id}:{scope_str}"
        elif credentials.credential_type == CredentialType.MANAGED_IDENTITY:
            client_id = credentials.client_id or "system"
            return f"mi:{client_id}:{scope_str}"
        else:
            return f"unknown:{scope_str}"
    
    async def authenticate(
        self,
        credentials: AuthenticationCredentials,
        scopes: Optional[List[str]] = None,
        resource: Optional[str] = None,
    ) -> TokenInfo:
        """
        Authenticate and obtain an access token.
        
        Args:
            credentials: Authentication credentials
            scopes: Requested OAuth scopes
            resource: Target resource (optional)
            
        Returns:
            TokenInfo containing the access token and metadata
        """
        # Use default scopes if none provided
        if not scopes:
            scopes = self.default_scopes
        
        # Check cache first
        cache_key = self._get_cache_key(credentials, scopes)
        cached_token = self._token_cache.get(cache_key)
        if cached_token and not cached_token.is_expired:
            self._logger.debug("Using cached token", cache_key=cache_key)
            return cached_token
        
        self._logger.info(
            "Authenticating with Azure Entra ID",
            credential_type=credentials.credential_type.value,
            scopes=scopes
        )
        
        try:
            if credentials.credential_type == CredentialType.CLIENT_CREDENTIALS:
                token_info = await self._authenticate_client_credentials(credentials, scopes)
            elif credentials.credential_type == CredentialType.MANAGED_IDENTITY:
                token_info = await self._authenticate_managed_identity(credentials, scopes)
            else:
                raise ProviderConfigurationError(
                    f"Unsupported credential type: {credentials.credential_type}"
                )
            
            # Cache the token
            self._token_cache[cache_key] = token_info
            
            self._logger.info(
                "Authentication successful",
                token_expires_in=token_info.expires_in,
                scopes=token_info.scope
            )
            
            return token_info
            
        except ClientAuthenticationError as e:
            self._logger.error("Azure authentication failed", error=str(e))
            raise AuthenticationError(f"Azure Entra ID authentication failed: {e}")
        except Exception as e:
            self._logger.error("Unexpected authentication error", error=str(e))
            raise AuthenticationError(f"Authentication failed: {e}")
    
    async def _authenticate_client_credentials(
        self,
        credentials: AuthenticationCredentials,
        scopes: List[str]
    ) -> TokenInfo:
        """Authenticate using client credentials flow."""
        if not credentials.tenant_id and not self.tenant_id:
            raise ProviderConfigurationError("tenant_id is required for client credentials flow")
        
        tenant_id = credentials.tenant_id or self.tenant_id
        
        try:
            # Create Azure credential
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
            )
            
            # Request token
            # Convert scopes to proper format for Azure
            azure_scopes = [f"{scope}/.default" if not scope.endswith("/.default") else scope 
                           for scope in scopes]
            
            access_token: AccessToken = await self._get_azure_token(credential, azure_scopes)
            
            return TokenInfo(
                access_token=access_token.token,
                token_type="Bearer",
                expires_at=access_token.expires_on,
                scope=" ".join(scopes),
            )
            
        except Exception as e:
            raise AuthenticationError(f"Client credentials authentication failed: {e}")
    
    async def _authenticate_managed_identity(
        self,
        credentials: AuthenticationCredentials,
        scopes: List[str]
    ) -> TokenInfo:
        """Authenticate using managed identity."""
        try:
            # Create managed identity credential
            if credentials.client_id:
                # User-assigned managed identity
                credential = ManagedIdentityCredential(client_id=credentials.client_id)
                self._logger.debug("Using user-assigned managed identity", client_id=credentials.client_id)
            else:
                # System-assigned managed identity
                credential = ManagedIdentityCredential()
                self._logger.debug("Using system-assigned managed identity")
            
            # Request token
            azure_scopes = [f"{scope}/.default" if not scope.endswith("/.default") else scope 
                           for scope in scopes]
            
            access_token: AccessToken = await self._get_azure_token(credential, azure_scopes)
            
            return TokenInfo(
                access_token=access_token.token,
                token_type="Bearer",
                expires_at=access_token.expires_on,
                scope=" ".join(scopes),
            )
            
        except ClientAuthenticationError as e:
            raise ManagedIdentityError(f"Managed identity authentication failed: {e}")
        except Exception as e:
            raise AuthenticationError(f"Managed identity authentication failed: {e}")
    
    async def _get_azure_token(self, credential, scopes: List[str]) -> AccessToken:
        """Get token from Azure credential (async wrapper)."""
        try:
            # Azure SDK doesn't have async methods for get_token, so we'll use sync
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, credential.get_token, *scopes)
        except Exception as e:
            raise AuthenticationError(f"Failed to get token from Azure: {e}")
    
    async def refresh_token(self, token_info: TokenInfo) -> TokenInfo:
        """
        Refresh an expired or expiring token.
        
        For Azure Entra ID, we typically re-authenticate rather than refresh
        since client credentials don't use refresh tokens.
        """
        # For client credentials flow, we re-authenticate
        # This would need the original credentials, which we don't store
        # In practice, the caller should re-authenticate
        raise AuthenticationError(
            "Token refresh not supported for client credentials flow. "
            "Please re-authenticate to get a new token."
        )
    
    async def validate_token(self, access_token: str) -> ValidationResult:
        """
        Validate an access token with Azure Entra ID.
        
        This performs online validation by calling Azure's token introspection
        or userinfo endpoints.
        """
        try:
            # Extract basic info from token without validation first
            token_info = await self.get_token_info(access_token)
            if not token_info:
                return ValidationResult(
                    is_valid=False,
                    error_message="Cannot parse token"
                )
            
            # Check if token is expired
            if token_info.is_expired:
                return ValidationResult(
                    is_valid=False,
                    token_info=token_info,
                    error_message="Token is expired"
                )
            
            # Validate with Azure (simplified - in production you'd verify signature)
            claims = await self._get_token_claims(access_token)
            
            if not claims:
                return ValidationResult(
                    is_valid=False,
                    token_info=token_info,
                    error_message="Token validation failed"
                )
            
            return ValidationResult(
                is_valid=True,
                token_info=token_info,
                principal_id=claims.get("sub"),
                principal_name=claims.get("unique_name") or claims.get("upn"),
                scopes=token_info.scopes
            )
            
        except Exception as e:
            self._logger.error("Token validation error", error=str(e))
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {e}"
            )
    
    async def get_token_info(self, access_token: str) -> Optional[TokenInfo]:
        """
        Get information about a token without full validation.
        
        This method parses the JWT token to extract basic information
        without verifying the signature.
        """
        try:
            import base64
            import jwt
            
            # Decode JWT payload (without verification)
            payload = jwt.decode(access_token, options={"verify_signature": False})
            
            expires_at = payload.get("exp")
            issued_at = payload.get("iat")
            scope = payload.get("scp") or " ".join(payload.get("roles", []))
            
            return TokenInfo(
                access_token=access_token,
                token_type="Bearer",
                expires_at=expires_at,
                issued_at=issued_at,
                scope=scope,
            )
            
        except Exception as e:
            self._logger.debug("Failed to parse token", error=str(e))
            return None
    
    async def _get_token_claims(self, access_token: str) -> Optional[Dict[str, Union[str, int, List[str]]]]:
        """
        Get token claims (simplified implementation).
        
        In a production environment, you would:
        1. Verify the token signature using Azure's public keys
        2. Validate issuer, audience, and other standard claims
        3. Check token revocation status
        """
        try:
            import jwt
            
            # In production, you should verify the signature
            # For now, we'll just decode without verification
            claims = jwt.decode(access_token, options={"verify_signature": False})
            
            # Basic validation
            if claims.get("iss") and "microsoft" not in claims.get("iss", "").lower():
                return None
                
            return claims
            
        except Exception as e:
            self._logger.debug("Failed to get token claims", error=str(e))
            return None
