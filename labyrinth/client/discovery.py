"""
Agent discovery service for Labyrinth.

This module provides functionality to discover, fetch, and cache agent cards
for agent-to-agent communication using the A2A SDK.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from a2a import types as a2a_types

from labyrinth.utils.config import Config, get_config
from labyrinth.utils.exceptions import (
    LabyrinthError,
    AgentError,
    AgentNotFoundError,
    CommunicationError,
)

logger = structlog.get_logger(__name__)


class AgentCardCache:
    """Cache for agent cards to avoid repeated fetches."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, agent_url: str) -> Optional[a2a_types.AgentCard]:
        """Get agent card from cache if not expired."""
        async with self._lock:
            if agent_url not in self._cache:
                return None
            
            # Check if expired
            if time.time() - self._timestamps[agent_url] > self.ttl_seconds:
                del self._cache[agent_url]
                del self._timestamps[agent_url]
                return None
            
            # Return cached card
            try:
                return a2a_types.AgentCard(**self._cache[agent_url])
            except Exception as e:
                logger.warning("Failed to deserialize cached agent card", error=str(e))
                del self._cache[agent_url]
                del self._timestamps[agent_url]
                return None
    
    async def set(self, agent_url: str, card: a2a_types.AgentCard) -> None:
        """Store agent card in cache."""
        async with self._lock:
            self._cache[agent_url] = card.model_dump()
            self._timestamps[agent_url] = time.time()
    
    async def invalidate(self, agent_url: str) -> None:
        """Remove agent card from cache."""
        async with self._lock:
            self._cache.pop(agent_url, None)
            self._timestamps.pop(agent_url, None)
    
    async def clear(self) -> None:
        """Clear all cached agent cards."""
        async with self._lock:
            self._cache.clear()
            self._timestamps.clear()


class AgentDiscoveryService:
    """Service for discovering and managing A2A agents."""
    
    def __init__(
        self, 
        config: Optional[Config] = None,
        cache_ttl: int = 300,
        http_timeout: int = 10
    ):
        self.config = config or get_config()
        self.cache = AgentCardCache(ttl_seconds=cache_ttl)
        self.http_timeout = http_timeout
        
        # Known agent registries and endpoints
        self._known_agents: Dict[str, str] = {}  # agent_id -> base_url
        self._agent_registries: List[str] = []   # Registry URLs
        
        self._logger = logger.bind(service="discovery")
    
    def add_known_agent(self, agent_id: str, base_url: str) -> None:
        """Add a known agent to the discovery service."""
        self._known_agents[agent_id] = base_url
        self._logger.info("Added known agent", agent_id=agent_id, base_url=base_url)
    
    def add_registry(self, registry_url: str) -> None:
        """Add an agent registry for discovery."""
        if registry_url not in self._agent_registries:
            self._agent_registries.append(registry_url)
            self._logger.info("Added agent registry", registry_url=registry_url)
    
    def set_default_registry(self, registry_url: str = "http://localhost:8888") -> None:
        """Set the default local registry."""
        self._agent_registries.insert(0, registry_url)
        self._logger.info("Set default registry", registry_url=registry_url)
    
    async def fetch_agent_card(self, agent_url: str) -> a2a_types.AgentCard:
        """
        Fetch agent card from the given URL.
        
        Args:
            agent_url: Base URL of the agent
            
        Returns:
            AgentCard object
            
        Raises:
            AgentNotFoundError: If agent card cannot be fetched
            CommunicationError: If there's a communication error
        """
        # Check cache first
        cached_card = await self.cache.get(agent_url)
        if cached_card:
            self._logger.debug("Using cached agent card", agent_url=agent_url)
            return cached_card
        
        self._logger.info("Fetching agent card", agent_url=agent_url)
        
        # Standard A2A well-known endpoints
        card_endpoints = [
            "/.well-known/agent-card",
            "/agent-card",
            "/.well-known/a2a/agent-card",
        ]
        
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            for endpoint in card_endpoints:
                try:
                    card_url = urljoin(agent_url.rstrip('/') + '/', endpoint.lstrip('/'))
                    
                    response = await client.get(card_url)
                    
                    if response.status_code == 200:
                        card_data = response.json()
                        card = a2a_types.AgentCard(**card_data)
                        
                        # Cache the card
                        await self.cache.set(agent_url, card)
                        
                        self._logger.info(
                            "Successfully fetched agent card",
                            agent_url=agent_url,
                            card_url=card_url,
                            agent_name=card.name
                        )
                        
                        return card
                    
                    elif response.status_code == 404:
                        # Try next endpoint
                        continue
                    else:
                        self._logger.warning(
                            "Unexpected status code fetching agent card",
                            card_url=card_url,
                            status_code=response.status_code
                        )
                        
                except httpx.RequestError as e:
                    self._logger.warning(
                        "Request error fetching agent card",
                        card_url=card_url,
                        error=str(e)
                    )
                    continue
                except Exception as e:
                    self._logger.warning(
                        "Error parsing agent card",
                        card_url=card_url,
                        error=str(e)
                    )
                    continue
        
        raise AgentNotFoundError(f"Could not fetch agent card from {agent_url}")
    
    async def discover_agent(self, agent_id: str) -> a2a_types.AgentCard:
        """
        Discover an agent by ID using various discovery methods.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentCard object
            
        Raises:
            AgentNotFoundError: If agent cannot be found
        """
        self._logger.info("Discovering agent", agent_id=agent_id)
        
        # 1. Check known agents first
        if agent_id in self._known_agents:
            agent_url = self._known_agents[agent_id]
            try:
                return await self.fetch_agent_card(agent_url)
            except Exception as e:
                self._logger.warning(
                    "Failed to fetch known agent card",
                    agent_id=agent_id,
                    agent_url=agent_url,
                    error=str(e)
                )
        
        # 2. Try agent registries
        for registry_url in self._agent_registries:
            try:
                card = await self._discover_from_registry(registry_url, agent_id)
                if card:
                    return card
            except Exception as e:
                self._logger.warning(
                    "Failed to discover from registry",
                    registry_url=registry_url,
                    agent_id=agent_id,
                    error=str(e)
                )
        
        # 3. Try DNS-based discovery (simplified)
        try:
            card = await self._discover_via_dns(agent_id)
            if card:
                return card
        except Exception as e:
            self._logger.warning(
                "Failed DNS discovery",
                agent_id=agent_id,
                error=str(e)
            )
        
        raise AgentNotFoundError(f"Agent {agent_id} not found")
    
    async def _discover_from_registry(
        self, 
        registry_url: str, 
        agent_id: str
    ) -> Optional[a2a_types.AgentCard]:
        """Discover agent from a registry service."""
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                # Try common registry endpoint patterns
                endpoints = [
                    f"/agents/{agent_id}",
                    f"/api/agents/{agent_id}",
                    f"/registry/agents/{agent_id}",
                    f"/discover/{agent_id}",
                ]
                
                for endpoint in endpoints:
                    url = urljoin(registry_url.rstrip('/') + '/', endpoint.lstrip('/'))
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different registry response formats
                        if "agent_url" in data or "url" in data:
                            # Registry returns agent URL
                            agent_url = data.get("agent_url") or data.get("url")
                            return await self.fetch_agent_card(agent_url)
                        
                        elif "agent_card" in data:
                            # Registry returns full agent card
                            return a2a_types.AgentCard(**data["agent_card"])
                        
                        elif "name" in data:
                            # Registry returns agent card directly
                            return a2a_types.AgentCard(**data)
                        
        except Exception as e:
            self._logger.debug(
                "Registry discovery failed",
                registry_url=registry_url,
                agent_id=agent_id,
                error=str(e)
            )
        
        return None
    
    async def _discover_via_dns(self, agent_id: str) -> Optional[a2a_types.AgentCard]:
        """Simplified DNS-based discovery."""
        # This is a simplified implementation
        # In a full system, this would do proper DNS TXT record lookups
        # or use service discovery mechanisms like Consul, etcd, etc.
        
        # Try common patterns
        possible_urls = [
            f"http://{agent_id}.agents.local:8080",
            f"http://{agent_id}.local:8080", 
            f"http://agent-{agent_id}.local:8080",
            f"https://{agent_id}.agents.example.com",
        ]
        
        for url in possible_urls:
            try:
                return await self.fetch_agent_card(url)
            except Exception:
                continue
        
        return None
    
    async def list_available_agents(self) -> List[Dict[str, Any]]:
        """
        List all available agents from various sources.
        
        Returns:
            List of agent information dictionaries
        """
        agents = []
        
        # Add known agents
        for agent_id, base_url in self._known_agents.items():
            try:
                card = await self.fetch_agent_card(base_url)
                agents.append({
                    "agent_id": agent_id,
                    "name": card.name,
                    "description": card.description,
                    "url": base_url,
                    "skills": [skill.name for skill in card.skills],
                    "source": "known"
                })
            except Exception as e:
                self._logger.warning(
                    "Failed to fetch card for known agent",
                    agent_id=agent_id,
                    error=str(e)
                )
        
        # Query registries for additional agents
        for registry_url in self._agent_registries:
            try:
                registry_agents = await self._list_from_registry(registry_url)
                agents.extend(registry_agents)
            except Exception as e:
                self._logger.warning(
                    "Failed to list agents from registry",
                    registry_url=registry_url,
                    error=str(e)
                )
        
        return agents
    
    async def _list_from_registry(self, registry_url: str) -> List[Dict[str, Any]]:
        """List agents from a registry service."""
        agents = []
        
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                # Try common registry list endpoints
                endpoints = [
                    "/agents",
                    "/api/agents",
                    "/registry/agents",
                    "/list",
                ]
                
                for endpoint in endpoints:
                    url = urljoin(registry_url.rstrip('/') + '/', endpoint.lstrip('/'))
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response formats
                        if isinstance(data, list):
                            agent_list = data
                        elif "agents" in data:
                            agent_list = data["agents"]
                        else:
                            continue
                        
                        for agent_info in agent_list:
                            agent_data = {
                                "source": "registry",
                                "registry_url": registry_url,
                            }
                            agent_data.update(agent_info)
                            agents.append(agent_data)
                        
                        break  # Successfully got data from this registry
                
        except Exception as e:
            self._logger.debug(
                "Failed to list agents from registry",
                registry_url=registry_url,
                error=str(e)
            )
        
        return agents
    
    async def health_check_agent(self, agent_url: str) -> Dict[str, Any]:
        """
        Perform a health check on an agent.
        
        Args:
            agent_url: Base URL of the agent
            
        Returns:
            Health check results
        """
        health_info = {
            "url": agent_url,
            "healthy": False,
            "response_time_ms": None,
            "error": None,
            "card_available": False,
        }
        
        start_time = time.time()
        
        try:
            # Try to fetch agent card as health check
            card = await self.fetch_agent_card(agent_url)
            
            response_time = (time.time() - start_time) * 1000
            
            health_info.update({
                "healthy": True,
                "response_time_ms": round(response_time, 2),
                "card_available": True,
                "agent_name": card.name,
                "skills_count": len(card.skills),
            })
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_info.update({
                "healthy": False,
                "response_time_ms": round(response_time, 2),
                "error": str(e),
            })
        
        return health_info


# Global discovery service instance
_discovery_service: Optional[AgentDiscoveryService] = None


def get_discovery_service() -> AgentDiscoveryService:
    """Get the global discovery service instance."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = AgentDiscoveryService()
    return _discovery_service


def set_discovery_service(service: AgentDiscoveryService) -> None:
    """Set the global discovery service instance."""
    global _discovery_service
    _discovery_service = service
