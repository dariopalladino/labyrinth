#!/usr/bin/env python3
"""
Advanced example with multiple agents communicating with each other.

This example demonstrates:
1. Creating multiple specialized agents
2. Inter-agent communication
3. Complex task coordination
"""

import asyncio
from typing import List, Dict, Any
from labyrinth import Agent, AgentClient, Message, Config


# Create specialized agents

def create_calculator_agent() -> Agent:
    """Create a calculator agent with mathematical capabilities."""
    agent = Agent(
        name="calculator",
        description="Mathematical calculation agent",
        port=8081
    )
    
    @agent.skill("add")
    async def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    @agent.skill("multiply")
    async def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    @agent.skill("factorial")
    async def factorial(n: int) -> int:
        """Calculate factorial of a number."""
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
    
    return agent


def create_data_processor_agent() -> Agent:
    """Create a data processing agent."""
    agent = Agent(
        name="data-processor",
        description="Data processing and analysis agent",
        port=8082
    )
    
    @agent.skill("analyze_list")
    async def analyze_list(numbers: List[float]) -> Dict[str, Any]:
        """Analyze a list of numbers."""
        if not numbers:
            return {"error": "Empty list provided"}
        
        return {
            "count": len(numbers),
            "sum": sum(numbers),
            "average": sum(numbers) / len(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "sorted": sorted(numbers)
        }
    
    @agent.skill("filter_data")
    async def filter_data(data: List[Dict[str, Any]], field: str, min_value: float) -> List[Dict[str, Any]]:
        """Filter data based on field value."""
        return [item for item in data if item.get(field, 0) >= min_value]
    
    return agent


def create_orchestrator_agent() -> Agent:
    """Create an orchestrator agent that coordinates other agents."""
    agent = Agent(
        name="orchestrator", 
        description="Agent coordination and workflow management",
        port=8083
    )
    
    @agent.skill("complex_calculation")
    async def complex_calculation(numbers: List[float]) -> Dict[str, Any]:
        """Perform complex calculation using multiple agents."""
        # This would coordinate with other agents in a real scenario
        client = AgentClient()
        
        # Step 1: Analyze the data
        analysis_task = await client.create_task(
            agent_id="data-processor",
            skill="analyze_list",
            parameters={"numbers": numbers}
        )
        
        # Step 2: Calculate factorial of count (if reasonable)
        count = len(numbers)
        if count <= 10:  # Reasonable limit for factorial
            factorial_task = await client.create_task(
                agent_id="calculator",
                skill="factorial", 
                parameters={"n": count}
            )
        
        # Combine results (simplified for example)
        return {
            "status": "completed",
            "input_count": count,
            "message": f"Would coordinate calculation of {count} numbers"
        }
    
    return agent


async def main():
    """Main function to demonstrate multi-agent coordination."""
    
    # Create agents
    calculator = create_calculator_agent()
    data_processor = create_data_processor_agent()
    orchestrator = create_orchestrator_agent()
    
    print("Created agents:")
    print(f"- {calculator.name}: {list(calculator.get_skills().keys())}")
    print(f"- {data_processor.name}: {list(data_processor.get_skills().keys())}")
    print(f"- {orchestrator.name}: {list(orchestrator.get_skills().keys())}")
    
    # In a real application, you would start all agents:
    # async with calculator, data_processor, orchestrator:
    #     print("\nAll agents started!")
    #     
    #     # Create client for coordination
    #     async with AgentClient() as client:
    #         # Test individual agents
    #         print("\nTesting calculator agent...")
    #         calc_result = await client.send_message(
    #             to_agent="calculator",
    #             message='{"a": 5, "b": 3}',
    #             skill="add"
    #         )
    #         print(f"5 + 3 = {calc_result.content}")
    #         
    #         print("\nTesting data processor agent...")
    #         data_result = await client.send_message(
    #             to_agent="data-processor", 
    #             message='{"numbers": [1, 2, 3, 4, 5]}',
    #             skill="analyze_list"
    #         )
    #         print(f"Analysis result: {data_result.content}")
    #         
    #         print("\nTesting orchestrator agent...")
    #         orchestrator_result = await client.send_message(
    #             to_agent="orchestrator",
    #             message='{"numbers": [10, 20, 30, 40, 50]}',
    #             skill="complex_calculation"
    #         )
    #         print(f"Orchestration result: {orchestrator_result.content}")
    
    print("\nMulti-agent example completed!")
    print("In a real application, uncomment the agent startup code above.")


if __name__ == "__main__":
    asyncio.run(main())
