"""Web-grounded seasonality and weather validator."""
import json
import os
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from tools.google_cse import GoogleCSE, SearchHit

try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_search_queries(profile: Dict, candidate: Dict, season: str) -> List[str]:
    """
    Build search queries for weather/seasonality information.
    
    Args:
        profile: Traveler profile
        candidate: Candidate destination
        season: Travel season/period
    
    Returns:
        List of search query strings
    """
    destination = candidate.get("name", "")
    queries = []
    
    # Query 1: General weather for destination and season
    queries.append(f"{destination} {season} weather climate")
    
    # Query 2: Tourist season/crowd level
    queries.append(f"{destination} {season} tourist season crowd level")
    
    # Query 3: Best time to visit
    queries.append(f"{destination} best time to visit {season}")
    
    return queries


@traceable(name="seasonality_weather_web_search")
def web_search_weather(
    cse_client: GoogleCSE,
    profile: Dict,
    candidate: Dict,
    season: str
) -> List[SearchHit]:
    """
    Perform web search for weather/seasonality information.
    
    Returns:
        List of search hits
    """
    queries = build_search_queries(profile, candidate, season)
    
    # Search all queries and combine results
    all_hits = []
    for query in queries:
        hits = cse_client.search_weather(query, num_results=3)
        all_hits.extend(hits)
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_hits = []
    for hit in all_hits:
        if hit.url not in seen_urls:
            seen_urls.add(hit.url)
            unique_hits.append(hit)
    
    return unique_hits[:5]  # Return top 5 unique results


def build_seasonality_weather_web_validator(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build web-grounded seasonality and weather validator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a seasonality analyst for travel recommendations. Evaluate the destination's weather, season, and crowd levels based on the provided web search results. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Travel period: {season}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Web search results:
{search_results}

Evaluate seasonality and weather based on the search results:
- Typical weather conditions for the travel period
- Temperature and climate comfort
- Rainfall/precipitation patterns
- Tourist crowd levels (high/medium/low season)
- Seasonal events or festivals
- Best/worst aspects of visiting during this period

IMPORTANT:
- Base your evaluation on the provided search results
- Cite specific information from the search results in your reasons
- If search results are insufficient, note it in assumptions
- Do NOT make up information not found in search results

Return JSON schema exactly:
{{
  "validator": "seasonality_weather",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail | unknown",
  "reasons": ["..."],
  "citations": [
    {{
      "title": "...",
      "url": "...",
      "snippet": "..."
    }}
  ],
  "assumptions": [
    "검색 결과 요약 기반",
    "실시간 데이터 아님"
  ],
  "questions_to_user": []
}}

Scoring:
- score: 0.0-1.0 (1.0 = perfect season, 0.0 = poor season)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4), "unknown" (insufficient data)
- citations: Include relevant search results that support your evaluation
""")
    ])
    
    return prompt | llm | parser


def run_seasonality_weather_web_validator(
    chain,
    cse_client: GoogleCSE,
    profile: Dict,
    candidate: Dict,
    candidate_id: str
) -> Dict:
    """
    Execute web-grounded seasonality and weather validator.
    
    Returns validator result with citations and graceful error handling.
    """
    try:
        season = profile.get("constraints", {}).get("season", "알 수 없음")
        
        # Step 1: Web search
        search_hits = web_search_weather(cse_client, profile, candidate, season)
        
        # Step 2: Format search results for LLM
        search_results_text = ""
        if search_hits:
            for i, hit in enumerate(search_hits, 1):
                search_results_text += f"\n[{i}] {hit.title}\nURL: {hit.url}\n{hit.snippet}\n"
        else:
            search_results_text = "검색 결과가 없습니다."
        
        # Step 3: LLM judge
        result = chain.invoke({
            "profile": safe_json(profile),
            "season": season,
            "candidate": safe_json(candidate),
            "candidate_id": candidate_id,
            "search_results": search_results_text
        })
        
        # Step 4: Validate and add citations
        if "validator" not in result:
            result["validator"] = "seasonality_weather"
        if "candidate_id" not in result:
            result["candidate_id"] = candidate_id
        if "score" not in result:
            result["score"] = 0.0
        if "verdict" not in result:
            result["verdict"] = "unknown"
        if "reasons" not in result:
            result["reasons"] = ["검증 실패"]
        if "assumptions" not in result:
            result["assumptions"] = ["검색 결과 요약 기반", "실시간 데이터 아님"]
        if "questions_to_user" not in result:
            result["questions_to_user"] = []
        
        # Ensure citations are included
        if "citations" not in result:
            # Add search hits as citations
            result["citations"] = [
                {
                    "title": hit.title,
                    "url": hit.url,
                    "snippet": hit.snippet
                }
                for hit in search_hits[:3]  # Top 3 citations
            ]
        elif not result.get("citations"):
            # If citations is empty, add search hits
            result["citations"] = [
                {
                    "title": hit.title,
                    "url": hit.url,
                    "snippet": hit.snippet
                }
                for hit in search_hits[:3]
            ]
        
        # Add search metadata
        result["_search_queries"] = build_search_queries(profile, candidate, season)
        result["_num_search_hits"] = len(search_hits)
        
        return result
        
    except Exception as e:
        # Graceful error handling
        return {
            "validator": "seasonality_weather",
            "candidate_id": candidate_id,
            "score": 0.0,
            "verdict": "unknown",
            "reasons": [f"검증 실패: {str(e)}"],
            "citations": [],
            "assumptions": ["검색 실패", "실시간 데이터 아님"],
            "questions_to_user": [],
            "_search_queries": [],
            "_num_search_hits": 0
        }