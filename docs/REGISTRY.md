# Labyrinth Agent Registry

The Labyrinth Agent Registry is a service discovery system that enables agents to register their capabilities and discover other agents in a distributed A2A (Agent-to-Agent) network.

## Features

- **Agent Registration**: Agents can register with the registry, publishing their capabilities and endpoint information
- **Service Discovery**: Clients can discover available agents by ID, skill, or query the entire registry
- **Health Monitoring**: Automatic health checks with configurable heartbeat intervals and stale agent cleanup  
- **Skill-based Filtering**: Find agents that have specific skills or capabilities
- **RESTful API**: HTTP-based API for easy integration and testing
- **CLI Management**: Command-line interface for registry operations
- **Statistics & Monitoring**: Real-time stats on registered agents, skills, and system health

## Architecture

The registry system consists of several key components:

### Core Components

1. **AgentRegistry**: In-memory registry that maintains agent registrations
2. **RegistryServer**: FastAPI-based HTTP server exposing the registry API  
3. **AgentDiscoveryService**: Client-side service for discovering agents
4. **CLI Tools**: Command-line interface for registry management

### Data Model

- **AgentRegistration**: Represents a registered agent with metadata
- **AgentCard**: A2A standard agent card describing capabilities
- **Health Status**: Tracking for agent availability and responsiveness

## Quick Start

### Starting a Registry Server

```bash
# Start with default settings (localhost:8888)
labyrinth-registry start

# Start with custom settings
labyrinth-registry start --host 0.0.0.0 --port 9000 --heartbeat-interval 30
```

### Using the Registry in Code

```python
import asyncio
from labyrinth.server import Agent, RegistryServer, AgentRegistry

# Create and start a registry
async def start_registry():
    registry = AgentRegistry()
    server = RegistryServer(registry, host="localhost", port=8888)
    await server.start()  # This will block until stopped

# Create an agent and register it
async def register_agent():
    # Create an agent
    agent = Agent(
        name="My Agent", 
        description="A helpful agent",
        host="localhost",
        port=8080
    )
    
    # Add skills
    @agent.skill("greet")
    async def greet(name: str) -> str:
        return f"Hello, {name}!"
    
    # Register with registry
    import aiohttp
    registration_data = {
        "agent_card": agent.get_agent_card().model_dump(),
        "base_url": f"http://{agent.host}:{agent.port}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8888/agents/My Agent/register",
            json=registration_data
        ) as response:
            result = await response.json()
            print(f"Registration result: {result}")
```

## Registry API

### Endpoints

#### Agent Management

- `POST /agents/{agent_id}/register` - Register an agent
- `DELETE /agents/{agent_id}` - Unregister an agent  
- `GET /agents/{agent_id}` - Get agent details
- `POST /agents/{agent_id}/heartbeat` - Send agent heartbeat

#### Discovery

- `GET /agents` - List all agents (with optional filters)
  - Query params: `skill=<skill_name>`, `healthy_only=true/false`
- `GET /stats` - Get registry statistics

#### Health & Status

- `GET /health` - Registry health check
- `GET /` - Basic service info

### Example API Usage

```bash
# Check registry status
curl http://localhost:8888/health

# List all agents
curl http://localhost:8888/agents

# Find agents with specific skill
curl "http://localhost:8888/agents?skill=translate"

# Get agent details
curl http://localhost:8888/agents/my-agent

# Send heartbeat
curl -X POST http://localhost:8888/agents/my-agent/heartbeat
```

## CLI Usage

The `labyrinth-registry` command provides a full-featured CLI:

### Registry Management

```bash
# Start registry server
labyrinth-registry start --host 0.0.0.0 --port 8888

# Check registry status
labyrinth-registry status

# List registered agents
labyrinth-registry list

# Show detailed agent info
labyrinth-registry show <agent_id>

# Send heartbeat for agent
labyrinth-registry heartbeat <agent_id>

# Unregister an agent
labyrinth-registry unregister <agent_id>
```

### Filtering and Queries

```bash
# List agents with specific skill
labyrinth-registry list --skill translate

# Include unhealthy agents
labyrinth-registry list --unhealthy
```

## Client Discovery

The discovery service provides programmatic access to find and connect to agents:

```python
from labyrinth.client.discovery import AgentDiscoveryService

# Create discovery service
discovery = AgentDiscoveryService()

# Add registries to search
discovery.add_registry("http://localhost:8888")
discovery.set_default_registry()  # Adds localhost:8888 as default

# Add known agents
discovery.add_known_agent("special-agent", "http://192.168.1.100:8080")

# Discover an agent by ID
agent_card = await discovery.discover_agent("translator-bot")
print(f"Found agent: {agent_card.name}")

# List all available agents
agents = await discovery.list_available_agents()
for agent in agents:
    print(f"- {agent['name']}: {agent['skills']}")

# Health check an agent
health = await discovery.health_check_agent("http://agent:8080")
if health["healthy"]:
    print(f"Agent is healthy (response time: {health['response_time_ms']}ms)")
```

## Configuration

### Registry Settings

```python
from labyrinth.server.registry import AgentRegistry

registry = AgentRegistry(
    heartbeat_interval=60,    # Heartbeat check interval (seconds)
    stale_threshold=300,      # Mark agent stale after this time
)
```

### Discovery Settings

```python
from labyrinth.client.discovery import AgentDiscoveryService

discovery = AgentDiscoveryService(
    cache_ttl=300,         # Cache agent cards for 5 minutes
    http_timeout=10,       # HTTP request timeout
)
```

## Health Monitoring

The registry automatically monitors agent health:

- **Heartbeats**: Agents should send periodic heartbeats to stay marked as healthy
- **Stale Detection**: Agents that haven't sent heartbeats become stale, then are removed
- **Health API**: Get real-time stats on agent health and availability

### Health States

1. **Healthy**: Agent has sent recent heartbeat
2. **Stale**: Agent hasn't sent heartbeat within threshold
3. **Removed**: Agent removed after extended stale period

## Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8888
CMD ["labyrinth-registry", "start", "--host", "0.0.0.0", "--port", "8888"]
```

### Environment Variables

```bash
export LABYRINTH_REGISTRY_HOST=0.0.0.0
export LABYRINTH_REGISTRY_PORT=8888
export LABYRINTH_HEARTBEAT_INTERVAL=60
export LABYRINTH_STALE_THRESHOLD=300
```

### Load Balancing

For high availability, run multiple registry instances behind a load balancer:

```yaml
# docker-compose.yml
version: '3.8'
services:
  registry1:
    build: .
    ports:
      - "8888:8888"
    environment:
      - LABYRINTH_REGISTRY_HOST=0.0.0.0
      
  registry2:
    build: .
    ports:
      - "8889:8888"
    environment:
      - LABYRINTH_REGISTRY_HOST=0.0.0.0
      
  nginx:
    image: nginx
    ports:
      - "80:80"
    depends_on:
      - registry1
      - registry2
```

## Best Practices

### Agent Registration

- Use descriptive agent names and IDs
- Register all available skills with clear descriptions
- Send heartbeats regularly (recommended: every 30-60 seconds)
- Handle registration failures gracefully

### Registry Management

- Monitor registry health and statistics
- Set appropriate heartbeat and stale thresholds for your network
- Use multiple registry instances for high availability
- Implement proper logging and monitoring

### Client Discovery

- Cache agent cards to reduce registry load
- Implement retry logic for discovery failures
- Use skill-based discovery to find appropriate agents
- Validate agent health before attempting connections

## Troubleshooting

### Common Issues

1. **Agent not appearing in registry**
   - Check registration request format
   - Verify agent card contains required fields
   - Ensure registry is accessible from agent

2. **Agents marked as stale**
   - Verify heartbeat mechanism is working
   - Check network connectivity
   - Adjust stale thresholds if needed

3. **Discovery failures**
   - Verify registry URLs are correct
   - Check network connectivity
   - Review discovery service logs

### Debug Commands

```bash
# Check registry health
labyrinth-registry status

# View all agents including unhealthy
labyrinth-registry list --unhealthy

# Get detailed agent information
labyrinth-registry show <agent_id>
```

## Examples

See the `examples/` directory for complete working examples:

- `registry_example.py` - Full registry workflow demonstration
- `multi_agent_registry.py` - Multiple agents with registry
- `discovery_client.py` - Client-side discovery examples

## Future Enhancements

Planned features for future versions:

- Persistent storage (Redis, PostgreSQL)
- Agent authentication and authorization
- WebSocket support for real-time updates
- Geographic/region-based discovery
- Service mesh integration
- Prometheus metrics export
