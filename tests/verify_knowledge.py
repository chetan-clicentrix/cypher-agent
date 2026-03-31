"""
Verification script for KnowledgeAgent
"""
import asyncio
import os
from src.core.engine import CypherEngine

async def test_knowledge():
    print("🚀 Initializing CypherEngine...")
    engine = CypherEngine()
    
    print("\n🔍 Testing KnowledgeAgent capability detection...")
    queries = [
        "list files in this folder",
        "summarize SOUL.md",
        "search for 'Gemini' in my files",
        "what is in requirements.txt"
    ]
    
    for q in queries:
        agent, score = engine.agent_router.route(q)
        print(f"Query: '{q}' → Agent: {agent.name}, Score: {score:.2f}")

    print("\n✅ Verification complete!")

if __name__ == "__main__":
    asyncio.run(test_knowledge())
