"""
Wake Word Detector
Continuously listens for "Cipher" wake word and triggers voice mode
"""

import threading
import numpy as np
import sounddevice as sd
import os
import pvporcupine
from typing import Callable, Optional
from dotenv import load_dotenv

load_dotenv()

class WakeWordDetector:
    """
    Continuously listens for wake word ("Jarvis") in the background using Picovoice Porcupine.
    
    When wake word detected:
    - Plays a short acknowledgment sound (beep)
    - Triggers the provided callback function
    
    Strategy: Continuous audio stream → Porcupine frame processor → wake word
    """
    
    def __init__(self, 
                 wake_words: list = None,
                 on_wake: Callable = None,
                 mic_device: Optional[int] = None):
        """
        Args:
            wake_words: List of trigger words (ignored now, uses built-in porcupine words)
            on_wake: Callback function to call when wake word detected
            mic_device: Mic device index (from CIPHER_MIC_DEVICE env var)
        """
        self.on_wake = on_wake
        
        # Load Porcupine API key
        self.access_key = os.getenv("PICOVOICE_API_KEY")
        if not self.access_key:
            raise ValueError("PICOVOICE_API_KEY is not set in the environment variables.")
            
        # Initialize Porcupine with "jarvis" keyword. 
        self.porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=['jarvis']
        )
        
        # Mic setup
        mic_index = os.getenv('CIPHER_MIC_DEVICE')
        if mic_device is not None:
            self.mic_device = mic_device
        elif mic_index and mic_index.isdigit():
            self.mic_device = int(mic_index)
        else:
            self.mic_device = None  # OS default microphone
            
        self.sample_rate = self.porcupine.sample_rate
        
        try:
            device_info = sd.query_devices(self.mic_device, 'input')
            self.channels = min(2, int(device_info['max_input_channels']))
        except Exception:
            self.channels = 1
            
        self.frame_length = self.porcupine.frame_length
        
        # State
        self.running = False
        self.is_paused = False
        self.stream: Optional[sd.InputStream] = None
        
        from ..utils.logger import setup_logger
        self.logger = setup_logger("INFO")
        
    def _play_wake_sound(self):
        """Play a short beep to signal wake up"""
        try:
            t = np.linspace(0, 0.2, int(16000 * 0.2))
            beep = 0.3 * np.sin(2 * np.pi * 880 * t)
            sd.play(beep, 16000)
            sd.wait()
        except:
            pass
            
    def _trigger_wake(self, entity: str):
        self._play_wake_sound()
        if self.on_wake:
            self.on_wake(entity)
            
    def _audio_callback(self, indata, frames, time, status):
        """Callback to process each audio frame in real-time"""
        if not self.running or self.is_paused:
            return
            
        if status:
            self.logger.warning(f"Audio stream status: {status}")
            
        # Down-mix to mono
        if self.channels > 1:
            audio_mono = indata[:, 0]
        else:
            audio_mono = indata[:, 0] if indata.ndim > 1 else indata
            
        # Convert audio to int16 expected by Porcupine
        audio_frame = (audio_mono * 32767).astype(np.int16)
        
        # Porcupine expects an exact frame_length.
        if len(audio_frame) == self.frame_length:
            keyword_index = self.porcupine.process(audio_frame)
            if keyword_index >= 0:
                self.logger.info("🔔 Wake word 'Jarvis' detected!")
                # FIRE IN A SEPARATE THREAD SO WE DON'T BLOCK PYAUDIO STREAM:
                threading.Thread(target=self._trigger_wake, args=("jarvis",), daemon=True).start()
    
    def start(self):
        """Start wake word detection in background thread"""
        if self.running:
            return
        
        self.running = True
        
        self.logger.info("👂 Wake word detector started - say 'Jarvis' to wake up!")
        
        # Start PyAudio streaming layer callback
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.frame_length,
            device=self.mic_device,
            channels=self.channels,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()
    
    def stop(self):
        """Stop wake word detection"""
        self.running = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.logger.info("👂 Wake word detector stopped")
    
    def pause(self):
        """Temporarily pause detection (during voice conversation)"""
        self.is_paused = True
    
    def resume(self):
        """Resume detection after voice conversation ends"""
        self.is_paused = False

    def __del__(self):
        if hasattr(self, 'porcupine') and self.porcupine is not None:
            self.porcupine.delete()
