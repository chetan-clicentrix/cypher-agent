"""
Pyttsx3 TTS Provider
Offline text-to-speech using Pyttsx3
"""

import pyttsx3
import threading
from typing import Optional


class Pyttsx3Provider:
    """
    Offline TTS using Pyttsx3
    Runs in separate thread to avoid asyncio conflicts
    """
    
    def __init__(self, rate: int = 175, volume: float = 0.9, voice_index: int = 0):
        try:
            self.rate = rate
            self.volume = volume
            self.voice_index = voice_index
            self.available = True
            # Don't init engine here - create fresh one each time to avoid loop issues
        except Exception as e:
            print(f"Error initializing Pyttsx3: {e}")
            self.available = False
    
    def _speak_in_thread(self, text: str):
        """
        Speak in a fresh thread with its own engine instance
        This avoids asyncio event loop conflicts
        """
        try:
            # Create a fresh engine for each call (thread-safe)
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            
            # Set voice
            voices = engine.getProperty('voices')
            if voices and len(voices) > self.voice_index:
                engine.setProperty('voice', voices[self.voice_index].id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"TTS thread error: {e}")
    
    def speak(self, text: str) -> bool:
        """
        Speak text in a separate thread (non-blocking for asyncio)
        """
        if not self.available:
            return False
        
        try:
            # Run in a daemon thread so it doesn't block the event loop
            thread = threading.Thread(
                target=self._speak_in_thread,
                args=(text,),
                daemon=True
            )
            thread.start()
            thread.join()  # Wait for speech to finish
            return True
        except Exception as e:
            print(f"Error starting TTS thread: {e}")
            return False
    
    def speak_async(self, text: str) -> bool:
        """
        Speak text without waiting (fire and forget)
        Use this for non-blocking speech
        """
        if not self.available:
            return False
        
        try:
            thread = threading.Thread(
                target=self._speak_in_thread,
                args=(text,),
                daemon=True
            )
            thread.start()
            return True
        except Exception as e:
            print(f"Error starting TTS thread: {e}")
            return False
    
    def save_to_file(self, text: str, filename: str) -> bool:
        """Save speech to audio file"""
        if not self.available:
            return False
        
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            engine.save_to_file(text, filename)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
    
    def get_voices(self) -> list:
        """Get list of available voices"""
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            result = [{"id": v.id, "name": v.name} for v in voices]
            engine.stop()
            return result
        except:
            return []

    
    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Save speech to audio file
        
        Args:
            text: Text to convert
            filename: Output filename (e.g., 'output.wav')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
    
    def get_voices(self) -> list:
        """Get list of available voices"""
        if not self.available:
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [{"id": v.id, "name": v.name, "languages": v.languages} for v in voices]
        except:
            return []
