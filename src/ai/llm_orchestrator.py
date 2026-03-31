"""
LLM Orchestrator
Manages local and cloud LLM providers

Tier system:
  local  → Ollama llama3.2      (fast, offline, simple tasks)
  cloud  → Google Gemini Flash  (balanced, most tasks)
  power  → NVIDIA Qwen3.5-397B  (heavy reasoning, complex tasks)
"""

import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from .nvidia_llm_provider import create_nvidia_llm
from ..utils.logger import setup_logger

load_dotenv()
logger = setup_logger()

class LLMOrchestrator:
    """Manages and orchestrates LLM providers across three tiers"""
    
    def __init__(self):
        self.local_llm = None       # Ollama (fast, offline)
        self.cloud_llm = None       # Gemini / OpenAI (balanced)
        self.power_llm = None       # NVIDIA Qwen (powerful)
        self.cloud_provider = None
        self._models = {}           # Cache for custom provider/model instances
        self._setup_providers()
    
    def _setup_providers(self):
        """Initialize LLM providers"""
        
        google_key = os.getenv('GOOGLE_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        # ── Cloud LLM (Gemini > OpenAI > Anthropic) ──────────────────────
        if google_key and google_key != 'your_google_key_here':
            try:
                self.cloud_llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    temperature=0.7,
                    google_api_key=google_key
                )
                self.cloud_provider = "Gemini"
                logger.info("✅ Google Gemini 2.0 Flash initialized (Cloud LLM)")
            except Exception as e:
                logger.warning(f"⚠️ Gemini initialization failed: {e}")
        
        if not self.cloud_llm and openai_key and openai_key != 'your_openai_key_here':
            try:
                self.cloud_llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7, api_key=openai_key)
                self.cloud_provider = "OpenAI"
                logger.info("✅ OpenAI GPT-4 initialized (Cloud LLM)")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI initialization failed: {e}")
        
        if not self.cloud_llm and anthropic_key and anthropic_key != 'your_anthropic_key_here':
            try:
                self.cloud_llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0.7, api_key=anthropic_key)
                self.cloud_provider = "Anthropic"
                logger.info("✅ Anthropic Claude initialized (Cloud LLM)")
            except Exception as e:
                logger.warning(f"⚠️ Anthropic initialization failed: {e}")
        
        # ── Power LLM (NVIDIA Qwen3.5-397B) ─────────────────────────────
        try:
            nvidia_llm = create_nvidia_llm("qwen/qwen3.5-397b-a17b")
            if nvidia_llm:
                self.power_llm = nvidia_llm
                logger.info("⚡ NVIDIA Qwen3.5-397B initialized (Power LLM)")
            else:
                logger.info("💡 NVIDIA LLM: Add NVIDIA_API_KEY to .env to enable Qwen3.5-397B")
        except Exception as e:
            logger.warning(f"⚠️ NVIDIA LLM initialization failed: {e}")
        
        # ── Local LLM (Ollama) ────────────────────────────────────────────
        ollama_endpoint = os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434')
        try:
            from langchain_ollama import ChatOllama
            self.local_llm = ChatOllama(model="llama3.2", base_url=ollama_endpoint, temperature=0.7)
            logger.info("✅ Ollama (llama3.2) initialized (Local LLM)")
        except Exception as e:
            logger.warning(f"⚠️ Ollama initialization failed: {e}")
        
        # ── Status summary ────────────────────────────────────────────────
        if self.cloud_llm:
            logger.info(f"🌐 Cloud LLM ready: {self.cloud_provider}")
        if self.local_llm:
            logger.info("🏠 Local LLM ready: Ollama (llama3.2)")
        if self.power_llm:
            logger.info("⚡ Power LLM ready: NVIDIA Qwen3.5-397B")
        if not self.cloud_llm and not self.local_llm and not self.power_llm:
            logger.warning("⚠️ No LLM configured. Add API keys to .env file or install Ollama")
    
    def get_llm(self, llm_type: str = "cloud"):
        """
        Get LLM instance by tier.
        
        Tiers:
          'local'  → Ollama (fast responses, no internet)
          'cloud'  → Gemini / OpenAI (balanced)
          'power'  → NVIDIA Qwen3.5-397B (deep reasoning)
          'auto'   → Best available (power > cloud > local)
        """
        if llm_type == "local":
            return self.local_llm or self.cloud_llm or self.power_llm
        
        elif llm_type == "cloud":
            return self.cloud_llm or self.power_llm or self.local_llm
        
        elif llm_type == "power":
            if self.power_llm:
                return self.power_llm
            logger.warning("⚠️ Power LLM (NVIDIA) not available, falling back to cloud")
            return self.cloud_llm or self.local_llm
        
        elif llm_type == "auto":
            return self.power_llm or self.cloud_llm or self.local_llm
        
        return self.cloud_llm or self.local_llm or self.power_llm
    
    def get_model_by_name(self, model_name: str):
        """Get or lazily instantiate an LLM instance by its specific config name (e.g. ollama/llama3.2)"""
        name_lower = model_name.lower()
        
        # Check cache first
        if name_lower in self._models:
            return self._models[name_lower]
            
        # Try backwards compatibility for simple names
        if name_lower == "ollama":
            return self.local_llm or self.cloud_llm or self.power_llm
        elif name_lower == "gemini":
            return self.cloud_llm or self.power_llm or self.local_llm
        elif name_lower == "nvidia":
            return self.power_llm or self.cloud_llm or self.local_llm
            
        # Parse and lazily instantiate custom model requests
        llm = self._create_model(name_lower)
        if llm:
            logger.info(f"🚀 Lazily instantiated custom model: {name_lower}")
            self._models[name_lower] = llm
            return llm
            
        logger.warning(f"⚠️ Failed to instantiate requested model: {model_name}, falling back to auto")
        return self.get_llm("auto")
        
    def _create_model(self, model_string: str):
        """Parse provider/model and instantiate the exact LangChain model"""
        parts = model_string.split('/', 1)
        provider = parts[0]
        specific_model = parts[1] if len(parts) > 1 else None

        try:
            if provider == "ollama":
                model_name = specific_model or "llama3.2"
                ollama_endpoint = os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434')
                from langchain_ollama import ChatOllama
                return ChatOllama(model=model_name, base_url=ollama_endpoint, temperature=0.7)
                
            elif provider == "gemini":
                model_name = specific_model or "gemini-2.0-flash"
                google_key = os.getenv('GOOGLE_API_KEY')
                if google_key and google_key != 'your_google_key_here':
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    return ChatGoogleGenerativeAI(model=model_name, temperature=0.7, google_api_key=google_key)
                else:
                    logger.warning("Gemini API key missing")
                    
            elif provider == "openai":
                model_name = specific_model or "gpt-4-turbo-preview"
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key and openai_key != 'your_openai_key_here':
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI(model=model_name, temperature=0.7, api_key=openai_key)
                else:
                    logger.warning("OpenAI API key missing")
            
            elif provider == "anthropic":
                model_name = specific_model or "claude-3-sonnet-20240229"
                anthropic_key = os.getenv('ANTHROPIC_API_KEY')
                if anthropic_key and anthropic_key != 'your_anthropic_key_here':
                    from langchain_anthropic import ChatAnthropic
                    return ChatAnthropic(model=model_name, temperature=0.7, api_key=anthropic_key)
                else:
                    logger.warning("Anthropic API key missing")
                    
            elif provider == "nvidia":
                model_name = specific_model or "qwen/qwen3.5-397b-a17b"
                from .nvidia_llm_provider import create_nvidia_llm
                return create_nvidia_llm(model_name)
                
        except Exception as e:
            logger.error(f"Failed to create model {model_string}: {e}")
            
        return None
    
    def get_best_for_complexity(self, score: int):
        """
        Get best LLM based on complexity score and DEFAULT_LLM setting.
        
        If DEFAULT_LLM=nvidia → use NVIDIA for everything
        If DEFAULT_LLM=gemini  → use Gemini for everything
        Otherwise use tiered routing:
          0-3  → local/nvidia  (simple, fast)
          4-6  → cloud/gemini  (balanced)
          7-10 → power/nvidia  (complex reasoning)
        """
        default = os.getenv("DEFAULT_LLM", "auto").lower()
        
        # Override - use one model for everything
        if default == "nvidia":
            llm = self.get_llm("power")
            return llm, "nvidia"
        elif default == "gemini":
            llm = self.get_llm("cloud")
            return llm, "gemini"
        elif default == "ollama":
            llm = self.get_llm("local")
            return llm, "ollama"
        
        # Auto: smart 3-tier routing
        if score <= 3:
            return self.get_llm("local"), "local"
        elif score <= 6:
            return self.get_llm("cloud"), "cloud"
        else:
            return self.get_llm("power"), "power"

    
    async def query(self, prompt: str, llm_type: str = "cloud") -> str:
        """Query the appropriate LLM"""
        llm = self.get_llm(llm_type)
        if not llm:
            return "⚠️ No LLM available. Please configure API keys in .env file."
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"❌ LLM query failed: {e}")
            return f"Error: {str(e)}"

