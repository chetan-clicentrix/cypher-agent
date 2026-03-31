"""
Base Agent Class
Abstract base class for all specialized agents in the Cipher system
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..utils.logger import setup_logger

logger = setup_logger()


class BaseAgent(ABC):
    """
    Base class for all specialized agents
    
    Each agent is responsible for:
    1. Determining if it can handle a query (intent matching)
    2. Processing queries in its domain
    3. Managing its own tools and resources
    """
    
    def __init__(self, name: str, description: str, llm_orchestrator):
        """
        Initialize base agent
        
        Args:
            name: Human-readable name of the agent
            description: Clear, specialized description of this agent's capabilities for the LLM router
            llm_orchestrator: LLMOrchestrator instance for LLM access
        """
        self.name = name
        self.description = description
        self.llm_orchestrator = llm_orchestrator
        self.logger = setup_logger()
        self.logger.info(f"✅ Initialized {self.name}")
    
    @abstractmethod
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the query
        
        Args:
            query: User's query string
            context: Optional context information (history, user prefs, etc.)
        
        Returns:
            float: Confidence score 0.0-1.0
                  0.0 = Cannot handle at all
                  1.0 = Perfect match for this agent
                  
        Example:
            "Show me RAM usage" -> SystemAgent returns 0.9
            "Generate an image" -> MediaAgent returns 0.95
        """
        pass
    
    @abstractmethod
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process the query and return a response
        
        Args:
            query: User's query string
            context: Optional context information
        
        Returns:
            str: Agent's response to the query
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> List[Any]:
        """
        Get list of tools this agent uses
        
        Returns:
            List of LangChain tools or custom tool objects
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get agent metadata and status
        
        Returns:
            Dict containing agent info
        """
        return {
            "name": self.name,
            "description": self.description,
            "tools": [tool.name if hasattr(tool, 'name') else str(tool) for tool in self.get_tools()],
            "status": "active"
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
