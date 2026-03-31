import os
import queue
import threading
from typing import Optional
import wave

try:
    import pyaudio
except ImportError:
    pyaudio = None
    
try:
    import riva.client
except ImportError:
    riva = None

from ...utils.logger import setup_logger

logger = setup_logger("INFO")

class RivaTTSProvider:
    """TTS Provider using NVIDIA Riva magpie-tts-multilingual model via gRPC"""
    def __init__(self):
        self.available = False
        self.auth = None
        self.tts_service = None
        
        if not pyaudio:
            logger.warning("PyAudio not available. Riva TTS requires PyAudio to play streamed audio.")
            return
            
        if not riva:
            logger.warning("Nvidia-Riva-Client not installed.")
            return
            
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            logger.warning("NVIDIA_API_KEY not found in .env. Riva TTS unavailable.")
            return
            
        try:
            # Authenticate with the NVIDIA Build endpoint
            self.auth = riva.client.Auth(
                None, # no uri needed if using use_ssl with specific metadata
                use_ssl=True,
                metadata_args=[
                    ("function-id", "877104f7-e885-42b9-8de8-f6e4c6303969"),
                    ("authorization", f"Bearer {api_key}")
                ]
            )
            
            # The specific endpoint for NVIDIA NIM TTS
            self.tts_service = riva.client.SpeechSynthesisService(self.auth)
            # Hardcode the endpoint URI directly into the stub since Auth() doesn't expose it nicely in all versions
            import grpc
            channel = grpc.secure_channel("grpc.nvcf.nvidia.com:443", grpc.ssl_channel_credentials())
            self.tts_service.stub = riva.client.proto.riva_tts_pb2_grpc.RivaSpeechSynthesisStub(channel)

            self.available = True
        except Exception as e:
            logger.warning(f"Failed to initialize Riva TTS client: {e}")
            
    def speak(self, text: str, voice_name: str = "Magpie-Multilingual.EN-US.Aria") -> bool:
        """Stream text to audio using Riva and play it back instantly"""
        if not self.available:
            return False
            
        try:
            logger.info(f"🗣️ Stream-speaking via Riva ({voice_name}): {text[:30]}...")
            
            # Create a PyAudio instance
            pa = pyaudio.PyAudio()
            
            # Request streaming synthesis from Riva
            responses = self.tts_service.synthesize_online(
                text,
                voice_name=voice_name,
                language_code="en-US"
            )

            # We don't know the precise framerate until the first packet arrives, 
            # but Riva defaults to 44.1kHz or 48kHz. We'll set it dynamically.
            stream = None
            
            try:
                for response in responses:
                    if len(response.audio) > 0:
                        if stream is None:
                            # Initialize audio playback stream on first valid audio chunk
                            # Most Riva multilingal models stream cleanly at 44100Hz or 48000Hz 
                            stream = pa.open(
                                format=pyaudio.paInt16,
                                channels=1,
                                rate=48000,
                                output=True
                            )
                        # Write raw audio bytes to speaker
                        stream.write(response.audio)
                        
            finally:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
                pa.terminate()
                
            return True
            
        except Exception as e:
            logger.error(f"Riva TTS error: {e}")
            return False
