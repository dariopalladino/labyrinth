"""
Token validation implementations for Labyrinth authentication.
"""

import time
from typing import Dict, List, Optional, Set, Union

import structlog

from .interfaces import TokenValidator, AuthenticationProvider, ValidationResult, TokenInfo
from .exceptions import InvalidTokenError, InvalidScopeError

logger = structlog.get_logger(__name__)


class DefaultTokenValidator(TokenValidator):
    """
    Default token validator using an authentication provider.
    
    This validator delegates to the authentication provider for token validation
    and adds additional scope and claim checking logic.
    """
    
    def __init__(
        self,
        auth_provider: AuthenticationProvider,
        required_scope: str = "agentic_ai_solution",
        allow_expired_grace_period: int = 60,  # seconds
    ):
        """
        Initialize the validator.
        
        Args:
            auth_provider: Authentication provider for token validation
            required_scope: Default required scope for agent communication
            allow_expired_grace_period: Grace period for expired tokens (seconds)
        """
        self.auth_provider = auth_provider
        self.required_scope = required_scope
        self.allow_expired_grace_period = allow_expired_grace_period
        
        self._logger = logger.bind(validator="default")
    
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
        try:
            # Use provider's validation first
            provider_result = await self.auth_provider.validate_token(access_token)
            
            if not provider_result.is_valid:
                return provider_result
            
            # Additional validation logic
            token_info = provider_result.token_info
            if not token_info:
                return ValidationResult(
                    is_valid=False,
                    error_message="No token information available"
                )
            
            # Check required scopes
            effective_scopes = required_scopes or {self.required_scope}
            if not self._check_scopes(token_info, effective_scopes):
                missing_scopes = effective_scopes - token_info.scopes
                return ValidationResult(
                    is_valid=False,
                    token_info=token_info,
                    error_message=f"Missing required scopes: {missing_scopes}",
                    scopes=token_info.scopes
                )
            
            # Check additional claims if provided
            if additional_claims:
                claims = await self.extract_claims(access_token)
                if not self._check_additional_claims(claims, additional_claims):
                    return ValidationResult(
                        is_valid=False,
                        token_info=token_info,
                        error_message="Additional claim validation failed",
                        scopes=token_info.scopes
                    )
            
            # Check expiration with grace period
            if token_info.is_expired:
                if token_info.expires_at and (time.time() - token_info.expires_at) > self.allow_expired_grace_period:
                    return ValidationResult(
                        is_valid=False,
                        token_info=token_info,
                        error_message="Token is expired beyond grace period",
                        scopes=token_info.scopes
                    )
                else:
                    self._logger.warning("Token is expired but within grace period")
            
            # All checks passed
            return ValidationResult(
                is_valid=True,
                token_info=token_info,
                principal_id=provider_result.principal_id,
                principal_name=provider_result.principal_name,
                scopes=token_info.scopes
            )
            
        except Exception as e:
            self._logger.error("Token validation error", error=str(e))
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {e}"
            )
    
    async def extract_claims(self, access_token: str) -> Dict[str, Union[str, int, List[str]]]:
        """
        Extract claims from a token.
        
        Args:
            access_token: The token to parse
            
        Returns:
            Dictionary of token claims
        """
        try:
            import jwt
            
            # Decode without verification (provider should handle verification)
            claims = jwt.decode(access_token, options={"verify_signature": False})
            return claims
            
        except Exception as e:
            self._logger.debug("Failed to extract claims", error=str(e))
            return {}
    
    def _check_scopes(self, token_info: TokenInfo, required_scopes: Set[str]) -> bool:
        """Check if token has all required scopes."""
        if not required_scopes:
            return True
        
        token_scopes = token_info.scopes
        return required_scopes.issubset(token_scopes)
    
    def _check_additional_claims(
        self,
        claims: Dict[str, Union[str, int, List[str]]],
        required_claims: Dict[str, str]
    ) -> bool:
        """Check if token has required claim values."""
        for claim_name, expected_value in required_claims.items():
            actual_value = claims.get(claim_name)
            if actual_value != expected_value:
                self._logger.debug(
                    "Claim validation failed",
                    claim=claim_name,
                    expected=expected_value,
                    actual=actual_value
                )
                return False
        
        return True


class ScopeOnlyValidator(TokenValidator):
    """
    Simple validator that only checks token scopes without full validation.
    
    Useful for development or when you trust the token source but want
    to enforce scope-based authorization.
    """
    
    def __init__(self, required_scope: str = "agentic_ai_solution"):
        """
        Initialize scope-only validator.
        
        Args:
            required_scope: Required scope for validation
        """
        self.required_scope = required_scope
        self._logger = logger.bind(validator="scope_only")
    
    async def validate(
        self,
        access_token: str,
        required_scopes: Optional[Set[str]] = None,
        additional_claims: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Validate token by checking scopes only.
        
        Args:
            access_token: The token to validate
            required_scopes: Scopes that must be present
            additional_claims: Ignored in this validator
            
        Returns:
            ValidationResult with scope validation
        """
        try:
            claims = await self.extract_claims(access_token)
            if not claims:
                return ValidationResult(
                    is_valid=False,
                    error_message="Cannot parse token claims"
                )
            
            # Extract scopes from claims
            scopes_claim = claims.get("scp", claims.get("scope", ""))
            if isinstance(scopes_claim, list):
                token_scopes = set(scopes_claim)
            else:
                token_scopes = set(str(scopes_claim).split())
            
            # Check required scopes
            effective_scopes = required_scopes or {self.required_scope}
            if not effective_scopes.issubset(token_scopes):
                missing_scopes = effective_scopes - token_scopes
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required scopes: {missing_scopes}",
                    scopes=token_scopes
                )
            
            # Extract basic info
            expires_at = claims.get("exp")
            principal_id = claims.get("sub")
            principal_name = claims.get("unique_name") or claims.get("upn")
            
            # Check expiration
            if expires_at and time.time() >= expires_at:
                return ValidationResult(
                    is_valid=False,
                    error_message="Token is expired",
                    scopes=token_scopes
                )
            
            # Create token info
            token_info = TokenInfo(
                access_token=access_token,
                expires_at=expires_at,
                scope=" ".join(token_scopes)
            )
            
            return ValidationResult(
                is_valid=True,
                token_info=token_info,
                principal_id=principal_id,
                principal_name=principal_name,
                scopes=token_scopes
            )
            
        except Exception as e:
            self._logger.error("Scope validation error", error=str(e))
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation error: {e}"
            )
    
    async def extract_claims(self, access_token: str) -> Dict[str, Union[str, int, List[str]]]:
        """Extract claims from token."""
        try:
            import jwt
            return jwt.decode(access_token, options={"verify_signature": False})
        except Exception as e:
            self._logger.debug("Failed to extract claims", error=str(e))
            return {}
