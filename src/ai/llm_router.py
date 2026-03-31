"""
Intelligent LLM Router
Routes queries to local or cloud LLM based on complexity
"""

from typing import Optional, Literal
from .complexity_analyzer import ComplexityAnalyzer
from ..utils.logger import setup_logger

logger = setup_logger()

LLMType = Literal["local", "cloud"]

class LLMRouter:
    """Routes queries to appropriate LLM based on complexity"""
    
    def __init__(self, config: dict):
        """
        Initialize LLM Router
        
        Args:
            config: Configuration dict with thresholds and preferences
        """
        self.analyzer = ComplexityAnalyzer()
        self.simple_threshold = config.get('simple_threshold', 3)
        self.complex_threshold = config.get('complex_threshold', 7)
        self.medium_preference = config.get('medium_preference', 'local')
        
        logger.info(f"🔀 LLM Router initialized: Simple≤{self.simple_threshold}, Complex≥{self.complex_threshold}")
    
    def route(self, query: str, context: dict = None) -> tuple[LLMType, int, str]:
        """
        Determine which LLM to use for the query
        
        Args:
            query: User's query
            context: Optional context information
        
        Returns:
            tuple: (llm_type, complexity_score, reasoning)
        """
        score = self.analyzer.analyze(query, context)
        complexity_label = self.analyzer.get_complexity_label(score)
        
        # Routing logic
        if score <= self.simple_threshold:
            llm_type = "local"
            reasoning = f"Simple task (score: {score}) → Local LLM for fast response"
        elif score >= self.complex_threshold:
            llm_type = "cloud"
            reasoning = f"Complex task (score: {score}) → Cloud LLM for better reasoning"
        else:
            # Medium complexity - use preference
            llm_type = self.medium_preference
            reasoning = f"Medium task (score: {score}) → {llm_type.title()} LLM (preference)"
        
        logger.info(f"📊 Query: '{query[:50]}...' | Complexity: {complexity_label} ({score}) → {llm_type.upper()}")
        
        return llm_type, score, reasoning
    
    def should_use_cloud(self, query: str, context: dict = None) -> bool:
        """Quick check if cloud LLM should be used"""
        llm_type, _, _ = self.route(query, context)
        return llm_type == "cloud"
