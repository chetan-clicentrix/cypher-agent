"""
STT Provider: Google Speech Recognition
Uses sounddevice for mic recording + Google's free STT API
No pyaudio needed! Works on Windows Python 3.13
"""

import wave
import tempfile
import os
import sounddevice as sd
import numpy as np
from typing import Optional
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()


class GoogleSpeechProvider:
    """
    Speech-to-Text using Google's free Web Speech API
    Uses sounddevice for recording (avoids pyaudio issues on Windows)
    
    - 100% Free (uses Google's free API)
    - No API key required
    - Works on Windows Python 3.13
    """
    
    def __init__(self):
        self.available = False
        self.sample_rate = 16000  # 16kHz mono - best for speech
        self.channels = 1
        
        # Mic device index from env (defaults to 1 = Airdopes 300 headset)
        mic_index = os.getenv('CIPHER_MIC_DEVICE', '1')
        self.mic_device = int(mic_index)
        
        try:
            devices = sd.query_devices()
            mic_name = devices[self.mic_device]['name'] if self.mic_device < len(devices) else 'Unknown'
            self.recognizer = sr.Recognizer()
            self.available = True
            print(f"✅ Google Speech STT initialized (mic: [{self.mic_device}] {mic_name})")
        except Exception as e:
            print(f"⚠️ Google Speech STT unavailable: {e}")
    
    def _record_until_silence(self, 
                               silence_db: float = -70.0,
                               silence_duration: float = 1.5,
                               max_duration: int = 30) -> Optional[np.ndarray]:
        """
        Record from mic until user stops speaking
        Uses RMS-based silence detection
        """
        chunk = int(self.sample_rate * 0.1)  # 100ms chunks
        all_audio = []
        silent_chunks = 0
        needed_silent = int(silence_duration / 0.1)
        started = False
        loud_enough = False
        
        try:
            with sd.InputStream(samplerate=self.sample_rate,
                                channels=self.channels,
                                dtype='float32',
                                blocksize=chunk,
                                device=self.mic_device) as stream:
                
                print("🎙️ Speak now...")
                
                for i in range(int(max_duration / 0.1)):
                    data, _ = stream.read(chunk)
                    
                    # Calculate RMS volume in dB
                    rms = np.sqrt(np.mean(data ** 2))
                    db = 20 * np.log10(rms + 1e-10)
                    
                    # Debug: show levels every 5 chunks
                    if i % 5 == 0:
                        bar = "█" * max(0, min(int(db + 70), 20))
                        print(f"  Level: {db:.0f}dB [{bar:<20}]", end='\r')
                    
                    if db > silence_db:
                        # Sound detected
                        started = True
                        loud_enough = True
                        silent_chunks = 0
                        all_audio.append(data)
                    elif started:
                        # Silence after speaking
                        silent_chunks += 1
                        all_audio.append(data)
                        if silent_chunks >= needed_silent:
                            break
                
                print()  # newline after level display
                
                if not all_audio or not loud_enough:
                    return None
                
                return np.concatenate(all_audio, axis=0)
                
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None

    
    def _save_wav(self, audio: np.ndarray) -> str:
        """Save numpy audio array to a temp WAV file"""
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        
        # Convert float32 → int16
        audio_int16 = (audio * 32767).astype(np.int16)
        
        with wave.open(tmp.name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        return tmp.name
    
    def listen_and_transcribe(self, duration: Optional[int] = None) -> Optional[str]:
        """
        Record from microphone and transcribe using Google STT
        """
        if not self.available:
            return None
        
        try:
            # 1. Record audio
            if duration:
                audio_data = sd.rec(int(duration * self.sample_rate),
                                   samplerate=self.sample_rate,
                                   channels=self.channels,
                                   dtype='float32')
                sd.wait()
            else:
                audio_data = self._record_until_silence()
            
            if audio_data is None or len(audio_data) == 0:
                print("⏱️ No speech detected. Please try again.")
                return None
            
            # 2. Save to WAV file
            wav_path = self._save_wav(audio_data)
            
            # 3. Transcribe using SpeechRecognition with WAV file
            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)
            
            os.unlink(wav_path)  # Cleanup
            
            # 4. Send to Google STT
            print("🔄 Transcribing...")
            text = self.recognizer.recognize_google(audio)
            print(f"📝 Heard: {text}")
            return text
            
        except sr.UnknownValueError:
            print("❓ Could not understand. Please speak more clearly.")
            return None
        except sr.RequestError as e:
            print(f"❌ Google STT error: {e}")
            return None
        except Exception as e:
            print(f"❌ STT error: {e}")
            return None

