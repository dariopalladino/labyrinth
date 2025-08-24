#!/usr/bin/env python3
"""
CLI for managing the Labyrinth agent registry.
"""

import asyncio
import sys
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.json import JSON

from labyrinth.server.registry import RegistryServer, get_agent_registry


console = Console()


@click.group()
def registry():
    """Manage the Labyrinth agent registry."""
    pass


@registry.command()
@click.option("--host", default="0.0.0.0", help="Host to bind the registry server")
@click.option("--port", default=8888, help="Port to bind the registry server")
@click.option("--heartbeat-interval", default=60, help="Heartbeat check interval in seconds")
@click.option("--stale-threshold", default=300, help="Stale agent threshold in seconds")
def start(host: str, port: int, heartbeat_interval: int, stale_threshold: int):
    """Start the agent registry server."""
    console.print(f"[bold blue]Starting Labyrinth Agent Registry[/bold blue]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print(f"Heartbeat interval: {heartbeat_interval}s")
    console.print(f"Stale threshold: {stale_threshold}s")
    console.print()
    
    async def start_server():
        registry_impl = get_agent_registry(
            heartbeat_interval=heartbeat_interval,
            stale_threshold=stale_threshold
        )
        server = RegistryServer(
            registry=registry_impl,
            host=host,
            port=port
        )
        
        try:
            await server.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down registry server...[/yellow]")
        except Exception as e:
            console.print(f"[red]Error starting registry server: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(start_server())


@registry.command()
@click.option("--url", default="http://localhost:8888", help="Registry URL")
def status(url: str):
    """Check registry status."""
    
    async def check_status():
        try:
            async with httpx.AsyncClient() as client:
                # Check basic health
                response = await client.get(f"{url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    console.print("[green]✓[/green] Registry is healthy")
                    
                    # Display stats
                    stats = data.get("stats", {})
                    
                    table = Table(title="Registry Statistics")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="magenta")
                    
                    table.add_row("Total Agents", str(stats.get("total_agents", 0)))
                    table.add_row("Healthy Agents", str(stats.get("healthy_agents", 0)))
                    table.add_row("Stale Agents", str(stats.get("stale_agents", 0)))
                    table.add_row("Uptime (seconds)", f"{stats.get('uptime_seconds', 0):.1f}")
                    
                    console.print(table)
                    
                    # Show skill counts if available
                    skill_counts = stats.get("skill_counts", {})
                    if skill_counts:
                        console.print("\n[bold]Skill Distribution:[/bold]")
                        for skill, count in skill_counts.items():
                            console.print(f"  {skill}: {count}")
                else:
                    console.print(f"[red]✗[/red] Registry is unhealthy (HTTP {response.status_code})")
                    
        except httpx.ConnectError:
            console.print(f"[red]✗[/red] Cannot connect to registry at {url}")
        except Exception as e:
            console.print(f"[red]✗[/red] Error checking registry status: {e}")
    
    asyncio.run(check_status())


@registry.command()
@click.option("--url", default="http://localhost:8888", help="Registry URL")
@click.option("--skill", help="Filter by skill name")
@click.option("--unhealthy", is_flag=True, help="Show unhealthy agents too")
def list(url: str, skill: Optional[str], unhealthy: bool):
    """List registered agents."""
    
    async def list_agents():
        try:
            async with httpx.AsyncClient() as client:
                params = {}
                if skill:
                    params["skill"] = skill
                if unhealthy:
                    params["healthy_only"] = False
                
                response = await client.get(f"{url}/agents", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    agents = data.get("agents", [])
                    count = data.get("count", len(agents))
                    
                    if not agents:
                        console.print("[yellow]No agents found[/yellow]")
                        return
                    
                    table = Table(title=f"Registered Agents ({count} found)")
                    table.add_column("Agent ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("URL", style="blue")
                    table.add_column("Skills", style="magenta")
                    table.add_column("Status", style="red")
                    
                    for agent in agents:
                        status = "✓ Healthy" if agent.get("healthy", False) else "✗ Unhealthy"
                        skills = ", ".join(agent.get("skills", []))
                        
                        table.add_row(
                            agent.get("agent_id", "N/A"),
                            agent.get("name", "N/A"),
                            agent.get("url", "N/A"),
                            skills,
                            status
                        )
                    
                    console.print(table)
                else:
                    console.print(f"[red]Error listing agents (HTTP {response.status_code})[/red]")
                    
        except httpx.ConnectError:
            console.print(f"[red]✗[/red] Cannot connect to registry at {url}")
        except Exception as e:
            console.print(f"[red]Error listing agents: {e}[/red]")
    
    asyncio.run(list_agents())


@registry.command()
@click.argument("agent_id")
@click.option("--url", default="http://localhost:8888", help="Registry URL")
def show(agent_id: str, url: str):
    """Show details for a specific agent."""
    
    async def show_agent():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/agents/{agent_id}")
                
                if response.status_code == 200:
                    agent_data = response.json()
                    
                    console.print(f"[bold green]Agent: {agent_data.get('name', 'N/A')}[/bold green]")
                    console.print(f"ID: {agent_data.get('agent_id', 'N/A')}")
                    console.print(f"URL: {agent_data.get('url', 'N/A')}")
                    console.print(f"Description: {agent_data.get('description', 'N/A')}")
                    console.print(f"Healthy: {'Yes' if agent_data.get('healthy', False) else 'No'}")
                    console.print(f"Registered: {agent_data.get('registered_at', 'N/A')}")
                    console.print(f"Last Heartbeat: {agent_data.get('last_heartbeat', 'N/A')}")
                    
                    skills = agent_data.get('skills', [])
                    if skills:
                        console.print(f"\n[bold]Skills ({len(skills)}):[/bold]")
                        for skill in skills:
                            console.print(f"  • {skill}")
                    
                    # Show full agent card if available
                    agent_card = agent_data.get('agent_card')
                    if agent_card:
                        console.print("\n[bold]Full Agent Card:[/bold]")
                        console.print(JSON.from_data(agent_card))
                    
                elif response.status_code == 404:
                    console.print(f"[red]Agent '{agent_id}' not found[/red]")
                else:
                    console.print(f"[red]Error fetching agent (HTTP {response.status_code})[/red]")
                    
        except httpx.ConnectError:
            console.print(f"[red]✗[/red] Cannot connect to registry at {url}")
        except Exception as e:
            console.print(f"[red]Error fetching agent: {e}[/red]")
    
    asyncio.run(show_agent())


@registry.command()
@click.argument("agent_id")
@click.option("--url", default="http://localhost:8888", help="Registry URL")
def heartbeat(agent_id: str, url: str):
    """Send heartbeat for an agent."""
    
    async def send_heartbeat():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{url}/agents/{agent_id}/heartbeat")
                
                if response.status_code == 200:
                    result = response.json()
                    console.print(f"[green]✓[/green] Heartbeat sent for agent '{agent_id}'")
                elif response.status_code == 404:
                    console.print(f"[red]Agent '{agent_id}' not found[/red]")
                else:
                    console.print(f"[red]Error sending heartbeat (HTTP {response.status_code})[/red]")
                    
        except httpx.ConnectError:
            console.print(f"[red]✗[/red] Cannot connect to registry at {url}")
        except Exception as e:
            console.print(f"[red]Error sending heartbeat: {e}[/red]")
    
    asyncio.run(send_heartbeat())


@registry.command()
@click.argument("agent_id")
@click.option("--url", default="http://localhost:8888", help="Registry URL")
def unregister(agent_id: str, url: str):
    """Unregister an agent from the registry."""
    
    async def unregister_agent():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{url}/agents/{agent_id}")
                
                if response.status_code == 200:
                    console.print(f"[green]✓[/green] Agent '{agent_id}' unregistered successfully")
                elif response.status_code == 404:
                    console.print(f"[red]Agent '{agent_id}' not found[/red]")
                else:
                    console.print(f"[red]Error unregistering agent (HTTP {response.status_code})[/red]")
                    
        except httpx.ConnectError:
            console.print(f"[red]✗[/red] Cannot connect to registry at {url}")
        except Exception as e:
            console.print(f"[red]Error unregistering agent: {e}[/red]")
    
    asyncio.run(unregister_agent())


if __name__ == "__main__":
    registry()
