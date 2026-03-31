"""
File Reader Tool
Safely reads content from local files (text, code, PDF)
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import pypdf

def read_file_content(file_path: str, max_chars: int = 10000) -> Dict[str, Any]:
    """
    Read content from a file safely.
    Supports text-based files and PDFs.
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"success": False, "error": "File not found"}
    
    if not path.is_file():
        return {"success": False, "error": "Not a file"}
    
    # Check extension
    ext = path.suffix.lower()
    
    try:
        if ext == '.pdf':
            return _read_pdf(path, max_chars)
        else:
            # Assume text for other extensions
            return _read_text(path, max_chars)
    except Exception as e:
        return {"success": False, "error": str(e)}

def _read_text(path: Path, max_chars: int) -> Dict[str, Any]:
    """Read text files"""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(max_chars)
            is_truncated = f.read(1) != ''
            
        return {
            "success": True,
            "content": content,
            "truncated": is_truncated,
            "type": "text",
            "size": path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to read text file: {e}"}

def _read_pdf(path: Path, max_chars: int) -> Dict[str, Any]:
    """Read PDF files using pypdf"""
    try:
        reader = pypdf.PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            if len(text) > max_chars:
                text = text[:max_chars]
                break
        
        return {
            "success": True,
            "content": text,
            "truncated": len(text) >= max_chars,
            "type": "pdf",
            "pages": len(reader.pages)
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to read PDF: {e}"}
