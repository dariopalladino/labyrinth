"""
Simple agent registry for Labyrinth.

This module provides a basic agent registry that agents can register with
and clients can query to discover available agents.
"""
from abc import ABC
import asyncio
import time
from typing import Any, Dict, List, Optional, Set

import structlog
from fastapi import FastAPI, HTTPException, Response, Request
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

logger = structlog.get_logger(__name__)


class AgentRegistration:
    """Represents a registered agent."""
    
    def __init__(
        self,
        agent_id: str,
        agent_card: a2a_types.AgentCard,
        base_url: str,
        registered_at: Optional[float] = None
    ):
        self.agent_id = agent_id
        self.agent_card = agent_card
        self.base_url = base_url
        self.registered_at = registered_at or time.time()
        self.last_heartbeat = self.registered_at
        self.healthy = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "name": self.agent_card.name,
            "description": self.agent_card.description,
            "url": self.base_url,
            "skills": [skill.name for skill in self.agent_card.skills],
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "healthy": self.healthy,
            "agent_card": self.agent_card.model_dump(),
        }
    
    def update_heartbeat(self) -> None:
        """Update heartbeat timestamp and mark as healthy."""
        self.last_heartbeat = time.time()
        self.healthy = True
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if registration is stale."""
        return time.time() - self.last_heartbeat > max_age_seconds


class AgentRegistryInterface(ABC):
    def __init__(
        self,
        config: Optional[Config] = None,
        heartbeat_interval: int = 60,
        stale_threshold: int = 300
    ):
        self.config = config or get_config()
        self.heartbeat_interval = heartbeat_interval
        self.stale_threshold = stale_threshold
        
        self._registrations: Dict[str, AgentRegistration] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        self._logger = logger.bind(service="registry")
    
    async def start(self) -> None:
        """Start the registry and cleanup tasks."""
    
    async def stop(self) -> None:
        """Stop the registry and cleanup tasks."""

    async def heartbeat(self, agent_id: str) -> bool:
        """
        Update heartbeat for a registered agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if heartbeat was updated
        """

    async def register_agent(
        self,
        agent_id: str,
        agent_card: a2a_types.AgentCard,
        base_url: str
    ) -> None:
        """
        Register an agent with the registry.
        
        Args:
            agent_id: Unique agent identifier
            agent_card: Agent card with capabilities
            base_url: Base URL where agent can be reached
        """

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: Agent identifier to unregister
            
        Returns:
            True if agent was found and unregistered
        """

    async def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """
        Get registration information for a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentRegistration if found, None otherwise
        """

    async def list_agents(
        self,
        skill_filter: Optional[str] = None,
        healthy_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all registered agents.
        
        Args:
            skill_filter: Filter agents by skill name
            healthy_only: Only return healthy agents
            
        Returns:
            List of agent information dictionaries
        """

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry stats
        """

# TODO:
# - Replace this AgentRegistry implementation with a database AgentRegistry
class AgentRegistryInMemory(AgentRegistryInterface):
    """Simple in-memory agent registry."""    
    # TODO: 
    # Agent Id is the name identifier of the Agent. It could be changed to an asset_id uuid4() identifier

    async def start(self) -> None:
        """Start the registry and cleanup tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._logger.info("Agent registry started")
    
    async def stop(self) -> None:
        """Stop the registry and cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        self._logger.info("Agent registry stopped")

    async def heartbeat(self, agent_id: str) -> bool:
        async with self._lock:
            if agent_id in self._registrations:
                self._registrations[agent_id].update_heartbeat()
                return True
            else:
                return False
    
    async def register_agent(
        self,
        agent_id: str,
        agent_card: a2a_types.AgentCard,
        base_url: str
    ) -> None:
        async with self._lock:
            registration = AgentRegistration(
                agent_id=agent_id,
                agent_card=agent_card,
                base_url=base_url
            )
            # TODO: add a boolean field as part of the registration to either lock or unlock an agent card from self override
            if len(self._registrations[agent_id]):
            # if self._registration[agent_id].card_lock:
            #   then cannot override 
            # else:
                self._logger.info(f"Agent {agent_id} already registered. It will be overwritten!")

            self._registrations[agent_id] = registration
            
            self._logger.info(
                "Agent registered",
                agent_id=agent_id,
                agent_name=agent_card.name,
                base_url=base_url,
                skills_count=len(agent_card.skills)
            )
    
    async def unregister_agent(self, agent_id: str) -> bool:
        async with self._lock:
            if agent_id in self._registrations:
                del self._registrations[agent_id]
                self._logger.info("Agent unregistered", agent_id=agent_id)
                return True
            else:
                self._logger.warning("Attempted to unregister unknown agent", agent_id=agent_id)
                return False
    
    
    async def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        async with self._lock:
            return self._registrations.get(agent_id)
    
    async def list_agents(
        self,
        skill_filter: Optional[str] = None,
        healthy_only: bool = True
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            agents = []
            
            for registration in self._registrations.values():
                # Skip unhealthy agents if requested
                if healthy_only and not registration.healthy:
                    continue
                
                # Apply skill filter
                if skill_filter:
                    skills = [skill.name for skill in registration.agent_card.skills]
                    if skill_filter not in skills:
                        continue
                
                agents.append(registration.to_dict())
            
            return agents
    
    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            total_agents = len(self._registrations)
            healthy_agents = sum(1 for r in self._registrations.values() if r.healthy)
            stale_agents = sum(1 for r in self._registrations.values() if r.is_stale(self.stale_threshold))
            
            # Collect skill statistics
            skill_counts = {}
            for registration in self._registrations.values():
                for skill in registration.agent_card.skills:
                    skill_counts[skill.name] = skill_counts.get(skill.name, 0) + 1
            
            return {
                "total_agents": total_agents,
                "healthy_agents": healthy_agents,
                "stale_agents": stale_agents,
                "skill_counts": skill_counts,
                "uptime_seconds": time.time() - (self._registrations and min(
                    r.registered_at for r in self._registrations.values()) or time.time())
            }
    
    async def _cleanup_loop(self) -> None:
        """
        Background task to clean up stale agent registrations.
        """
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._cleanup_stale_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error("Error in cleanup loop", error=str(e))
    
    async def _cleanup_stale_agents(self) -> None:
        """
        Remove stale agent registrations.
        """
        async with self._lock:
            stale_agents = []
            
            for agent_id, registration in self._registrations.items():
                if registration.is_stale(self.stale_threshold):
                    stale_agents.append(agent_id)
                    registration.healthy = False
            
            # Remove stale agents after additional grace period
            for agent_id in stale_agents:
                registration = self._registrations[agent_id]
                # Allow double the threshold before complete removal
                if registration.is_stale(self.stale_threshold * 2):
                    del self._registrations[agent_id]
                    self._logger.info(
                        "Removed stale agent registration",
                        agent_id=agent_id,
                        last_heartbeat=registration.last_heartbeat
                    )
                else:
                    self._logger.warning(
                        "Marked agent as unhealthy",
                        agent_id=agent_id,
                        last_heartbeat=registration.last_heartbeat
                    )


class RegistryServer:
    """
    HTTP server for the agent registry.
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistryInterface] = None,
        host: str = "0.0.0.0",
        port: int = 8888
    ):
        self.registry = registry or AgentRegistryInMemory()
        self.host = host
        self.port = port
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """
        Create FastAPI application with registry endpoints.
        """
        app = FastAPI(
            title="Labyrinth Agent Registry",
            description="Registry for discovering and managing Labyrinth agents",
            version="1.0.0"
        )
        
        @app.on_event("startup")
        async def startup_event():
            await self.registry.start()
        
        @app.on_event("shutdown")
        async def shutdown_event():
            await self.registry.stop()
        
        @app.get("/")
        async def root():
            return {"service": "Labyrinth Agent Registry", "status": "running"}
        
        @app.get("/health")
        async def health():
            stats = await self.registry.get_stats()
            return {"status": "healthy", "stats": stats}
        
        # TODO:
        # - add authentication (token validation)
        @app.post("/agents/{agent_id}/register")
        async def register_agent(agent_id: str, registration_data: dict):
            try:
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
        async def unregister_agent(agent_id: str):
            success = await self.registry.unregister_agent(agent_id)
            if success:
                return {"status": "unregistered", "agent_id": agent_id}
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        @app.post("/agents/{agent_id}/heartbeat")
        async def agent_heartbeat(agent_id: str):
            success = await self.registry.heartbeat(agent_id)
            if success:
                return {"status": "heartbeat_updated", "agent_id": agent_id}
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not registered")
        
        @app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str):
            registration = await self.registry.get_agent(agent_id)
            if registration:
                return registration.to_dict()
            else:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        @app.get("/agents")
        async def list_agents(
            skill: Optional[str] = None,
            healthy_only: bool = True
        ):
            agents = await self.registry.list_agents(
                skill_filter=skill,
                healthy_only=healthy_only
            )
            return {"agents": agents, "count": len(agents)}
        
        @app.get("/stats")
        async def get_stats():
            return await self.registry.get_stats()
        
        return app
    
    async def start(self) -> None:
        """
        Start the registry server.
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


def get_agent_registry(config=None, heartbeat_interval=None, stale_threshold=None):
    """ 
     Return an Instance of the AgentRegistry (i.e. AgentRegistryInMemory, AgentRegistryDatabase)
     through Dependency Injection
     For now AgentRegistryInMemory 
    """
    return AgentRegistryInMemory(config, heartbeat_interval, stale_threshold)


# Global registry instance
_global_registry: Optional[AgentRegistryInterface] = None


def get_registry() -> AgentRegistryInMemory:
    """Get the global registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = get_agent_registry()
    return _global_registry


def set_registry(registry: AgentRegistryInterface) -> None:
    """Set the global registry instance."""
    global _global_registry
    _global_registry = registry

