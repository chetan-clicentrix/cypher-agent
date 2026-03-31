"""
Settings Manager
Loads configuration from config.yaml and .env
Provides a clean interface for the rest of the app to access settings.
"""

import os
import yaml
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load .env variables immediately
load_dotenv()

class Settings:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load the config.yaml file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")
        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print("⚠️ config.yaml not found. Using default settings.")
            self._config = {}
        except Exception as e:
            print(f"❌ Error loading config.yaml: {e}")
            self._config = {}

    @property
    def default_llm(self) -> str:
        """Get the default LLM provider from config"""
        return self._config.get("llm", {}).get("default_model", "ollama")

    @property
    def router_llm(self) -> str:
        """Get the LLM provider for the AgentRouter"""
        return self._config.get("llm", {}).get("router_model", "ollama")

    def get_agent_llm(self, agent_name: str) -> str:
        """Get the specific LLM configured for an agent, or fallback to default"""
        models = self._config.get("llm", {}).get("agent_models", {})
        return models.get(agent_name, self.default_llm)

    @property
    def cloud_timeout(self) -> int:
        return self._config.get("timeouts", {}).get("cloud_timeout", 30)

    @property
    def local_timeout(self) -> int:
        return self._config.get("timeouts", {}).get("local_timeout", 60)

    @property
    def use_tavily_search(self) -> bool:
        """Determines if the Research Agent should use Tavily (True) or DuckDuckGo (False)"""
        return self._config.get("research", {}).get("use_tavily", False)

    @property
    def tts_provider(self) -> str:
        """Get the default TTS provider (local, cloud, or riva)"""
        return self._config.get("tts", {}).get("provider", "local")

    @property
    def riva_voice(self) -> str:
        """Get the default Riva TTS voice"""
        return self._config.get("tts", {}).get("riva", {}).get("voice", "Magpie-Multilingual.EN-US.Aria")

    @property
    def voice_mode(self) -> str:
        """Get the voice mode (modular or gemini_live)"""
        return self._config.get("voice", {}).get("mode", "modular")

# Global singleton instance
settings = Settings()
