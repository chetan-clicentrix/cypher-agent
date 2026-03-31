"""
STT Providers Package
"""

from .google_speech_provider import GoogleSpeechProvider
from .nvidia_whisper_provider import NvidiaWhisperProvider

__all__ = ["GoogleSpeechProvider", "NvidiaWhisperProvider"]
