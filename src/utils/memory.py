"""
Memory System
Loads and manages Cipher's persistent memory and personality
Inspired by OpenClaw's memory management approach
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re


class Memory:
    """
    Manages Cipher's persistent memory across multiple files:
    - SOUL.md: Personality and core principles
    - USER.md: User profile and preferences
    - MEMORY.md: Curated long-term learnings
    - memory/YYYY-MM-DD.md: Daily conversation logs
    """
    
    def __init__(self, 
                 soul_path: str = "SOUL.md", 
                 user_path: str = "USER.md",
                 memory_path: str = "MEMORY.md",
                 memory_dir: str = "memory"):
        self.soul_path = Path(soul_path)
        self.user_path = Path(user_path)
        self.memory_path = Path(memory_path)
        self.memory_dir = Path(memory_dir)
        
        # Memory storage
        self.soul_content = ""
        self.user_profile = {}
        self.long_term_memory = []
        self.conversation_history: List[Dict[str, str]] = []
        
        # Create memory directory if it doesn't exist
        self.memory_dir.mkdir(exist_ok=True)
        
        # Load all memory types
        self.load_soul()
        self.load_user_profile()
        self.load_long_term_memory()
        self.load_today_memory()
    
    # ============================================
    # SOUL.md - Personality and Core Principles
    # ============================================
    
    def load_soul(self) -> bool:
        """Load SOUL.md content (personality)"""
        try:
            if self.soul_path.exists():
                with open(self.soul_path, 'r', encoding='utf-8') as f:
                    self.soul_content = f.read()
                return True
            return False
        except Exception as e:
            print(f"Error loading SOUL.md: {e}")
            return False
    
    def get_soul_context(self) -> str:
        """Get soul content for LLM context"""
        return self.soul_content
    
    # ============================================
    # USER.md - User Profile
    # ============================================
    
    def load_user_profile(self) -> Dict[str, Any]:
        """Load USER.md and parse into structured dict"""
        try:
            if not self.user_path.exists():
                return {}
            
            with open(self.user_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple parsing - extract key information
            profile = {
                'name': self._extract_field(content, 'Name'),
                'company': self._extract_field(content, 'Company'),
                'role': self._extract_field(content, 'Role'),
                'full_content': content
            }
            
            self.user_profile = profile
            return profile
        except Exception as e:
            print(f"Error loading USER.md: {e}")
            return {}
    
    def _extract_field(self, content: str, field: str) -> str:
        """Extract field value from markdown"""
        pattern = rf'\*\*{field}\*\*:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, content)
        return match.group(1).strip() if match else ""
    
    def get_user_context(self) -> str:
        """Get user profile for LLM context"""
        return self.user_profile.get('full_content', '')
    
    def update_user_profile(self, field: str, value: str) -> bool:
        """Update specific field in USER.md"""
        try:
            if not self.user_path.exists():
                return False
            
            with open(self.user_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update the field
            pattern = rf'(\*\*{field}\*\*:)\s*(.+?)(\n)'
            updated = re.sub(pattern, rf'\1 {value}\3', content)
            
            with open(self.user_path, 'w', encoding='utf-8') as f:
                f.write(updated)
            
            self.load_user_profile()  # Reload
            return True
        except Exception as e:
            print(f"Error updating USER.md: {e}")
            return False
    
    # ============================================
    # MEMORY.md - Curated Long-Term Memory
    # ============================================
    
    def load_long_term_memory(self) -> List[str]:
        """Load MEMORY.md entries"""
        try:
            if not self.memory_path.exists():
                return []
            
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse entries (simple line-based for now)
            self.long_term_memory = [content]  # Store full content
            return self.long_term_memory
        except Exception as e:
            print(f"Error loading MEMORY.md: {e}")
            return []
    
    def add_to_long_term_memory(self, entry: str, category: str = "Important Learnings") -> bool:
        """Add entry to MEMORY.md under specific category"""
        try:
            if not self.memory_path.exists():
                return False
            
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find category section and add entry
            timestamp = datetime.now().strftime("%Y-%m-%d")
            new_entry = f"\n**{timestamp}** - {entry}\n"
            
            # Append to end for now (can be improved to find correct section)
            updated = content + new_entry
            
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                f.write(updated)
            
            self.load_long_term_memory()  # Reload
            return True
        except Exception as e:
            print(f"Error updating MEMORY.md: {e}")
            return False
    
    def get_memory_context(self) -> str:
        """Get MEMORY.md content for LLM context"""
        return self.long_term_memory[0] if self.long_term_memory else ""
    
    # ============================================
    # Daily Logs - Conversation History
    # ============================================
    
    def get_today_memory_path(self) -> Path:
        """Get path to today's memory file"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.memory_dir / f"{today}.md"
    
    def load_today_memory(self) -> bool:
        """Load today's memory log"""
        try:
            memory_path = self.get_today_memory_path()
            if memory_path.exists():
                with open(memory_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return True
            return False
        except Exception as e:
            print(f"Error loading today's memory: {e}")
            return False
    
    def load_recent_daily_logs(self, days: int = 3) -> List[str]:
        """Load last N days of conversation logs"""
        logs = []
        try:
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                log_path = self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"
                
                if log_path.exists():
                    with open(log_path, 'r', encoding='utf-8') as f:
                        logs.append(f.read())
            
            return logs
        except Exception as e:
            print(f"Error loading recent logs: {e}")
            return []
    
    def add_to_conversation(self, role: str, message: str):
        """Add message to conversation history"""
        # Clean any leaked internal routing info from responses
        if role == "Cipher":
            import re
            # Remove parenthetical internal notes like "(Internal routing...)"
            message = re.sub(r'\(Internal routing[^)]*\)', '', message).strip()
            message = re.sub(r'\(Note:.*?complexity.*?\)', '', message, flags=re.IGNORECASE).strip()
        
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 exchanges in memory
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    
    def save_today_memory(self) -> bool:
        """Save today's conversation to daily log"""
        try:
            memory_path = self.get_today_memory_path()
            
            # Create header if new file
            if not memory_path.exists():
                header = f"# Conversation Log - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            else:
                header = ""
            
            # Append conversation history
            with open(memory_path, 'a', encoding='utf-8') as f:
                if header:
                    f.write(header)
                
                for entry in self.conversation_history:
                    f.write(f"**{entry['role']}** ({entry['timestamp']}): {entry['message']}\n\n")
            
            # Clear conversation history after saving
            self.conversation_history = []
            return True
        except Exception as e:
            print(f"Error saving today's memory: {e}")
            return False
    
    def get_conversation_context(self, max_messages: int = 10) -> str:
        """Get recent conversation history as context"""
        if not self.conversation_history:
            return ""
        
        recent = self.conversation_history[-max_messages:]
        context = "## Recent Conversation:\n\n"
        for entry in recent:
            context += f"**{entry['role']}**: {entry['message']}\n"
        
        return context
    
    # ============================================
    # Full Context - Combines All Memory Types
    # ============================================
    
    def get_full_context(self) -> str:
        """
        Get complete context including soul, user profile, memory, and conversation
        """
        context_parts = []
        
        # 1. SOUL.md (Personality)
        if self.soul_content:
            context_parts.append(self.soul_content)
        
        # 2. USER.md (User Profile)
        user_context = self.get_user_context()
        if user_context:
            context_parts.append("\n---\n## User Profile\n" + user_context)
        
        # 3. MEMORY.md (Long-term learnings)
        memory_context = self.get_memory_context()
        if memory_context:
            context_parts.append("\n---\n## Long-Term Memory\n" + memory_context)
        
        # 4. Recent conversation
        conv_context = self.get_conversation_context()
        if conv_context:
            context_parts.append("\n---\n" + conv_context)
        
        return "\n".join(context_parts)


# Global memory instance
_memory = None

def get_memory() -> Memory:
    """Get or create global memory instance"""
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
