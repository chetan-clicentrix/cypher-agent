"""
System Agent Tools
Wraps system monitoring and terminal execution tools for the System Agent
"""

from typing import List
from langchain_core.tools import tool
from ...tools.system_monitor import SystemMonitor
from ...tools.terminal import TerminalExecutor

# Initialize shared instances
system_monitor = SystemMonitor()
terminal = TerminalExecutor()


@tool
def get_system_status(query: str = "") -> str:
    """
    Get current system resource usage including CPU, RAM, and Disk.
    Use when user asks about system performance, resource usage, or 'what's using my RAM/CPU'.
    """
    return system_monitor.get_system_summary()


@tool
def get_top_processes(query: str = "memory") -> str:
    """
    Get top 5 processes by CPU or RAM usage.
    Use when user asks 'what's using my memory', 'top processes', 'which app is using CPU', etc.
    Input should be 'cpu' or 'memory' to specify sort order.
    """
    # Parse query to determine sort method
    sort_by = "memory"  # default
    if "cpu" in query.lower():
        sort_by = "cpu"
    
    procs = system_monitor.get_top_processes(limit=5, sort_by=sort_by)
    
    result = f"**Top 5 Processes by {sort_by.upper()}:**\n"
    for proc in procs:
        result += f"- {proc['name']} (PID: {proc['pid']}): CPU {proc['cpu_percent']}%, RAM {proc['memory_percent']}%\n"
    
    return result


@tool
def execute_command(command: str) -> str:
    """
    Execute a terminal command (Windows CMD/PowerShell).
    Use when user asks to 'run', 'execute', 'list files', 'check network', or specific commands.
    Example inputs: 'dir', 'ping google.com', 'ipconfig'.
    """
    result = terminal.execute(command)
    
    if result['success']:
        output = result['output']
        if not output:
            return "Command executed successfully (no output)."
        return f"Output:\n{output}"
    else:
        return f"Error executing command:\n{result['error']}"


def get_system_tools() -> List:
    """Return list of all system tools"""
    return [
        get_system_status,
        get_top_processes,
        execute_command
    ]
