"""
Voice Agent
Handles voice-related commands and TTS control
"""

from typing import List, Optional, Dict, Any
from ..base_agent import BaseAgent


class VoiceAgent(BaseAgent):
    """
    Specialized agent for voice/TTS control
    
    Handles:
    - Enable/disable voice output
    - Switch between local/cloud TTS
    - Voice settings
    - Speak specific text
    """
    
    def __init__(self, llm_orchestrator, tts_orchestrator):
        super().__init__(
            "Voice Agent", 
            "Manages text-to-speech, speech-to-text, microphone settings, and voice-related settings. Route here only when the user explicitly asks to speak, change voice, or activate voice mode.",
            llm_orchestrator
        )
        self.tts = tts_orchestrator
        self.voice_enabled = False  # Start with voice disabled
        
        # Keywords for voice commands
        self.voice_keywords = [
            'voice', 'speak', 'say', 'read aloud',
            'enable voice', 'disable voice', 'turn on voice', 'turn off voice',
            'mute', 'unmute', 'tts',
            'local tts', 'cloud tts', 'switch tts'
        ]
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Detect voice-related queries
        """
        query_lower = query.lower()
        
        # Check for voice keywords
        matches = sum(1 for kw in self.voice_keywords if kw in query_lower)
        if matches > 0:
            return min(matches * 0.5, 0.9)
        
        return 0.0
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process voice-related commands
        """
        query_lower = query.lower()
        
        # Enable voice
        if any(kw in query_lower for kw in ['enable voice', 'turn on voice', 'unmute']):
            self.voice_enabled = True
            provider = self.tts.get_current_provider()
            return f"🔊 Voice output enabled! Using {provider} TTS."
        
        # Disable voice
        elif any(kw in query_lower for kw in ['disable voice', 'turn off voice', 'mute']):
            self.voice_enabled = False
            return "🔇 Voice output disabled."
        
        # Switch to local TTS
        elif 'local tts' in query_lower or 'use local' in query_lower:
            if self.tts.set_provider('local'):
                return "✅ Switched to Local TTS (Pyttsx3 - offline, fast)"
            else:
                return "❌ Local TTS not available"
        
        # Switch to cloud TTS
        elif 'cloud tts' in query_lower or 'use cloud' in query_lower or 'gemini tts' in query_lower:
            if self.tts.set_provider('cloud'):
                return "✅ Switched to Cloud TTS (Gemini - high quality)"
            else:
                return "❌ Cloud TTS not available. Check GEMINI_API_KEY in .env"
        
        # Speak specific text
        elif 'speak' in query_lower or 'say' in query_lower or 'read aloud' in query_lower:
            # Extract text to speak
            text = query
            for keyword in ['speak', 'say', 'read aloud', 'say this', 'speak this']:
                text = text.lower().replace(keyword, '').strip()
            
            if text:
                success = self.tts.speak(text)
                if success:
                    return f"🔊 Speaking: {text}"
                else:
                    return "❌ TTS not available"
            else:
                return "What would you like me to say?"
        
        # Voice status
        elif 'voice status' in query_lower or 'tts status' in query_lower:
            status = "enabled" if self.voice_enabled else "disabled"
            provider = self.tts.get_current_provider()
            available = self.tts.get_available_providers()
            
            return f"""Voice Status:
- Voice output: {status}
- Current TTS: {provider}
- Available: {', '.join(available)}"""
        
        return "Voice command not recognized. Try: 'enable voice', 'use cloud TTS', or 'speak hello'"
    
    def get_tools(self) -> List:
        """Voice agent doesn't use external tools"""
        return []
