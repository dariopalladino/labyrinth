"""
Authenticated agent registry for Labyrinth.

This module provides an authenticated agent registry that supports
token-based authentication and authorization for agent operations.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set

import structlog
from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from a2a import types as a2a_types

from labyrinth.utils.config import Config, get_config
from labyrinth.utils.exceptions import LabyrinthError
from labyrinth.auth import (
    AuthenticationMiddleware,
    ScopeBasedAuthMiddleware,
    TokenValidator,
    get_current_user,
    require_scope,
)
from .registry import AgentRegistry, AgentRegistration

logger = structlog.get_logger(__name__)


class AuthenticatedRegistryServer:
    """
    HTTP server for the authenticated agent registry.
    
    This registry server enforces authentication and authorization
    for all agent operations using OAuth/OpenID tokens.
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        token_validator: Optional[TokenValidator] = None,
        host: str = "0.0.0.0",
        port: int = 8888,
        require_https: bool = False,
        default_scope: str = "agentic_ai_solution",
    ):
        """
        Initialize authenticated registry server.
        
        Args:
            registry: Agent registry implementation
            token_validator: Token validator for authentication
            host: Host to bind server to
            port: Port to bind server to
            require_https: Whether to require HTTPS
            default_scope: Default required scope for operations
        """
        self.registry = registry or AgentRegistry()
        self.token_validator = token_validator
        self.host = host
        self.port = port
        self.require_https = require_https
        self.default_scope = default_scope
        
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """
        Create FastAPI application with authenticated registry endpoints.
        """
        app = FastAPI(
            title="Labyrinth Authenticated Agent Registry",
            description="Authenticated registry for discovering and managing Labyrinth agents",
            version="1.0.0"
        )
        
        # Add authentication middleware if token validator is provided
        if self.token_validator:
            # Define scope requirements for different endpoints
            endpoint_scopes = {
                "/agents/": {self.default_scope},  # All agent operations require default scope
                "/stats": {self.default_scope},    # Stats require authentication
            }
            
            # Add scope-based authentication middleware
            auth_middleware = ScopeBasedAuthMiddleware(
                app=app,
                token_validator=self.token_validator,
                required_scope=self.default_scope,
                endpoint_scopes=endpoint_scopes,
                exclude_paths=["/", "/health", "/docs", "/redoc", "/openapi.json"],
                require_https=self.require_https,
            )
            
            app.add_middleware(
                type(auth_middleware),
                **auth_middleware.__dict__
            )
        
        @app.on_event("startup")
        async def startup_event():
            await self.registry.start()
        
        @app.on_event("shutdown")
        async def shutdown_event():
            await self.registry.stop()
        
        @app.get("/")
        async def root():
            return {
                "service": "Labyrinth Authenticated Agent Registry", 
                "status": "running",
                "authentication": "enabled" if self.token_validator else "disabled"
            }
        
        @app.get("/health")
        async def health():
            """Health check endpoint (no authentication required)."""
            stats = await self.registry.get_stats()
            return {"status": "healthy", "stats": stats}
        
        @app.post("/agents/{agent_id}/register")
        async def register_agent(agent_id: str, registration_data: dict, request: Request):
            """
            Register an agent (requires authentication).
            
            The authenticated user must have the required scope to register agents.
            """
            try:
                # Log authentication info if available
                auth_info = get_current_user(request)
                if auth_info:
                    logger.info(
                        "Agent registration request",
                        agent_id=agent_id,
                        principal_id=auth_info.get("principal_id"),
                        principal_name=auth_info.get("principal_name")
                    )
                
                # Extract agent card and base URL from registration data
                agent_card_data = registration_data.get("agent_card")
                base_url = registration_data.get("base_url")
                
                if not agent_card_data or not base_url:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing agent_card or base_url in registration data"
                    )
                
                agent_card = a2a_types.AgentCard(**agent_card_data)
                await self.registry.register_agent(agent_id, agent_card, base_url)
                
                return {"status": "registered", "agent_id": agent_id}
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.delete("/agents/{agent_id}")
        async def unregister_agent(agent_id: str, request: Request):
            """
            Unregister an agent (requires authentication).
            """
            auth_info = get_current_user(request)
            if auth_info:
                logger.info(
                    "Agent unregistration request",
                    agent_id=agent_id,
                    principal_id=auth_info.get("principal_id")
                )
            
            success = await self.registry.unregister_agent(agent_id)
            if success:
                return {"status": "unregistered", "agent_id": agent_id}
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        @app.post("/agents/{agent_id}/heartbeat")
        async def agent_heartbeat(agent_id: str, request: Request):
            """
            Send heartbeat for an agent (requires authentication).
            
            Agents must authenticate to send heartbeats for themselves.
            """
            auth_info = get_current_user(request)
            if auth_info:
                logger.debug(
                    "Agent heartbeat",
                    agent_id=agent_id,
                    principal_id=auth_info.get("principal_id")
                )
            
            success = await self.registry.heartbeat(agent_id)
            if success:
                return {"status": "heartbeat_updated", "agent_id": agent_id}
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not registered")
        
        @app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str, request: Request):
            """
            Get agent details (requires authentication).
            """
            registration = await self.registry.get_agent(agent_id)
            if registration:
                return registration.to_dict()
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        @app.get("/agents")
        async def list_agents(
            skill: Optional[str] = None,
            healthy_only: bool = True,
            request: Request = None
        ):
            """
            List all agents (requires authentication).
            """
            agents = await self.registry.list_agents(
                skill_filter=skill,
                healthy_only=healthy_only
            )
            return {"agents": agents, "count": len(agents)}
        
        @app.get("/stats")
        async def get_stats(request: Request):
            """
            Get registry statistics (requires authentication).
            """
            auth_info = get_current_user(request)
            stats = await self.registry.get_stats()
            
            # Add authentication info to stats
            if auth_info:
                stats["authenticated_as"] = {
                    "principal_id": auth_info.get("principal_id"),
                    "principal_name": auth_info.get("principal_name"),
                    "scopes": list(auth_info.get("scopes", set())),
                }
            
            return stats
        
        return app
    
    async def start(self) -> None:
        """
        Start the authenticated registry server.
        """
        import uvicorn
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()


class RegistryAuthenticationManager:
    """
    Helper class for managing authentication in registry servers.
    
    This class provides utilities for setting up authentication
    providers and validators for registry servers.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize authentication manager.
        
        Args:
            config: Configuration object
        """
        self.config = config or get_config()
        self._logger = logger.bind(component="auth_manager")
    
    def create_azure_entra_validator(
        self,
        tenant_id: str,
        default_scope: str = "agentic_ai_solution",
        **kwargs
    ) -> TokenValidator:
        """
        Create Azure Entra ID token validator.
        
        Args:
            tenant_id: Azure tenant ID
            default_scope: Default required scope
            **kwargs: Additional arguments for Azure provider
            
        Returns:
            Configured token validator
        """
        from labyrinth.auth.providers import AzureEntraAuthProvider
        from labyrinth.auth.validators import DefaultTokenValidator
        
        # Create Azure Entra ID provider
        auth_provider = AzureEntraAuthProvider(
            tenant_id=tenant_id,
            default_scope=default_scope,
            **kwargs
        )
        
        # Create validator using the provider
        validator = DefaultTokenValidator(
            auth_provider=auth_provider,
            required_scope=default_scope,
        )
        
        self._logger.info("Created Azure Entra ID validator", tenant_id=tenant_id)
        return validator
    
    def create_scope_only_validator(
        self,
        required_scope: str = "agentic_ai_solution"
    ) -> TokenValidator:
        """
        Create simple scope-only validator for development.
        
        Args:
            required_scope: Required scope for validation
            
        Returns:
            Scope-only token validator
        """
        from labyrinth.auth.validators import ScopeOnlyValidator
        
        validator = ScopeOnlyValidator(required_scope=required_scope)
        
        self._logger.info("Created scope-only validator", scope=required_scope)
        return validator
