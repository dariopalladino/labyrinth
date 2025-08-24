#!/usr/bin/env python3
"""
Example showing how to use the Labyrinth agent registry.

This script demonstrates:
1. Starting a registry server
2. Registering agents with the registry
3. Discovering agents through the registry
4. Querying agent statistics and health
"""

import asyncio
import aiohttp
from labyrinth.server import Agent, Skill, RegistryServer, AgentRegistry

async def echo_skill(message: str) -> str:
    """Simple echo skill for testing."""
    return f"Echo: {message}"

async def create_test_agent():
    """Create a test agent for demonstration."""
    agent = Agent(
        name="Test Agent",
        description="A simple test agent",
        host="localhost",
        port=8080
    )
    
    # Add the echo skill
    agent.add_skill(
        name="echo",
        func=echo_skill,
        description="Echo input back to caller"
    )
    
    return agent

async def start_registry_server():
    """Start a registry server."""
    print("Starting registry server...")
    
    registry = AgentRegistry()
    server = RegistryServer(registry=registry, host="localhost", port=8888)
    
    # Start the server in a separate task
    server_task = asyncio.create_task(server.start())
    
    # Give the server time to start
    await asyncio.sleep(1)
    
    return server_task, registry

async def register_agent_with_registry(agent: Agent, registry_url: str = "http://localhost:8888"):
    """Register an agent with the registry."""
    print(f"Registering agent {agent.id} with registry...")
    
    # Prepare registration data
    registration_data = {
        "agent_card": agent.get_agent_card().model_dump(),
        "base_url": f"http://{agent.host}:{agent.port}"
    }
    
    # Register with the registry
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{registry_url}/agents/{agent.id}/register",
            json=registration_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"Agent registered successfully: {result}")
                return True
            else:
                error = await response.text()
                print(f"Failed to register agent: {error}")
                return False

async def list_agents(registry_url: str = "http://localhost:8888"):
    """List all registered agents."""
    print("Listing registered agents...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{registry_url}/agents") as response:
            if response.status == 200:
                result = await response.json()
                print(f"Found {result['count']} registered agents:")
                for agent in result['agents']:
                    print(f"  - {agent['name']} ({agent['agent_id']})")
                    print(f"    URL: {agent['url']}")
                    print(f"    Skills: {', '.join(agent['skills'])}")
                    print(f"    Healthy: {agent['healthy']}")
                    print()
                return result
            else:
                error = await response.text()
                print(f"Failed to list agents: {error}")
                return None

async def get_registry_stats(registry_url: str = "http://localhost:8888"):
    """Get registry statistics."""
    print("Getting registry statistics...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{registry_url}/stats") as response:
            if response.status == 200:
                stats = await response.json()
                print("Registry Statistics:")
                print(f"  Total agents: {stats['total_agents']}")
                print(f"  Healthy agents: {stats['healthy_agents']}")
                print(f"  Stale agents: {stats['stale_agents']}")
                print(f"  Uptime: {stats['uptime_seconds']:.1f} seconds")
                
                if stats['skill_counts']:
                    print("  Skill counts:")
                    for skill, count in stats['skill_counts'].items():
                        print(f"    - {skill}: {count}")
                print()
                return stats
            else:
                error = await response.text()
                print(f"Failed to get registry stats: {error}")
                return None

async def send_heartbeat(agent_id: str, registry_url: str = "http://localhost:8888"):
    """Send heartbeat for an agent."""
    print(f"Sending heartbeat for agent {agent_id}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{registry_url}/agents/{agent_id}/heartbeat") as response:
            if response.status == 200:
                result = await response.json()
                print(f"Heartbeat sent: {result}")
                return True
            else:
                error = await response.text()
                print(f"Failed to send heartbeat: {error}")
                return False

async def main():
    """Main example function."""
    print("=== Labyrinth Agent Registry Example ===\n")
    
    # Start the registry server
    try:
        server_task, registry = await start_registry_server()
        print("Registry server started successfully!\n")
        
        # Create and register a test agent
        agent = await create_test_agent()
        
        # Register the agent
        success = await register_agent_with_registry(agent)
        if not success:
            print("Failed to register agent, exiting...")
            return
        
        print()
        
        # List all agents
        await list_agents()
        
        # Get registry stats
        await get_registry_stats()
        
        # Send heartbeat
        await send_heartbeat(agent.id)
        
        print()
        
        # List agents filtered by skill
        print("Listing agents with 'echo' skill...")
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8888/agents?skill=echo") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Found {result['count']} agents with 'echo' skill")
                    for agent_info in result['agents']:
                        print(f"  - {agent_info['name']} ({agent_info['agent_id']})")
        
        print("\n=== Example completed successfully! ===")
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if 'server_task' in locals():
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
