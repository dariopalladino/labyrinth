# Labyrinth 🧩

**High-level Python API wrapper for Google's A2A SDK**

Labyrinth simplifies agent-to-agent communication by providing an intuitive, high-level interface around Google's A2A (Agent-to-Agent) SDK. Build powerful AI agents that can seamlessly communicate with each other without getting lost in the complexity of low-level protocol details.

## ✨ Features

- **🚀 Simple Agent Setup**: Create agents with just a few lines of code
- **💬 Easy Communication**: Send messages and handle responses effortlessly  
- **🔧 Smart Configuration**: Automatic configuration management with sensible defaults
- **🛡️ Robust Error Handling**: Built-in error handling and retry mechanisms
- **📋 Task Management**: Simplified task creation, tracking, and cancellation
- **🔍 Agent Discovery**: Built-in service discovery with registry support
- **🏪 Agent Registry**: Centralized registry for agent registration and discovery
- **💓 Health Monitoring**: Automatic health checks and agent lifecycle management
- **🎯 Skill-based Discovery**: Find agents by their specific capabilities
- **🔐 Authentication & Authorization**: OAuth 2.0 with Azure Entra ID and scope-based access control
- **🔒 Production Security**: HTTPS enforcement, managed identity support, and token management
- **🖥️ CLI Tools**: Command-line interface for registry and agent management
- **📊 Built-in Logging**: Structured logging for debugging and monitoring
- **⚡ Async Support**: Full async/await support for high-performance applications

## 📦 Installation

```bash
pip install labyrinth
```

## 🚀 Quick Start

### Creating an Agent

```python
from labyrinth import Agent

# Create an agent with minimal configuration
agent = Agent(
    name="my-assistant", 
    description="A helpful AI assistant"
)

# Define agent capabilities
@agent.skill("answer_questions")
async def answer_questions(question: str) -> str:
    return f"The answer to '{question}' is..."

# Start the agent
await agent.start()
```

### Sending Messages

```python
from labyrinth import AgentClient

# Create a client to communicate with other agents
client = AgentClient()

# Send a message to another agent
response = await client.send_message(
    to_agent="other-agent-id",
    message="Hello, how can you help me?",
    skill="answer_questions"
)

print(response.content)
```

### Task Management

```python
# Create and track long-running tasks
task = await client.create_task(
    agent_id="worker-agent",
    skill="process_data",
    parameters={"dataset": "large_data.csv"}
)

# Monitor task progress
status = await client.get_task_status(task.id)
print(f"Task status: {status.state}")

# Get results when complete
if status.is_complete:
    result = await client.get_task_result(task.id)
    print(f"Task result: {result}")
```

### Agent Registry & Service Discovery

```python
# Start a registry server
from labyrinth.server import RegistryServer, AgentRegistry

registry = AgentRegistry()
server = RegistryServer(registry, host="localhost", port=8888)
await server.start()
```

```python
# Register an agent with the registry
import aiohttp

agent = Agent(name="translator", description="Translation service")
agent.add_skill("translate", translate_text, "Translate text between languages")

# Register with central registry
registration_data = {
    "agent_card": agent.get_agent_card().model_dump(),
    "base_url": f"http://{agent.host}:{agent.port}"
}

async with aiohttp.ClientSession() as session:
    await session.post(
        "http://localhost:8888/agents/translator/register",
        json=registration_data
    )
```

```python
# Discover agents by capabilities
from labyrinth.client.discovery import AgentDiscoveryService

discovery = AgentDiscoveryService()
discovery.add_registry("http://localhost:8888")

# Find agents with specific skills
agents = await discovery.list_available_agents()
translators = [a for a in agents if "translate" in a["skills"]]

# Discover specific agent by ID
agent_card = await discovery.discover_agent("translator")
print(f"Found translator: {agent_card.name}")
```

### Authentication & Security

```python
# Authenticated registry with Azure Entra ID
from labyrinth.server.authenticated_registry import AuthenticatedRegistryServer
from labyrinth.auth import load_auth_config, create_auth_components

# Load authentication configuration
config = load_auth_config()
auth_provider, token_validator = create_auth_components(config)

# Create authenticated registry
registry = AgentRegistry()
server = AuthenticatedRegistryServer(
    registry=registry,
    token_validator=token_validator,
    host="localhost",
    port=8888,
    require_https=config.require_https,
    default_scope=config.required_scope,
)

await server.start()
```

```python
# Authenticated client with automatic token management
from labyrinth.client.authenticated_client import AuthenticatedClientManager

# Create authenticated client manager
client_manager = AuthenticatedClientManager()

# Client credentials flow
client = await client_manager.create_client_credentials_client(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id",
    scopes=["agentic_ai_solution"]
)

# Managed identity flow (Azure deployments)
client = await client_manager.create_managed_identity_client(
    scopes=["agentic_ai_solution"]
)

# Use authenticated client for secure operations
agents = await client.list_agents("https://registry.example.com")
result = await client.register_with_registry(
    registry_url="https://registry.example.com",
    agent_card=agent_card,
    base_url="https://myagent.example.com"
)
```

### CLI User Authentication

```bash
# Set up CLI authentication
export LABYRINTH_CLI_CLIENT_ID="your-public-client-id"
export LABYRINTH_CLI_TENANT_ID="your-tenant-id" 
export LABYRINTH_CLI_SCOPES="agentic_ai_solution"

# Interactive login using OAuth 2.0 Device Code Flow
labyrinth auth login
# Opens browser for authentication, secure for CLI tools

# Check authentication status
labyrinth auth status

# Get token for use in scripts
TOKEN=$(labyrinth auth token)
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/

# Logout
labyrinth auth logout
```

```python
# Use CLI authentication in Python scripts
from labyrinth.auth.interactive import authenticate_cli

# Quick authentication
access_token = await authenticate_cli(
    client_id="your-public-client-id",
    tenant_id="your-tenant-id",
    scopes=["agentic_ai_solution"]
)

# Token is automatically cached and reused
```

## 🖥️ CLI Tools

Labyrinth includes powerful command-line tools for managing agents and registries:

### Registry Management

```bash
# Start a registry server
labyrinth-registry start --host 0.0.0.0 --port 8888

# Check registry status and statistics
labyrinth-registry status

# List all registered agents
labyrinth-registry list

# Show detailed information about an agent
labyrinth-registry show translator

# List agents with specific skills
labyrinth-registry list --skill translate

# Send heartbeat for an agent
labyrinth-registry heartbeat translator

# Unregister an agent
labyrinth-registry unregister translator
```

### Registry API

The registry provides a REST API for integration:

```bash
# Health check
curl http://localhost:8888/health

# List agents
curl http://localhost:8888/agents

# Find agents by skill
curl "http://localhost:8888/agents?skill=translate"

# Get agent details
curl http://localhost:8888/agents/translator

# Register agent details
curl -X POST http://localhost:8888/agents/translator/register \
  -H "Content-Type: application/json" \
  -d '{"registration_data": {"agent_card": {...}, "base_url": "http://localhost:8081"}}'
  
# Registry statistics
curl http://localhost:8888/stats
```

## 📚 Documentation

- [User Guide](https://github.com/dariopalladino/labyrinth/README.md) - This guide
- [Agent Registry Guide](docs/REGISTRY.md) - Comprehensive registry system documentation
- [Authentication Guide](docs/README_authentication.md) - Complete authentication setup and examples
- [Azure Setup Guide](docs/azure_setup_guide.md) - Step-by-step Azure deployment guide
- [API Reference](https://github.com/dariopalladino/labyrinth/PROJECT_OVERVIEW.md)
- [Examples](examples/) - Working code examples including registry usage and authentication

## 🏗️ Architecture

Labyrinth provides a comprehensive suite of components for building distributed agent systems:

### Core Components

1. **Agent**: High-level agent creation and management with skill registration
2. **AgentClient**: Simplified client for agent communication and task management
3. **AgentRegistry**: Centralized service discovery and health monitoring
4. **AgentDiscoveryService**: Client-side service discovery with caching
5. **CLI Tools**: Command-line management for registries and agents

### Service Discovery Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Agent A   │◄──►│ Agent Registry   │◄──►│   Agent B   │
│             │    │                  │    │             │
│ - register  │    │ - discovery      │    │ - discover  │
│ - heartbeat │    │ - health checks  │    │ - connect   │
│ - skills    │    │ - statistics     │    │ - skills    │
└─────────────┘    └──────────────────┘    └─────────────┘
        ▲                     ▲                     ▲
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────────────┐
                    │  CLI Manager    │
                    │                 │
                    │ - list agents   │
                    │ - health check  │
                    │ - start/stop    │
                    └─────────────────┘
```

### Key Features

- **Automatic Service Discovery**: Agents automatically discover each other through registries
- **Health Monitoring**: Built-in health checks with automatic stale agent cleanup
- **Skill-based Routing**: Route messages to agents based on their capabilities
- **Horizontal Scaling**: Support for multiple registry instances and load balancing
- **Developer Experience**: Rich CLI tools and comprehensive APIs

Each component abstracts away the complexity of the underlying A2A SDK while providing full access to advanced features when needed.

## 🎯 Use Cases

Labyrinth is perfect for building:

- **🤖 AI Agent Networks**: Coordinate multiple AI agents for complex workflows
- **🐥 Microservice Communication**: Enable services to discover and communicate with each other
- **🏪 Service Meshes**: Build distributed systems with automatic service discovery
- **🔄 Workflow Orchestration**: Chain multiple agents to accomplish complex tasks
- **📋 Task Processing**: Distribute work across multiple specialized agents
- **🔍 Agent Marketplaces**: Create directories of available agent capabilities
- **📡 IoT Device Networks**: Enable devices to discover and coordinate with each other
- **🏮 Multi-tenant Systems**: Isolate and manage agents across different organizations

## 🚀 Advanced Features

### Health Monitoring & Auto-Recovery

- Automatic health checks with configurable intervals
- Graceful handling of failed agents
- Automatic cleanup of stale registrations
- Health status tracking and reporting

### Skill-based Discovery

- Query agents by their specific capabilities
- Filter agents based on skill combinations
- Dynamic skill registration and updates
- Semantic skill matching (planned)

### Authentication & Security

- OAuth 2.0 and OpenID Connect standard compliance
- Azure Entra ID integration with client credentials and managed identity
- Automatic token acquisition, refresh, and management
- Scope-based authorization with fine-grained access control
- HTTPS enforcement for production deployments
- JWT token validation with signature verification
- Configurable authentication providers (pluggable architecture)
- Development mode with scope-only validation for testing

### Production Ready

- Horizontal scaling with multiple registry instances
- Load balancing support for high availability
- Comprehensive error handling and retry logic
- Structured logging for observability
- CLI tools for operations and debugging
- Enterprise-grade security with Azure integration
- Multi-environment configuration support

### Developer Experience

- Intuitive Python APIs with type hints
- Rich CLI with colored output and tables
- Comprehensive documentation and examples
- Hot-reloading for development (planned)
- Built-in testing utilities (planned)

## 📝 Examples

### Basic Agent with Skills

```python
from labyrinth.server import Agent

# Create an agent
agent = Agent(
    name="math-helper",
    description="Mathematical computation assistant",
    host="localhost",
    port=8080
)

# Add skills using decorators
@agent.skill("add")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

@agent.skill("multiply")
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

# Start the agent
async def main():
    await agent.start()
    print(f"Agent {agent.name} is running on {agent.host}:{agent.port}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Multi-Agent System with Registry

```python
import asyncio
from labyrinth.server import Agent, RegistryServer, AgentRegistry
from labyrinth.client.discovery import AgentDiscoveryService

async def create_registry():
    """Create and start a registry server."""
    registry = AgentRegistry(heartbeat_interval=30, stale_threshold=120)
    server = RegistryServer(registry, host="localhost", port=8888)
    
    # Start in background
    registry_task = asyncio.create_task(server.start())
    await asyncio.sleep(1)  # Give time to start
    return registry_task

async def create_translator_agent():
    """Create a translation agent."""
    agent = Agent(name="translator", host="localhost", port=8081)
    
    @agent.skill("translate")
    async def translate_text(text: str, target_lang: str) -> str:
        # Simulated translation
        return f"[{target_lang.upper()}] {text}"
    
    await agent.start()
    return agent

async def create_summarizer_agent():
    """Create a text summarization agent."""
    agent = Agent(name="summarizer", host="localhost", port=8082)
    
    @agent.skill("summarize")
    async def summarize_text(text: str, max_length: int = 100) -> str:
        # Simulated summarization
        return text[:max_length] + "..." if len(text) > max_length else text
    
    await agent.start()
    return agent

async def register_agents_with_registry(agents):
    """Register all agents with the central registry."""
    import aiohttp
    
    for agent in agents:
        registration_data = {
            "agent_card": agent.get_agent_card().model_dump(),
            "base_url": f"http://{agent.host}:{agent.port}"
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"http://localhost:8888/agents/{agent.name}/register",
                json=registration_data
            )
        print(f"✅ Registered {agent.name} with registry")

async def discover_and_use_agents():
    """Discover agents and use their capabilities."""
    discovery = AgentDiscoveryService()
    discovery.add_registry("http://localhost:8888")
    
    # List all available agents
    agents = await discovery.list_available_agents()
    print("\n🔍 Available agents:")
    for agent in agents:
        print(f"  - {agent['name']}: {', '.join(agent['skills'])}")
    
    # Find agents with specific skills
    translators = [a for a in agents if "translate" in a["skills"]]
    if translators:
        print(f"\n🌐 Found translator: {translators[0]['name']}")

async def main():
    """Run the complete multi-agent example."""
    print("🚀 Starting multi-agent system with registry...")
    
    # Start registry
    registry_task = await create_registry()
    print("✅ Registry server started")
    
    # Create agents
    translator = await create_translator_agent()
    summarizer = await create_summarizer_agent()
    agents = [translator, summarizer]
    print("✅ Agents created and started")
    
    # Register agents
    await register_agents_with_registry(agents)
    
    # Discover and use agents
    await discover_and_use_agents()
    
    print("\n🎉 Multi-agent system is running!")
    print("🔧 Use the CLI to manage: labyrinth-registry status")
    
    # Keep running
    try:
        await asyncio.sleep(60)  # Run for 1 minute
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        registry_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

### CLI Management Example

```bash
# Terminal 1: Start the registry
labyrinth-registry start

# Terminal 2: Check status and manage agents
labyrinth-registry status
labyrinth-registry list
labyrinth-registry show translator
labyrinth-registry list --skill translate
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on top of Google's [A2A SDK](https://www.a2aprotocol.net/)
- Inspired by the need to simplify agent-to-agent communication
- Thanks to all contributors and the open-source community

---

**Ready to build amazing AI agents?** Get started with Labyrinth today! 🎯
