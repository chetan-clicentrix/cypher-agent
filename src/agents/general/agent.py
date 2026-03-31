"""
General Agent
Fallback agent for general queries, Q&A, and conversation
"""

from typing import List, Optional, Dict, Any
import asyncio
from ..base_agent import BaseAgent
from ...utils.memory import get_memory
from ...core.settings import settings


class GeneralAgent(BaseAgent):
    """
    General-purpose agent for queries that don't match specialized agents
    
    Handles:
    - General conversation
    - Q&A
    - Explanations
    - Anything not covered by specialized agents
    """
    
    def __init__(self, llm_orchestrator, llm_router=None):
        super().__init__(
            "General Agent",
            "Fallback conversational agent. Handles general chat, answering subjective questions, writing code, solving math problems, and executing conversational requests that do not fit specialized domains.",
            llm_orchestrator
        )
        self.llm_router = llm_router
        self.memory = get_memory()
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Always returns low confidence (0.2) as this is the fallback agent
        Other agents should take priority
        """
        return 0.2
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process general queries using LLM with intelligent routing and memory
        """
        # Add user query to conversation history
        self.memory.add_to_conversation("User", query)
        
        # Use LLM Router to decide complexity score
        if self.llm_router:
            llm_type, score, reasoning = self.llm_router.route(query)
            self.logger.info(f"🎯 LLM Routing: {reasoning}")
            # Use 3-tier selection based on complexity score
            llm, tier = self.llm_orchestrator.get_best_for_complexity(score)
            self.logger.info(f"💡 Selected tier: {tier.upper()} LLM")
            timeout = settings.local_timeout if tier == "local" else settings.cloud_timeout
        else:
            # Fallback to config.yaml mapped setting
            model_name = settings.get_agent_llm(self.name)
            llm = self.llm_orchestrator.get_model_by_name(model_name)
            tier = model_name
            timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        
        if not llm:
            return "⚠️ No LLM available. Please configure API keys in config.yaml or .env file."

        
        try:
            # Build prompt with soul + conversation history + strict rules
            soul = self.memory.get_soul_context()
            conv = self.memory.get_conversation_context(max_messages=6)  # Last 6 exchanges
            user_profile = self.memory.get_user_context()
            
            # Build layered context
            parts = []
            if soul:
                parts.append(soul)
            if user_profile:
                parts.append("## User Profile\n" + user_profile)
            if conv:
                parts.append(conv)  # Most recent conversation last = better context
            
            full_context = "\n\n".join(parts)
            
            prompt = f"""{full_context}

---
STRICT RULES (never break these):
- NEVER mention LLM names (Ollama, Gemini, NVIDIA, GPT, etc.)
- NEVER mention complexity scores or routing decisions
- Respond naturally and conversationally
- Use conversation history above to understand follow-up questions
- Be concise and direct

User: {query}
Cipher:"""
            
            self.logger.info(f"💬 Processing with {tier.upper()} LLM")
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)
            final_response = response.content.strip()
            # Also add assistant response to memory
            self.memory.add_to_conversation("Cipher", final_response)
            return final_response
        except asyncio.TimeoutError:
            return f"⚠️ The {tier.upper()} AI timed out while thinking. Try asking again."
        except Exception as e:
            self.logger.error(f"❌ General Agent error: {e}")
            return f"I ran into an issue processing that query: {str(e)}"
    
    def get_tools(self) -> List:
        """General agent doesn't use specific tools"""
        return []
