"""
Agent Router
Routes user queries to the appropriate specialized agent
"""

from typing import List, Optional, Tuple, Dict, Any
import asyncio
from .base_agent import BaseAgent
from ..utils.logger import setup_logger
from ..core.settings import settings

logger = setup_logger()


class AgentRouter:
    """
    Routes queries to appropriate agents based on intent classification
    
    Supports:
    - Multiple agent registration
    - Confidence-based routing
    - Fallback to general agent
    - Future: Parallel agent execution for complex queries
    """
    
    def __init__(self, agents: List[BaseAgent], fallback_agent: Optional[BaseAgent] = None, llm_orchestrator=None):
        """
        Initialize the agent router
        
        Args:
            agents: List of specialized agents to route to
            fallback_agent: Optional fallback agent (default: GeneralAgent)
            llm_orchestrator: Optional LLMOrchestrator for intelligent routing
        """
        self.agents = agents
        self.fallback_agent = fallback_agent
        self.llm_orchestrator = llm_orchestrator
        self.logger = setup_logger()
        
        # Log registered agents
        agent_names = [agent.name for agent in agents]
        self.logger.info(f"🔀 AgentRouter initialized with {len(agents)} agents: {', '.join(agent_names)}")
        
        if fallback_agent:
            self.logger.info(f"🔄 Fallback agent: {fallback_agent.name}")
    
    async def route(self, query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[BaseAgent, float]:
        """
        Route query to the best matching agent
        
        Args:
            query: User's query
            context: Optional context information
        
        Returns:
            Tuple of (selected_agent, confidence_score)
        """
        best_agent = None
        best_score = 0.0
        
        # Ask each agent how confident they are
        for agent in self.agents:
            try:
                score = agent.can_handle(query, context)
                self.logger.debug(f"📊 {agent.name}: {score:.2f} confidence")
                
                if score > best_score:
                    best_score = score
                    best_agent = agent
            except Exception as e:
                self.logger.error(f"❌ Error checking {agent.name}: {e}")
        
        # Fast-path: clear heuristic win
        if best_agent and best_score >= 0.85:
            self.logger.info(f"✅ Fast routing to {best_agent.name} (confidence: {best_score:.2f})")
            return best_agent, best_score
            
        # Slow-path: LLM Classification for complex or ambiguous intents
        if self.llm_orchestrator:
            llm_agent = await self.classify_with_llm(query)
            if llm_agent:
                self.logger.info(f"🧠 LLM routed to {llm_agent.name}")
                return llm_agent, 1.0

        # Heuristic fallback if LLM routing fails or isn't used
        if best_agent and best_score >= 0.5:
            self.logger.info(f"✅ Fallback routing to {best_agent.name} (confidence: {best_score:.2f})")
            return best_agent, best_score
        
        # Final fallback to general agent
        if self.fallback_agent:
            self.logger.info(f"🔄 Using fallback agent: {self.fallback_agent.name}")
            return self.fallback_agent, 0.5
        
        # No suitable agent found
        self.logger.warning("⚠️ No suitable agent found for query")
        return None, 0.0

    async def classify_with_llm(self, query: str) -> Optional[BaseAgent]:
        """
        Use an LLM to accurately determine the user's intent based on agent descriptions.
        """
        # Load the centrally configured router model
        router_model = settings.router_llm
        llm = self.llm_orchestrator.get_model_by_name(router_model)
        if not llm:
            return None
            
        agent_descriptions = ""
        for agent in self.agents:
            agent_descriptions += f"- **{agent.name}**: {agent.description}\n"
            
        if self.fallback_agent:
             agent_descriptions += f"- **{self.fallback_agent.name}**: {self.fallback_agent.description}\n"
            
        prompt = f"""You are a smart router for an AI assistant.
Your job is to read the user's query and decide which specialized agent should handle it.

Here are the available agents and their capabilities:
{agent_descriptions}

User Query: "{query}"

Analyze the query and respond with ONLY the exact name of the best agent to handle it. Do not include asterisks, quotes, or any other text.
If none of the specialized agents seem like a perfect fit, respond with "{self.fallback_agent.name if self.fallback_agent else 'General Agent'}".

Agent Name:"""

        try:
            # Add an explicit timeout to prevent hanging on unreliable Cloud endpoints
            timeout_sec = settings.local_timeout if router_model == "ollama" else settings.cloud_timeout
            
            # Use asyncio.wait_for to enforce the timeout
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout_sec)
            
            chosen_name = response.content.strip().replace("'", "").replace('"', '').replace('*', '')
            
            # Find the matching agent
            for agent in self.agents:
                if agent.name.lower() == chosen_name.lower():
                    return agent
            if self.fallback_agent and self.fallback_agent.name.lower() == chosen_name.lower():
                return self.fallback_agent
                
            self.logger.warning(f"LLM suggested unknown agent: {chosen_name}")
            return None
        except asyncio.TimeoutError:
            self.logger.error(f"LLM classification timed out after {timeout_sec}s using {router_model}")
            return None
        except Exception as e:
            self.logger.error(f"LLM classification failed: {e}")
            return None
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route and process a query
        
        Args:
            query: User's query
            context: Optional context
        
        Returns:
            Agent's response
        """
        agent, confidence = await self.route(query, context)
        
        if not agent:
            return "⚠️ I'm not sure how to handle that query. Please try rephrasing."
        
        try:
            response = await agent.process(query, context)
            return response
        except Exception as e:
            self.logger.error(f"❌ Error processing query with {agent.name}: {e}")
            return f"❌ Error: {str(e)}"
    
    def register_agent(self, agent: BaseAgent):
        """Add a new agent to the router"""
        self.agents.append(agent)
        self.logger.info(f"➕ Registered new agent: {agent.name}")
    
    def unregister_agent(self, agent_name: str):
        """Remove an agent from the router"""
        self.agents = [a for a in self.agents if a.name != agent_name]
        self.logger.info(f"➖ Unregistered agent: {agent_name}")
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Get info about all registered agents"""
        return [agent.get_info() for agent in self.agents]
