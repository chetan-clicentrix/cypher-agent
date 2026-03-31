"""
TTS Orchestrator
Manages multiple TTS providers (local and cloud)
"""

from typing import Optional, Dict, Any
from .tts_providers.pyttsx3_provider import Pyttsx3Provider
from .tts_providers.gemini_tts_provider import GeminiTTSProvider
from .tts_providers.riva_tts_provider import RivaTTSProvider
from ..core.settings import settings


class TTSOrchestrator:
    """
    Manages TTS providers and handles switching between them
    
    Providers:
    - local: Pyttsx3 (offline, free, fast)
    - cloud: Gemini TTS (online, high-quality)
    """
    
    def __init__(self):
        self.providers: Dict[str, Any] = {}
        self.current_provider = settings.tts_provider
        
        # Setup logger
        from ..utils.logger import setup_logger
        self.logger = setup_logger("INFO")
        
        self._setup_providers()
    
    def _setup_providers(self):
        """Initialize all available TTS providers"""
        
        # 1. Setup Pyttsx3 (local, offline)
        try:
            local_tts = Pyttsx3Provider()
            if local_tts.available:
                self.providers['local'] = local_tts
                self.logger.info("🏠 Local TTS (Pyttsx3) ready")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize local TTS: {e}")
        
        # 2. Setup Gemini TTS (cloud, premium)
        try:
            cloud_tts = GeminiTTSProvider()
            if cloud_tts.available:
                self.providers['cloud'] = cloud_tts
                self.logger.info("🌐 Cloud TTS (Gemini) ready")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize cloud TTS: {e}")

        # 3. Setup NVIDIA Riva (cloud, premium streaming)
        try:
            riva_tts = RivaTTSProvider()
            if getattr(riva_tts, 'available', False):
                self.providers['riva'] = riva_tts
                self.logger.info("⚡ Cloud TTS (NVIDIA Riva) ready")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Riva TTS: {e}")
        
        # Fallback check
        if not self.providers:
            self.logger.error("❌ No TTS providers available!")
    
    def speak(self, text: str, provider: Optional[str] = None) -> bool:
        """
        Convert text to speech
        
        Args:
            text: Text to speak
            provider: 'local' or 'cloud' (uses current if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        # Use specified provider or current default
        provider_name = provider or self.current_provider
        
        # Check if provider exists
        if provider_name not in self.providers:
            print(f"⚠️ Provider '{provider_name}' not available")
            # Try fallback
            if self.providers:
                provider_name = list(self.providers.keys())[0]
                print(f"🔄 Falling back to '{provider_name}'")
            else:
                return False
        
        # Speak using selected provider
        try:
            if provider_name == 'riva':
                # Pass the exact config voice name to Riva
                return self.providers[provider_name].speak(text, voice_name=settings.riva_voice)
            else:
                return self.providers[provider_name].speak(text)
        except Exception as e:
            print(f"Error speaking: {e}")
            return False
    
    def set_provider(self, provider: str) -> bool:
        """
        Switch TTS provider
        
        Args:
            provider: 'local' or 'cloud'
            
        Returns:
            True if switched, False if provider unavailable
        """
        if provider in self.providers:
            self.current_provider = provider
            print(f"✅ Switched to {provider} TTS")
            return True
        else:
            print(f"⚠️ Provider '{provider}' not available")
            return False
    
    def get_current_provider(self) -> str:
        """Get name of current TTS provider"""
        return self.current_provider
    
    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    def is_available(self) -> bool:
        """Check if any TTS provider is available"""
        return len(self.providers) > 0
