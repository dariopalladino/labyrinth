"""
Authentication middleware for Labyrinth agents and registry.

This module provides FastAPI middleware for token-based authentication
and authorization with configurable scope checking.
"""

import time
from typing import Dict, List, Optional, Set, Tuple, Callable, Any

import structlog
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .interfaces import TokenValidator, ValidationResult
from .exceptions import AuthenticationError, AuthorizationError

logger = structlog.get_logger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for token authentication and authorization.
    
    This middleware validates JWT tokens on incoming requests and enforces
    scope-based authorization for protected endpoints.
    """
    
    def __init__(
        self,
        app,
        token_validator: TokenValidator,
        required_scope: str = "agentic_ai_solution",
        protected_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        require_https: bool = False,
    ):
        """
        Initialize authentication middleware.
        
        Args:
            app: FastAPI application instance
            token_validator: Token validator for authentication
            required_scope: Default required scope for protected endpoints
            protected_paths: List of path prefixes that require authentication
            exclude_paths: List of path prefixes to exclude from authentication
            require_https: Whether to require HTTPS for authenticated requests
        """
        super().__init__(app)
        self.token_validator = token_validator
        self.required_scope = required_scope
        self.protected_paths = protected_paths or []
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.require_https = require_https
        
        self._logger = logger.bind(middleware="auth")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process incoming request and validate authentication if required.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint handler
            
        Returns:
            HTTP response
        """
        # Check if path should be authenticated
        if not self._should_authenticate(request.url.path):
            return await call_next(request)
        
        # Require HTTPS if configured
        if self.require_https and request.url.scheme != "https":
            self._logger.warning("HTTPS required for authenticated request", path=request.url.path)
            return Response(
                content="HTTPS required for authenticated requests",
                status_code=400
            )
        
        try:
            # Extract and validate token
            validation_result = await self._validate_request_token(request)
            
            if not validation_result.is_authenticated:
                self._logger.warning(
                    "Authentication failed",
                    path=request.url.path,
                    error=validation_result.error_message
                )
                return Response(
                    content=f"Authentication failed: {validation_result.error_message}",
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Add authentication info to request state
            request.state.auth_info = {
                "validated": True,
                "principal_id": validation_result.principal_id,
                "principal_name": validation_result.principal_name,
                "scopes": validation_result.scopes,
                "token_info": validation_result.token_info,
            }
            
            self._logger.debug(
                "Request authenticated",
                path=request.url.path,
                principal_id=validation_result.principal_id,
                scopes=list(validation_result.scopes) if validation_result.scopes else []
            )
            
            # Continue to next handler
            return await call_next(request)
            
        except Exception as e:
            self._logger.error(
                "Authentication middleware error",
                path=request.url.path,
                error=str(e)
            )
            return Response(
                content="Internal authentication error",
                status_code=500
            )
    
    def _should_authenticate(self, path: str) -> bool:
        """Check if a path requires authentication."""
        # Check excluded paths first
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        # If no protected paths specified, authenticate all non-excluded paths
        if not self.protected_paths:
            return True
        
        # Check if path matches any protected path
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        
        return False
    
    async def _validate_request_token(self, request: Request) -> ValidationResult:
        """Extract and validate token from request."""
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return ValidationResult(
                is_valid=False,
                error_message="Missing Authorization header"
            )
        
        if not auth_header.startswith("Bearer "):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid authorization scheme. Use 'Bearer <token>'"
            )
        
        access_token = auth_header[7:]  # Remove "Bearer " prefix
        if not access_token:
            return ValidationResult(
                is_valid=False,
                error_message="Missing access token"
            )
        
        # Validate token
        return await self.token_validator.validate(
            access_token=access_token,
            required_scopes={self.required_scope}
        )


class ScopeBasedAuthMiddleware(AuthenticationMiddleware):
    """
    Enhanced authentication middleware with per-endpoint scope requirements.
    
    This middleware allows different endpoints to require different scopes
    while maintaining backward compatibility with the base middleware.
    """
    
    def __init__(
        self,
        app,
        token_validator: TokenValidator,
        required_scope: str = "agentic_ai_solution",
        endpoint_scopes: Optional[Dict[str, Set[str]]] = None,
        protected_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        require_https: bool = False,
    ):
        """
        Initialize scope-based authentication middleware.
        
        Args:
            app: FastAPI application instance
            token_validator: Token validator for authentication
            required_scope: Default required scope
            endpoint_scopes: Mapping of path prefixes to required scopes
            protected_paths: List of path prefixes that require authentication
            exclude_paths: List of path prefixes to exclude from authentication
            require_https: Whether to require HTTPS
        """
        super().__init__(
            app, token_validator, required_scope,
            protected_paths, exclude_paths, require_https
        )
        self.endpoint_scopes = endpoint_scopes or {}
    
    def _get_required_scopes(self, path: str) -> Set[str]:
        """Get required scopes for a specific path."""
        # Check endpoint-specific scopes
        for endpoint_path, scopes in self.endpoint_scopes.items():
            if path.startswith(endpoint_path):
                return scopes
        
        # Fall back to default scope
        return {self.required_scope}
    
    async def _validate_request_token(self, request: Request) -> ValidationResult:
        """Extract and validate token with path-specific scopes."""
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return ValidationResult(
                is_valid=False,
                error_message="Missing Authorization header"
            )
        
        if not auth_header.startswith("Bearer "):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid authorization scheme. Use 'Bearer <token>'"
            )
        
        access_token = auth_header[7:]  # Remove "Bearer " prefix
        if not access_token:
            return ValidationResult(
                is_valid=False,
                error_message="Missing access token"
            )
        
        # Get required scopes for this path
        required_scopes = self._get_required_scopes(request.url.path)
        
        # Validate token with path-specific scopes
        return await self.token_validator.validate(
            access_token=access_token,
            required_scopes=required_scopes
        )


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract current user information from authenticated request.
    
    This function should be used in FastAPI endpoints to get the
    current authenticated user information.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with user information or None if not authenticated
    """
    return getattr(request.state, "auth_info", None)


def require_scope(required_scope: str) -> Callable:
    """
    Decorator to require specific scope for an endpoint.
    
    Args:
        required_scope: Scope that must be present in the token
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Find request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get("request")
            
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Cannot find request object for scope validation"
                )
            
            # Check if user is authenticated
            auth_info = get_current_user(request)
            if not auth_info:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            # Check if user has required scope
            user_scopes = auth_info.get("scopes", set())
            if required_scope not in user_scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required scope '{required_scope}' not present"
                )
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class HTTPBearerWithScopes(HTTPBearer):
    """
    Enhanced HTTPBearer security scheme with scope validation.
    
    This can be used as a dependency in FastAPI endpoints for
    fine-grained scope-based authorization.
    """
    
    def __init__(
        self,
        token_validator: TokenValidator,
        required_scopes: Optional[Set[str]] = None,
        auto_error: bool = True,
    ):
        """
        Initialize bearer auth with scope validation.
        
        Args:
            token_validator: Token validator for authentication
            required_scopes: Scopes required for this endpoint
            auto_error: Whether to raise HTTPException on auth failure
        """
        super().__init__(auto_error=auto_error)
        self.token_validator = token_validator
        self.required_scopes = required_scopes or {"agentic_ai_solution"}
    
    async def __call__(self, request: Request) -> Optional[ValidationResult]:
        """
        Validate bearer token and scopes.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult if authentication successful
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            return None
        
        # Validate token
        result = await self.token_validator.validate(
            access_token=credentials.credentials,
            required_scopes=self.required_scopes
        )
        
        if not result.is_authenticated:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail=result.error_message,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return result
