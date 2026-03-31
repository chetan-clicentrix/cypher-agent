"""
STT Orchestrator
Manages Speech-to-Text providers
"""

import asyncio
from typing import Optional
from .stt_providers.google_speech_provider import GoogleSpeechProvider
from .stt_providers.nvidia_whisper_provider import NvidiaWhisperProvider


class STTOrchestrator:
    """
    Manages STT providers
    
    Providers:
    - google: Google Speech Recognition (free, no API key, primary)
    - nvidia: NVIDIA Whisper-large-v3 (free API, higher accuracy, optional)
    """
    
    def __init__(self):
        self.providers = {}
        self.current_provider = "google"  # Default to Google (works immediately)
        
        from ..utils.logger import setup_logger
        self.logger = setup_logger("INFO")
        
        self._setup_providers()
    
    def _setup_providers(self):
        """Initialize all available STT providers"""
        
        # 1. Google Speech (free, no API key needed - try first)
        try:
            google = GoogleSpeechProvider()
            if google.available:
                self.providers['google'] = google
                self.current_provider = "google"
                self.logger.info("🎙️ Google Speech STT ready (primary)")
        except Exception as e:
            self.logger.warning(f"⚠️ Google STT unavailable: {e}")
        
        # 2. NVIDIA Whisper (optional, higher accuracy)
        try:
            nvidia = NvidiaWhisperProvider()
            if nvidia.available:
                self.providers['nvidia'] = nvidia
                self.logger.info("🎙️ NVIDIA Whisper STT ready (secondary)")
        except Exception as e:
            self.logger.warning(f"⚠️ NVIDIA STT unavailable: {e}")
        
        if not self.providers:
            self.logger.error("❌ No STT providers available!")
        else:
            self.logger.info(f"   Current STT: {self.current_provider}")
    
    def is_available(self) -> bool:
        return len(self.providers) > 0
    
    def set_provider(self, provider: str) -> bool:
        """Switch STT provider"""
        if provider in self.providers:
            self.current_provider = provider
            self.logger.info(f"✅ Switched STT to: {provider}")
            return True
        return False
    
    def listen(self, duration: Optional[int] = None) -> Optional[str]:
        """
        Record from microphone and transcribe
        
        Args:
            duration: Fixed duration in seconds (None = auto-stop on silence)
            
        Returns:
            Transcribed text or None
        """
        provider = self.providers.get(self.current_provider)
        if not provider:
            # Try any available provider
            if self.providers:
                provider = list(self.providers.values())[0]
            else:
                self.logger.error("❌ No STT provider available")
                return None
        
        return provider.listen_and_transcribe(duration=duration)
    
    async def listen_async(self, duration: Optional[int] = None) -> Optional[str]:
        """
        Async version of listen - runs in thread executor
        so it doesn't block the asyncio event loop
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.listen, duration)

