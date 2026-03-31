"""
System Agent
Handles system monitoring, process management, and terminal commands
Uses LLM to understand natural language intent → maps to actual commands
"""
import os
import asyncio
from typing import List, Optional, Dict, Any
from ..base_agent import BaseAgent
from .tools import get_system_tools
from ...tools.terminal import TerminalExecutor
from ...core.settings import settings


class SystemAgent(BaseAgent):
    """
    Intelligent system agent that understands natural language.
    
    Examples:
    - "what is my IP?" → runs ipconfig, extracts IP
    - "which directory am I in?" → runs cd, speaks the path
    - "navigate to D drive" → changes directory
    - "what's using my RAM?" → top processes
    - "open notepad" → runs notepad
    """
    
    def __init__(self, llm_orchestrator):
        super().__init__(
            "System Agent", 
            "Interacts with the local operating system. Executes terminal commands, checks CPU/RAM status, launches local apps, gets IP addresses, and navigates the local file system.",
            llm_orchestrator
        )
        self.terminal = TerminalExecutor()
        self.tools = get_system_tools()
        self.tool_dict = {tool.name: tool for tool in self.tools}
        
        # Natural language intent patterns
        self.system_keywords = [
            'ram', 'memory', 'cpu', 'disk', 'system', 'status', 
            'process', 'using', 'top', 'resource', 'performance',
            'ip', 'network', 'internet', 'connection', 'wifi',
            'directory', 'folder', 'navigate', 'path', 'where am i',
            'open', 'launch', 'run', 'execute', 'command',
            'file', 'list', 'show', 'ping', 'speed'
        ]
    
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        query_lower = query.lower()
        matches = sum(1 for kw in self.system_keywords if kw in query_lower)
        confidence = min(matches * 0.25, 0.9)
        
        # Strong signals - made them more specific to avoid false positives
        strong = ['run command', 'execute command', 'open app', 'launch app', 'navigate to', 
                  'ipconfig', 'ping ', 'dir ', 'ip address', 'current directory']
        if any(s in query_lower for s in strong):
            confidence = max(confidence, 0.85)
        
        return confidence
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Use LLM to decide what command to run, run it, then explain naturally.
        """
        query_lower = query.lower()
        
        # 1. System status (CPU/RAM/Disk)
        if any(w in query_lower for w in ['cpu', 'ram', 'disk', 'system status', 'system info', 'performance', 'memory usage']):
            raw = self.tool_dict['get_system_status'].func(query)
            return await self._explain_naturally(query, raw)
        
        # 2. Top processes
        if any(w in query_lower for w in ['process', 'what is using', "what's using", 'top app', 'running app']):
            raw = self.tool_dict['get_top_processes'].func(query)
            return await self._explain_naturally(query, raw)
        
        # 3. Let LLM decide which Windows command to run for everything else
        return await self._llm_decide_and_run(query)
    
    async def _llm_decide_and_run(self, query: str) -> str:
        """
        Ask LLM to pick the right Windows command for the user's natural language request,
        run it, then explain the result conversationally.
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        if not llm:
            return "LLM not available to process this command."
        
        # Step 1: Ask LLM which command to run
        command_prompt = f"""You are a Windows command assistant.
The user said: "{query}"

Reply with ONLY the Windows CMD/PowerShell command to run — nothing else, no explanation.

Examples:
- "what is my IP" → ipconfig | findstr "IPv4"
- "which directory am I in" → cd
- "navigate to D drive" → cd /d D:\\
- "list files" → dir
- "open notepad" → notepad
- "ping google" → ping google.com -n 2
- "current user" → whoami
- "disk space" → wmic logicaldisk get size,freespace,caption

Command:"""
        
        try:
            cmd_response = await asyncio.wait_for(llm.ainvoke(command_prompt), timeout=timeout)
            command = cmd_response.content.strip().strip('`').strip()
            
            # Safety: block dangerous commands
            blocked = ['format', 'del /f /s', 'rmdir /s /q', 'rd /s', 'reg delete', 
                      'shutdown', 'taskkill /f /im', 'cipher /w', 'sfc /scannow']
            if any(b in command.lower() for b in blocked):
                return "I can't run that command as it could be dangerous to your system."
            
            self.logger.info(f"🖥️ Running: {command}")
            
            # Step 2: Execute the command
            result = self.terminal.execute(command)
            
            if not result['success'] and not result['output']:
                return f"I tried running that but got an error: {result['error']}"
            
            output = result['output'] or result['error']
            
            # Step 3: Explain the output naturally
            return await self._explain_naturally(query, output)
            
        except Exception as e:
            self.logger.error(f"Command error: {e}")
            return "Sorry, I had trouble running that command."
    
    async def _explain_naturally(self, query: str, raw_output: str) -> str:
        """
        Ask LLM to explain raw command output in natural conversational language.
        No markdown, no bullet points — just speak like a human.
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        if not llm:
            return self._strip_markdown(raw_output)
        
        try:
            prompt = f"""You are Cipher, a friendly AI assistant talking out loud.

The user asked: "{query}"
Here is the raw data from the system: 
{raw_output[:800]}

Reply in 1-2 short natural sentences as if speaking to a friend.
Do NOT use markdown, asterisks, bullet points, or dashes.
Be direct and give only the key information.

Examples of good responses:
- "Your IP address is 192.168.1.5"
- "You're currently in the D colon backslash Cipher folder"  
- "Your RAM is about 6 gigs used out of 15"

Your response:"""
            
            response = await llm.ainvoke(prompt)
            return response.content.strip()
        except:
            return self._strip_markdown(raw_output[:300])
    
    def _strip_markdown(self, text: str) -> str:
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'^[-•]\s+', '', text, flags=re.MULTILINE)
        return text.strip()
    
    def get_tools(self) -> List:
        return self.tools
