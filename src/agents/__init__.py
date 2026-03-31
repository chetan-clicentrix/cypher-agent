"""
Multi-Agent System for Cipher AI Assistant
Routes queries to specialized agents based on intent
"""

from .base_agent import BaseAgent
from .agent_router import AgentRouter

__all__ = ["BaseAgent", "AgentRouter"]
