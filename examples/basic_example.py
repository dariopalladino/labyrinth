#!/usr/bin/env python3
"""
Basic example of using Labyrinth for agent-to-agent communication.

This example demonstrates:
1. Creating an agent with skills
2. Starting the agent 
3. Using a client to communicate with agents
"""

import asyncio
from labyrinth import Agent, AgentClient, Message


async def main():
    # Create an agent
    agent = Agent(
        name="helpful-assistant",
        description="A helpful AI assistant that can answer questions and perform tasks"
    )
    
    # Define agent skills using decorators
    @agent.skill("greet")
    async def greet_user(name: str) -> str:
        """Greet a user by name."""
        return f"Hello, {name}! How can I help you today?"
    
    @agent.skill("add_numbers") 
    async def add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b
    
    @agent.skill("process_text")
    async def process_text(text: str, operation: str = "upper") -> str:
        """Process text with various operations."""
        if operation == "upper":
            return text.upper()
        elif operation == "lower":
            return text.lower()
        elif operation == "reverse":
            return text[::-1]
        else:
            return f"Unknown operation: {operation}"
    
    # You can also add skills programmatically
    def calculate_square(number: float) -> float:
        """Calculate the square of a number."""
        return number ** 2
    
    agent.add_skill("square", calculate_square, "Calculate the square of a number")
    
    print(f"Agent '{agent.name}' created with skills: {list(agent.get_skills().keys())}")
    print(f"Agent capabilities: {agent.get_capabilities()}")
    
    # Demonstrate that the agent can now start successfully!
    # The key fix was properly instantiating DefaultRequestHandler with required dependencies
    print("\nStarting agent to demonstrate the fix...")
    async with agent:
        # Agent is now running and can receive requests
        print(f"✅ Agent is running: {agent.is_running}")
        print("✅ Agent started successfully with properly configured A2A components!")
        
        # The DefaultRequestHandler instantiation fix is now working!
        print(f"✅ DefaultRequestHandler properly created with:")
        print(f"   - AgentExecutor: {type(agent._agent_executor).__name__}")
        print(f"   - TaskStore: {type(agent._task_store).__name__}")
        print(f"   - QueueManager: {type(agent._queue_manager).__name__}")
        
        # Note: Full client-to-agent communication would require additional
        # A2A SDK integration for agent discovery and card fetching
        print("\n📝 Note: AgentClient communication requires additional A2A setup")        
    


if __name__ == "__main__":
    asyncio.run(main())
