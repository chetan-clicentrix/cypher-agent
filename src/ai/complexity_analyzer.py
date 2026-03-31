"""
Task Complexity Analyzer
Analyzes user queries to determine routing to local or cloud LLM
"""

class ComplexityAnalyzer:
    """Analyzes task complexity to route to appropriate LLM"""
    
    def __init__(self):
        # Keywords that indicate different complexity levels
        self.research_keywords = ['research', 'find information', 'what are', 'compare', 'analyze', 'explain in detail', 'summarize', 'summary', 'top', 'trends', 'latest']
        self.multi_step_keywords = ['and then', 'after that', 'create', 'generate', 'deploy', 'build', 'make a']
        self.creative_keywords = ['suggest', 'recommend', 'design', 'plan', 'strategy', 'brainstorm', 'ideas']
        self.code_keywords = ['debug', 'fix bug', 'refactor', 'optimize code', 'security', 'review code', 'write code']
        self.simple_keywords = ['turn on', 'turn off', 'what is', 'check', 'show', 'open', 'close', 'calculate']
    
    def analyze(self, query: str, context: dict = None) -> int:
        """
        Analyze query complexity and return score 0-10
        
        Args:
            query: User's query string
            context: Optional context (current project, recent history, etc.)
        
        Returns:
            int: Complexity score (0-10)
                0-3: Simple (local LLM)
                4-6: Medium (configurable)
                7-10: Complex (cloud LLM)
        """
        score = 0
        query_lower = query.lower()
        
        # Check for research indicators (+3)
        if any(kw in query_lower for kw in self.research_keywords):
            score += 3
        
        # Check for multi-step indicators (+2)
        if any(kw in query_lower for kw in self.multi_step_keywords):
            score += 2
        
        # Check for creativity/reasoning (+2)
        if any(kw in query_lower for kw in self.creative_keywords):
            score += 2
        
        # Check for code analysis (+2)
        if any(kw in query_lower for kw in self.code_keywords):
            score += 2
        
        # Check for simple commands (cap at 1)
        if any(kw in query_lower for kw in self.simple_keywords) and score == 0:
            score = 1
        
        # Query length factor
        word_count = len(query.split())
        if word_count > 30:
            score += 1  # Long queries often need better reasoning
        
        return min(score, 10)
    
    def get_complexity_label(self, score: int) -> str:
        """Get human-readable complexity label"""
        if score <= 3:
            return "Simple"
        elif score <= 6:
            return "Medium"
        else:
            return "Complex"
