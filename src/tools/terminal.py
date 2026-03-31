"""
Terminal Executor Tool
Allows executing system commands securely
"""

import subprocess
import os
from typing import Dict, Union
from ..utils.logger import setup_logger

logger = setup_logger()

class TerminalExecutor:
    """Executes terminal commands"""
    
    def __init__(self, working_dir: str = None):
        self.working_dir = working_dir or os.getcwd()
    
    def execute(self, command: str) -> Dict[str, Union[str, int, bool]]:
        """
        Execute a shell command
        
        Args:
            command: Command string to execute
            
        Returns:
            Dict containing output, error, return_code, and success status
        """
        try:
            logger.info(f"💻 Executing command: {command}")
            
            # Run command
            process = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout safety
            )
            
            return {
                "output": process.stdout.strip(),
                "error": process.stderr.strip(),
                "return_code": process.returncode,
                "success": process.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "output": "",
                "error": "Command timed out after 60 seconds",
                "return_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "output": "",
                "error": str(e),
                "return_code": -1,
                "success": False
            }
        
    def change_directory(self, path: str) -> Dict[str, Union[str, bool]]:
        """Change current working directory"""
        try:
            os.chdir(path)
            self.working_dir = os.getcwd()
            return {
                "output": f"Changed directory to: {self.working_dir}",
                "success": True
            }
        except Exception as e:
            return {
                "output": f"Failed to change directory: {e}",
                "success": False
            }
