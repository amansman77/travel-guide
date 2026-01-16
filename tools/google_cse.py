"""Google Custom Search Engine (CSE) client for web-grounded validation."""
import os
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SearchHit:
    """Standard search result structure."""
    title: str
    url: str
    snippet: str
    display_url: Optional[str] = None


class GoogleCSE:
    """
    Google Custom Search Engine client.
    Used for retrieving web information from trusted domains.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cx_weather: Optional[str] = None,
        cx_safety: Optional[str] = None
    ):
        """
        Initialize Google CSE client.
        
        Args:
            api_key: Google CSE API key (or from GOOGLE_CSE_API_KEY env)
            cx_weather: Weather PSE ID (or from GOOGLE_CSE_CX_WEATHER env)
            cx_safety: Safety PSE ID (or from GOOGLE_CSE_CX_SAFETY env)
        """
        self.api_key = api_key or os.getenv("GOOGLE_CSE_API_KEY")
        self.cx_weather = cx_weather or os.getenv("GOOGLE_CSE_CX_WEATHER")
        self.cx_safety = cx_safety or os.getenv("GOOGLE_CSE_CX_SAFETY")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        if not self.api_key:
            raise ValueError("GOOGLE_CSE_API_KEY is required")
    
    def search(
        self,
        query: str,
        cx: Optional[str] = None,
        num_results: int = 5,
        safe_search: str = "active"
    ) -> List[SearchHit]:
        """
        Perform web search using Google CSE.
        
        Args:
            query: Search query string
            cx: Custom Search Engine ID (if None, uses default)
            num_results: Number of results to return (max 10)
            safe_search: Safe search level (active, off)
        
        Returns:
            List of SearchHit objects
        """
        if not cx:
            raise ValueError("Custom Search Engine ID (cx) is required")
        
        params = {
            "key": self.api_key,
            "cx": cx,
            "q": query,
            "num": min(num_results, 10),  # Google CSE max is 10
            "safe": safe_search
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            hits = []
            
            for item in data.get("items", [])[:num_results]:
                hit = SearchHit(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    display_url=item.get("displayLink", "")
                )
                hits.append(hit)
            
            return hits
            
        except requests.exceptions.RequestException as e:
            # Graceful error handling
            return []
        except (KeyError, ValueError) as e:
            # JSON parsing error
            return []
    
    def search_weather(
        self,
        query: str,
        num_results: int = 5
    ) -> List[SearchHit]:
        """
        Search weather-related information using weather PSE.
        
        Args:
            query: Search query
            num_results: Number of results
        
        Returns:
            List of SearchHit objects
        """
        if not self.cx_weather:
            raise ValueError("GOOGLE_CSE_CX_WEATHER is required for weather search")
        
        return self.search(query, cx=self.cx_weather, num_results=num_results)
    
    def search_safety(
        self,
        query: str,
        num_results: int = 5
    ) -> List[SearchHit]:
        """
        Search safety-related information using safety PSE.
        
        Args:
            query: Search query
            num_results: Number of results
        
        Returns:
            List of SearchHit objects
        """
        if not self.cx_safety:
            raise ValueError("GOOGLE_CSE_CX_SAFETY is required for safety search")
        
        return self.search(query, cx=self.cx_safety, num_results=num_results)