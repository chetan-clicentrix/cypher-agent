"""
NVIDIA LLM Provider
Integrates NVIDIA's hosted LLM API (Qwen, Llama, etc.)
Compatible with LangChain via OpenAI-compatible interface
"""

import os
import requests
import json
from typing import Any, Iterator, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from dotenv import load_dotenv

load_dotenv()


class NvidiaLLM(BaseChatModel):
    """
    LangChain-compatible wrapper for NVIDIA's hosted LLM API.
    Supports streaming and non-streaming responses.
    
    Models available:
    - qwen/qwen3.5-397b-a17b    (flagship, very capable)
    - meta/llama-3.1-70b-instruct
    - mistralai/mixtral-8x7b-instruct
    """
    
    model: str = "qwen/qwen3.5-397b-a17b"
    api_key: str = ""
    api_base: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    temperature: float = 0.70
    top_p: float = 0.80
    top_k: int = 20
    max_tokens: int = 4096
    stream_enabled: bool = False  # Use False for LangChain compatibility
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.api_key:
            self.api_key = os.getenv("NVIDIA_API_KEY", "")
    
    @property
    def _llm_type(self) -> str:
        return "nvidia"
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to NVIDIA API format"""
        converted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            else:
                converted.append({"role": "user", "content": str(msg.content)})
        return converted
    
    def _call_api(self, messages: List[dict]) -> str:
        """Call NVIDIA API and return the response text"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        
        response = requests.post(
            self.api_base,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _call_api_streaming(self, messages: List[dict]) -> str:
        """Call NVIDIA API with streaming and collect full response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        
        full_response = ""
        
        with requests.post(
            self.api_base,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                        except json.JSONDecodeError:
                            pass
        
        return full_response
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response from the NVIDIA LLM"""
        converted = self._convert_messages(messages)
        
        try:
            if self.stream_enabled:
                content = self._call_api_streaming(converted)
            else:
                content = self._call_api(converted)
            
            message = AIMessage(content=content)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
            
        except Exception as e:
            raise ValueError(f"NVIDIA API error: {e}")
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate (runs sync in executor for compatibility)"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._generate(messages, stop, **kwargs)
        )


def create_nvidia_llm(model: str = "qwen/qwen3.5-397b-a17b") -> Optional[NvidiaLLM]:
    """Factory function to create NVIDIA LLM instance"""
    api_key = os.getenv("NVIDIA_API_KEY", "")
    
    if not api_key or api_key == "your_nvidia_api_key_here":
        return None
    
    return NvidiaLLM(
        model=model,
        api_key=api_key,
        temperature=0.70,
        top_p=0.80,
        max_tokens=4096
    )
