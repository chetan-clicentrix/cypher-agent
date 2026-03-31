"""
Verification script for ResearchAgent
"""
import asyncio
import os
from src.core.engine import CypherEngine

async def test_research():
    print("🚀 Initializing CypherEngine...")
    engine = CypherEngine()
    
    print("\n🔍 Testing ResearchAgent capability detection...")
    queries = [
        "What is the price of Bitcoin today?",
        "search for current news about NVIDIA",
        "Who won the game last night?",
        "What is the latest project you read in my files?"
    ]
    
    for q in queries:
        agent, score = engine.agent_router.route(q)
        print(f"Query: '{q}' → Agent: {agent.name}, Score: {score:.2f}")

    print("\n✅ Verification complete!")

if __name__ == "__main__":
    asyncio.run(test_research())
