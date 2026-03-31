"""
Web Search Tool
Wrapper for DuckDuckGo Search (Free & No Key Required)
"""

from ddgs import DDGS
from typing import List, Dict, Any
import logging
import os

# Suppress the noisy primp logger that ddgs uses
logging.getLogger("primp").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search the web using DuckDuckGo.
    Returns a list of dicts: {'title': ..., 'href': ..., 'body': ...}
    """
    results = []
    try:
        with DDGS() as ddgs:
            # text search
            ddgs_gen = ddgs.text(query, max_results=max_results)
            for r in ddgs_gen:
                results.append(r)
                
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return []

def search_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search specifically for news articles using DuckDuckGo.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # news search
            ddgs_gen = ddgs.news(query, max_results=max_results)
            for r in ddgs_gen:
                results.append(r)
                
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo news error: {e}")
        return []

def search_tavily(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily AI Search API.
    Returns a list of dicts: {'title': ..., 'href': ..., 'body': ...}
    """
    try:
        from tavily import TavilyClient
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.error("TAVILY_API_KEY not found in environment.")
            return []
            
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results
        )
        
        # Format results to match the existing DuckDuckGo structure
        # so the ResearchAgent doesn't need to change its parsing logic
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "href": r.get("url", ""),
                "body": r.get("content", "")
            })
            
        return results
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []

if __name__ == "__main__":
    # Test
    print("Searching for Bitcoin price...")
    res = search_web("Bitcoin price today")
    for r in res:
        print(f"- {r['title']}: {r['body'][:100]}...")
