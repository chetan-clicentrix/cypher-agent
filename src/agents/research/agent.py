"""
Research Agent
Specialized agent for web searching and real-time information retrieval
"""

import asyncio
import copy
from typing import List, Optional, Dict, Any
from ..base_agent import BaseAgent
from ...tools.web_search import search_web, search_tavily
from ...core.settings import settings

class ResearchAgent(BaseAgent):
    """
    Agent that can perform web searches to answer questions about 
    real-time events, news, and facts.
    """
    
    def __init__(self, llm_orchestrator):
        super().__init__(
            "Research Agent",
            "Connected to the internet. Uses DuckDuckGo to search the live web for real-time information, current events, latest news, and live asset prices (e.g., Bitcoin) not in the training data.",
            llm_orchestrator
        )
        
        # Keywords that indicate research/search-related queries
        self.search_keywords = [
            'search', 'google', 'find on web', 'look up', 'online',
            'news', 'current', 'latest', 'price', 'weather',
            'stock', 'who is', 'what happened', 'today', 'how much',
            'what is the', 'value of', 'bitcoin', 'crypto', 'btc', 'eth'
        ]
        
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Detect search-related queries
        """
        query_lower = query.lower()
        
        # Check for keywords
        matches = sum(1 for kw in self.search_keywords if kw in query_lower)
        confidence = min(matches * 0.25, 0.9)
        
        # Specific search intents
        # Strong signals - made them more specific to avoid false positives
        strong_signals = [
            'search for', 'on the web', 'look up', 
            'current price of', 'latest news', 'price of',
            'how much is', 'what is the value'
        ]
        if any(s in query_lower for s in strong_signals):
            confidence = max(confidence, 0.85)
            
        return confidence
        
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process the query by searching and summarizing
        """
        self.logger.info(f"🔍 Researching: {query}")
        
        # 1. Decide if we need broad search or news
        is_news = any(kw in query.lower() for kw in ['news', 'latest', 'today', 'happened'])
        
        # Step 1: Improve search query via LLM
        refined_query = await self._get_better_search_query(query)
        self.logger.info(f"🔍 Refined Search Query: '{refined_query}'")
        
        # Step 2: Route search to the preferred provider (Tavily or DuckDuckGo)
        if settings.use_tavily_search:
            self.logger.info(f"🌐 [TAVILY SEARCH]: Executing advanced AI search...")
            search_results = search_tavily(refined_query, max_results=3)
        else:
            self.logger.info(f"🦆 [DUCKDUCKGO SEARCH]: Executing free basic search...")
            search_results = search_web(refined_query, max_results=3)
            
        if not search_results:
            return f"I couldn't find any information on '{refined_query}'."
            
        # 4. Synthesize answer with LLM
        return await self._synthesize_search_results(query, search_results)

    async def _get_better_search_query(self, query: str) -> str:
        """
        Ask LLM to turn a natural question into a clean search query
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        
        prompt = f"""Turn this user request into a simple, efficient web search query.
User: "{query}"
Search Query:"""
        
        try:
            resp = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)
            return resp.content.strip().strip('"')
        except:
            return query # Fallback to original

    async def _synthesize_search_results(self, original_query: str, results: List[Dict[str, Any]]) -> str:
        """
        Use LLM to explain search results naturally
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        
        # Format results for prompt (Use up to 10 results for better accuracy)
        results_text = ""
        for i, r in enumerate(results[:10], 1):
            results_text += f"{i}. {r.get('title', 'No Title')}\n"
            results_text += f"Snippet: {r.get('body', r.get('snippet', 'No snippet'))}\n"
            results_text += f"Source: {r.get('href', r.get('link', 'No link'))}\n\n"
            
        prompt = f"""You are Cipher, a highly accurate AI assistant.
The user asked: "{original_query}"

I found these real-time search results:
{results_text}

CRITICAL INSTRUCTIONS:
1. Provide the direct answer IMMEDIATELY in 1 or 2 short sentences.
2. DO NOT add extra context, analysis, paragraphs, or fluff unless the user explicitly requested "details" or "explain".
3. ONLY use information from the search results provided above.
4. If the user asks for a price/number, just give the number and the source (e.g., "The current price of TCS is ₹2,717.40 according to MSN.").
5. If the results do NOT contain the specific value, just say "I couldn't find the exact current value in the latest results."
6. NEVER HALLUCINATE OR INVENT NUMBERS. Accuracy is more important than being helpful.

Response:"""
        
        try:
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)
            return response.content.strip()
        except asyncio.TimeoutError:
            self.logger.error(f"Synthesis timed out after {timeout}s using {model_name}")
            return "I tried to summarize the info online, but the AI timed out. Try asking again!"
        except Exception as e:
            self.logger.error(f"Synthesis error: {e}")
            return "I found some info online but had trouble summarizing it. Try asking again!"

    def get_tools(self) -> List:
        return [] # Internal tools
