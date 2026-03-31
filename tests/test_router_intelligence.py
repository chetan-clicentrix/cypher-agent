import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine import CypherEngine

async def run_tests():
    print("🚀 Initializing CypherEngine for Router Tests...")
    engine = CypherEngine()
    router = engine.agent_router
    
    # Test cases: (Query, Expected Agent)
    tests = [
        # Explicit/Heuristic matches
        ("list files", "System Agent"),
        ("What is the price of Bitcoin?", "Research Agent"),
        
        # Ambiguous/Conversational (require LLM)
        ("how you know the price you execute the tool ??", "General Agent"),
        ("can you execute a scan of my network?", "System Agent"),
        ("I need to remember that my favorite color is blue", "Memory Agent"),
        ("Read the README.md file in this project", "Knowledge Agent"),
        ("Change your voice to a female voice", "Voice Agent")
    ]
    
    print("\n🔍 Testing LLM Router Intelligence...\n")
    
    passed = 0
    for query, expected in tests:
        print(f"Query: '{query}'")
        agent, score = await router.route(query)
        agent_name = agent.name if agent else "None"
        
        if agent_name == expected:
            print(f"✅ PASSED (Routed to {agent_name})\n")
            passed += 1
        else:
            print(f"❌ FAILED (Expected: {expected}, Got: {agent_name})\n")
            
    print(f"🎯 Results: {passed}/{len(tests)} passed.")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(run_tests())
