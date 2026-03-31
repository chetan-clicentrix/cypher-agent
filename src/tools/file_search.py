"""
File Search Tool
Lists files and searches for keywords within files
"""

import os
from pathlib import Path
from typing import List, Dict, Any

def list_files(directory: str = ".", pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    List files in a directory matching a pattern.
    """
    path = Path(directory)
    if not path.exists():
        return []
    
    if recursive:
        files = path.rglob(pattern)
    else:
        files = path.glob(pattern)
        
    return [str(f.relative_to(path)) for f in files if f.is_file()]

def search_in_files(keyword: str, directory: str = ".", extensions: List[str] = None) -> List[Dict[str, Any]]:
    """
    Search for a keyword inside files in a directory.
    """
    path = Path(directory)
    results = []
    
    if extensions is None:
        extensions = ['.txt', '.md', '.py', '.js', '.json', '.c', '.cpp', '.h']
        
    for root, _, files in os.walk(path):
        # Skip hidden directories like .git, venv
        if any(part.startswith('.') or part == 'venv' for part in Path(root).parts):
            continue
            
        for file in files:
            file_path = Path(root) / file
            if extensions and file_path.suffix.lower() not in extensions:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            results.append({
                                "file": str(file_path.relative_to(path)),
                                "line": i,
                                "content": line.strip()
                            })
                            if len(results) > 50:  # Safety limit
                                return results
            except Exception:
                continue
                
    return results
