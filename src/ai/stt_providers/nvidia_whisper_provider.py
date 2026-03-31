"""
STT Provider: NVIDIA Whisper-large-v3
Speech-to-text using NVIDIA's free API
"""

import os
import io
import tempfile
import requests
import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Optional
from pathlib import Path


class NvidiaWhisperProvider:
    """
    Speech-to-Text using NVIDIA's free Whisper-large-v3 API
    
    NVIDIA provides free API access to whisper-large-v3 via their
    AI Foundation Models catalog.
    
    API Endpoint: https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/
    Model: openai/whisper-large-v3
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NVIDIA_API_KEY')
        self.available = False
        
        # NVIDIA API endpoint for Whisper
        self.api_url = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/1598d209-5e27-4d3c-8079-4751568b1081"
        
        # Audio recording settings
        self.sample_rate = 16000  # Whisper works best at 16kHz
        self.channels = 1         # Mono audio
        
        if not self.api_key:
            print("⚠️ NVIDIA_API_KEY not set. Add to .env file.")
            return
        
        self.available = True
        print("✅ NVIDIA Whisper STT initialized")
    
    def record_audio(self, duration: int = 5) -> Optional[np.ndarray]:
        """
        Record audio from microphone
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Audio data as numpy array, or None if failed
        """
        try:
            print(f"🎙️ Recording for {duration} seconds... Speak now!")
            
            # Record audio
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            sd.wait()  # Wait for recording to complete
            
            print("✅ Recording complete!")
            return audio_data
            
        except Exception as e:
            print(f"❌ Error recording audio: {e}")
            return None
    
    def record_until_silence(self, silence_threshold: float = 0.01, 
                              silence_duration: float = 1.5,
                              max_duration: int = 30) -> Optional[np.ndarray]:
        """
        Record audio and stop automatically when user stops speaking
        
        Args:
            silence_threshold: Volume below this is considered silence
            silence_duration: Seconds of silence before stopping
            max_duration: Maximum recording duration
            
        Returns:
            Audio data, or None if failed
        """
        try:
            print("🎙️ Listening... (speak now, stop speaking to end)")
            
            chunk_size = int(self.sample_rate * 0.1)  # 100ms chunks
            all_audio = []
            silent_chunks = 0
            max_silent_chunks = int(silence_duration / 0.1)
            started_speaking = False
            
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='float32') as stream:
                for _ in range(int(max_duration / 0.1)):
                    chunk, _ = stream.read(chunk_size)
                    volume = np.abs(chunk).mean()
                    
                    if volume > silence_threshold:
                        # User is speaking
                        started_speaking = True
                        silent_chunks = 0
                        all_audio.append(chunk)
                    elif started_speaking:
                        # Silence after speaking
                        silent_chunks += 1
                        all_audio.append(chunk)
                        
                        if silent_chunks >= max_silent_chunks:
                            # Enough silence - stop recording
                            break
            
            if not all_audio:
                return None
            
            audio_data = np.concatenate(all_audio, axis=0)
            print("✅ Recording complete!")
            return audio_data
            
        except Exception as e:
            print(f"❌ Error recording: {e}")
            return None
    
    def transcribe_audio_array(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio data using NVIDIA Whisper API
        
        Args:
            audio_data: Audio as numpy array
            
        Returns:
            Transcribed text, or None if failed
        """
        if not self.available:
            return None
        
        try:
            # Save audio to temp WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            sf.write(tmp_path, audio_data, self.sample_rate)
            
            # Transcribe using NVIDIA API
            result = self.transcribe_file(tmp_path)
            
            # Cleanup temp file
            os.unlink(tmp_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Error transcribing: {e}")
            return None
    
    def transcribe_file(self, audio_path: str) -> Optional[str]:
        """
        Transcribe an audio file using NVIDIA Whisper API
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            Transcribed text, or None if failed
        """
        if not self.available:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
            
            # Send audio file to NVIDIA API
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'audio': (Path(audio_path).name, audio_file, 'audio/wav')
                }
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                # Extract text from response
                text = result.get('text', '') or result.get('transcription', '')
                return text.strip()
            else:
                print(f"❌ NVIDIA API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def listen_and_transcribe(self, duration: Optional[int] = None) -> Optional[str]:
        """
        Record from mic and transcribe
        
        Args:
            duration: Fixed duration (None = auto-stop on silence)
            
        Returns:
            Transcribed text, or None if failed
        """
        if not self.available:
            print("❌ STT not available")
            return None
        
        # Record audio
        if duration:
            audio = self.record_audio(duration)
        else:
            audio = self.record_until_silence()
        
        if audio is None:
            return None
        
        # Transcribe
        print("🔄 Transcribing...")
        text = self.transcribe_audio_array(audio)
        
        if text:
            print(f"📝 Heard: {text}")
        
        return text
