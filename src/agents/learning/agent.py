"""
Learning Agent
Automatically extracts and stores important information from conversations
"""

from typing import List, Optional, Dict, Any
import asyncio
from ..base_agent import BaseAgent
from ...utils.memory import get_memory
from ...core.settings import settings


class LearningAgent(BaseAgent):
    """
    Monitors conversations and automatically learns about the user
    
    Intelligently extracts:
    - Name, location, age
    - Job, company, role
    - Preferences, interests
    - if you learn new thing
    Saves to:
    - USER.md: Facts about user (parsed and structured)
    - MEMORY.md: Project insights, decisions, learnings
    """
    
    def __init__(self, llm_orchestrator, llm_router=None):
        super().__init__(
            "Learning Agent",
            "Updates the AI's core instructions and behavior guidelines. Route here only if the user explicitly instructs you to change how you talk, act, or behave permanently.",
            llm_orchestrator
        )
        self.llm_router = llm_router
        self.memory = get_memory()
        
        # Patterns that indicate learning opportunities
        self.user_patterns = [
            'my name is', 'i am', 'call me',
            'i work at', 'i work on', 'my job',
            'i live in', 'i\'m from', 'from'
        ]
        
        self.preference_patterns = [
            'i prefer', 'i like', 'i love', 'i hate',
            'i usually', 'i always', 'i never'
        ]
        
        self.memory_patterns = [
            'remember that', 'note that', 'keep in mind',
            'important', 'decision', 'we decided'
        ]
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        This agent runs in the background, always returns 0
        It processes queries after other agents
        """
        return 0.0
    
    async def extract_user_info_with_llm(self, query: str) -> Dict[str, str]:
        """
        Use LLM to intelligently extract structured user information
        """
        try:
            model_name = settings.get_agent_llm(self.name)
            llm = self.llm_orchestrator.get_model_by_name(model_name)
            timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
            if not llm:
                return {}
            
            extraction_prompt = f"""Extract structured information from this user message. Return ONLY a JSON object with these fields (use null if not mentioned):

User message: "{query}"

Extract:
- name: Full name
- location: City/place
- company: Company name
- role: Job title/role
- interests: What they like (comma-separated)

Return ONLY valid JSON, nothing else:
{{
  "name": "...",
  "location": "...",
  "company": "...",
  "role": "...",
  "interests": "..."
}}"""
            
            result = await asyncio.wait_for(llm.ainvoke(extraction_prompt), timeout=timeout)
            response = result.content.strip()
            
            # Try to parse JSON
            import json
            # Remove markdown code blocks if present
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response.strip())
            return {k: v for k, v in data.items() if v and v != "null"}
            
        except Exception as e:
            self.logger.error(f"Error extracting with LLM: {e}")
            return {}
    
    async def extract_learnings(self, query: str, response: str) -> Dict[str, Any]:
        """
        Extract important information and categorize it
        Returns dict with 'user_info', 'preferences', and 'memory' keys
        """
        query_lower = query.lower()
        learnings = {
            'user_info': {},
            'preferences': [],
            'memory': []
        }
        
        # Check if this looks like user information
        has_user_info = any(p in query_lower for p in self.user_patterns)
        
        if has_user_info:
            # Use LLM to intelligently extract structured info
            user_info = await self.extract_user_info_with_llm(query)
            if user_info:
                learnings['user_info'] = user_info
        
        # Check for preferences
        elif any(p in query_lower for p in self.preference_patterns):
            learnings['preferences'].append(query)
        
        # Check for memory items
        elif any(p in query_lower for p in self.memory_patterns):
            learnings['memory'].append(query)
        
        return learnings
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        This agent doesn't respond directly, it learns in the background
        """
        # Get the response from context if available
        response = context.get('response', '') if context else ''
        
        # Extract learnings
        learnings = await self.extract_learnings(query, response)
        
        # Update USER.md with structured info
        if learnings['user_info']:
            for field, value in learnings['user_info'].items():
                # Map to USER.md fields
                field_map = {
                    'name': 'Name',
                    'location': 'Location',
                    'company': 'Company',
                    'role': 'Role'
                }
                
                if field in field_map:
                    success = self.memory.update_user_profile(field_map[field], value)
                    if success:
                        self.logger.info(f"📝 Updated USER.md: {field_map[field]} = {value}")
                elif field == 'interests':
                    # Add to interests section (for now, just log)
                    self.logger.info(f"📝 Learned interests: {value}")
        
        # Save preferences to MEMORY.md
        for pref in learnings['preferences']:
            self.memory.add_to_long_term_memory(f"Preference: {pref}")
            self.logger.info(f"📝 Learned (MEMORY): Preference - {pref}")
        
        # Save to MEMORY.md
        for item in learnings['memory']:
            self.memory.add_to_long_term_memory(item)
            self.logger.info(f"📝 Learned (MEMORY): {item}")
        
        return ""  # This agent doesn't produce output
    
    def get_tools(self) -> List:
        """Learning agent doesn't use external tools"""
        return []

