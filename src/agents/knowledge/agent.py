"""
Knowledge Agent
Specialized agent for filesystem interaction and document understanding
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from ..base_agent import BaseAgent
from ...tools.file_reader import read_file_content
from ...tools.file_search import list_files, search_in_files
from ...core.settings import settings

class KnowledgeAgent(BaseAgent):
    """
    Agent that can read files, search directory structures, 
    and answer questions about local documents.
    """
    
    def __init__(self, llm_orchestrator):
        super().__init__(
            "Knowledge Agent",
            "Reads and analyzes local files. Can view project code, read text/markdown/PDF files, summarize local documents, and perform keyword searches in the local codebase or directories.",
            llm_orchestrator
        )
        
        # Keywords that indicate knowledge/file-related queries
        self.knowledge_keywords = [
            'read', 'file', 'content', 'summarize', 'search',
            'find', 'look for', 'directory', 'folder', 'files',
            'pdf', 'document', 'inside'
        ]
        
    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Detect file/knowledge-related queries
        """
        query_lower = query.lower()
        
        # Check for keywords
        matches = sum(1 for kw in self.knowledge_keywords if kw in query_lower)
        confidence = min(matches * 0.25, 0.9)
        
        # Strong signals
        strong_signals = [
            'read the file', 'what is in', 'summarize', 
            'search for', 'list files'
        ]
        if any(s in query_lower for s in strong_signals):
            confidence = max(confidence, 0.85)
            
        return confidence
        
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process the query using LLM and file tools
        """
        query_lower = query.lower()
        
        # 1. Handle "list files" or "what files are here"
        if any(w in query_lower for w in ['list files', 'show files', 'what files', 'files in this folder']):
            files = list_files()
            if not files:
                return "The directory seems to be empty or I couldn't access it."
            
            file_list = "\n".join([f"- {f}" for f in files[:20]]) # Limit display
            if len(files) > 20:
                file_list += f"\n...and {len(files)-20} more."
                
            return await self._summarize_file("current directory", f"Here are the files in the current directory:\n{file_list}", query)

        # 2. Handle "search for X"
        if 'search for' in query_lower:
            keyword = query_lower.split('search for')[-1].strip().strip('"')
            results = search_in_files(keyword)
            if not results:
                return f"I couldn't find any occurrences of '{keyword}' in the text/code files."
            
            # Format results for LLM
            raw_data = "Search results:\n"
            for r in results[:10]:
                raw_data += f"File: {r['file']}, Line {r['line']}: {r['content']}\n"
                
            return await self._summarize_file("search results", raw_data, query)

        # 3. Handle "read file X" or "summarize X"
        return await self._llm_decide_and_read(query)

    async def _extract_search_params(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Use LLM to extract the exact search parameters (filename pattern or text snippet) from a query
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        if not llm:
            return None
        
        prompt = f"""You are an expert at extracting search parameters from user queries.
The user wants to search for files or content within files.
Extract the following information from the user's query:
- `filename_pattern`: A glob-style pattern for filenames to search (e.g., "*.py", "report.md", "src/**"). If not specified, use "**/*".
- `text_snippet`: A specific text string or keyword to search for within the files. If not specified, use null.

Respond with a JSON object containing these two keys.

User query: "{query}"

Example:
User query: "find all python files containing 'async def'"
Response: {{"filename_pattern": "*.py", "text_snippet": "async def"}}

User query: "search for 'TODO' in the documentation folder"
Response: {{"filename_pattern": "docs/**/*", "text_snippet": "TODO"}}

User query: "list all markdown files"
Response: {{"filename_pattern": "*.md", "text_snippet": null}}

User query: "what files are in the src directory?"
Response: {{"filename_pattern": "src/**/*", "text_snippet": null}}

JSON Response:"""
        try:
            import json
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)
            content = response.content.strip().strip('`').replace('json\n', '')
            return json.loads(content)
        except Exception as e:
            self.logger.warning(f"Failed to extract search params: {e}")
            return None

    async def _llm_decide_and_read(self, query: str) -> str:
        """
        Use LLM to identify which file the user wants to read or search,
        then execute the tool and explain.
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        if not llm:
            return "I'm unable to access the LLM to process this request."
        
        # Step 1: Identify the file path/action
        identify_prompt = f"""You are a filesystem assistant.
The user said: "{query}"

If the user wants to read or summarize a file, identify the filename.
Reply with ONLY the filename or path. 
If you can't identify a filename, reply with "NONE".

Examples:
- "read SOUL.md" → SOUL.md
- "summarize the src/core/engine.py file" → src/core/engine.py
- "what is in requirements.txt" → requirements.txt

Filename:"""
        
        try:
            filename_resp = await asyncio.wait_for(llm.ainvoke(identify_prompt), timeout=timeout)
            filename = filename_resp.content.strip().strip('"').strip("'")
            
            if filename == "NONE":
                return "I'm not exactly sure which file you'd like me to look at. Could you specify the filename?"
            
            self.logger.info(f"📁 Reading file: {filename}")
            
            # Step 2: Read the file
            result = read_file_content(filename)
            
            if not result['success']:
                return f"I had trouble reading that file: {result['error']}"
            
            # Step 3: Explain naturally
            return await self._summarize_file(filename, result['content'], query)
            
        except asyncio.TimeoutError:
            return "The LLM took too long to identify the file. Please try again."
        except Exception as e:
            self.logger.error(f"Knowledge Agent error: {e}")
            return "Sorry, I had trouble processing that file-related request."

    async def _summarize_file(self, filename: str, content: str, query: str) -> str:
        """
        Use LLM to answer questions about a file's content
        """
        model_name = settings.get_agent_llm(self.name)
        llm = self.llm_orchestrator.get_model_by_name(model_name)
        timeout = settings.local_timeout if model_name == "ollama" else settings.cloud_timeout
        if not llm:
            return f"I found the following content for '{filename}', but I'm having trouble summarizing it: \n\n{content[:500]}..."
        
        prompt = f"""You are Cipher, a helpful AI assistant.
The user asked: "{query}"

Here is the data/content from the filesystem (from file: {filename}):
{content[:4000]}

Please provide a helpful, natural response. 
If it's a file summary, be concise but informative.
If it's a search result, point out where the keyword was found.
Speak directly to the user. No markdown headers.

Response:"""
        
        try:
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)
            return response.content.strip()
        except asyncio.TimeoutError:
            return f"Timeout while analyzing {filename}."
        except Exception as e:
            self.logger.error(f"Failed to summarize file: {e}")
            return f"Error analyzing '{filename}'"

    def get_tools(self) -> List:
        return [] # Tools are internal to this agent
