"""
Gemini TTS Provider
Cloud text-to-speech using Google Gemini
"""

import os
from pathlib import Path
from typing import Optional
import platform
import subprocess


class GeminiTTSProvider:
    """
    Cloud TTS using Google Gemini
    
    Pros:
    - High-quality, natural voices
    - Free tier available
    - Uses existing Gemini API key
    
    Cons:
    - Requires internet
    - Daily limits on free tier
    """
    
    def __init__(self, api_key: Optional[str] = None, voice: str = "Aoede", output_dir: str = "audio"):
        """
        Initialize Gemini TTS
        
        Args:
            api_key: Gemini API key (or from env)
            voice: Voice name (default: Aoede - female)
            output_dir: Directory to save audio files
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.voice = voice
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Check if API key is available
        if not self.api_key:
            print("⚠️ Gemini API key not found. Cloud TTS unavailable.")
            self.available = False
            return
        
        try:
            from google import genai
            from google.genai import types
            
            self.client = genai.Client(api_key=self.api_key)
            self.types = types
            self.model = "gemini-2.0-flash-exp"  # Using flash model for TTS
            self.available = True
            print("✅ Gemini TTS initialized")
        except Exception as e:
            print(f"Error initializing Gemini TTS: {e}")
            self.available = False
    
    def speak(self, text: str, output_file: Optional[str] = None) -> bool:
        """
        Generate speech and play it
        
        Args:
            text: Text to speak
            output_file: Optional custom filename
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            print("⚠️ Gemini TTS not available")
            return False
        
        try:
            # Generate unique filename if not provided
            if not output_file:
                import time
                output_file = self.output_dir / f"speech_{int(time.time())}.wav"
            else:
                output_file = self.output_dir / output_file
            
            # Generate speech
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=self.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=self.types.SpeechConfig(
                        voice_config=self.types.VoiceConfig(
                            prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    )
                )
            )
            
            # Save audio
            with open(output_file, 'wb') as f:
                f.write(response.audio_data)
            
            # Play audio
            self._play_audio(str(output_file))
            return True
            
        except Exception as e:
            print(f"Error with Gemini TTS: {e}")
            return False
    
    def _play_audio(self, filename: str):
        """Play audio file using system player"""
        try:
            system = platform.system()
            
            if system == "Windows":
                os.startfile(filename)
            elif system == "Darwin":  # macOS
                subprocess.call(["afplay", filename])
            else:  # Linux
                subprocess.call(["aplay", filename])
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Save speech to audio file without playing
        
        Args:
            text: Text to convert
            filename: Output filename
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=self.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=self.types.SpeechConfig(
                        voice_config=self.types.VoiceConfig(
                            prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    )
                )
            )
            
            output_path = self.output_dir / filename
            with open(output_path, 'wb') as f:
                f.write(response.audio_data)
            
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
