"""Web-grounded safety risk validator."""
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


def build_search_queries(profile: Dict, candidate: Dict) -> List[str]:
    """
    Build search queries for safety information.
    
    Args:
        profile: Traveler profile
        candidate: Candidate destination
    
    Returns:
        List of search query strings
    """
    destination = candidate.get("name", "")
    queries = []
    
    # Query 1: General safety for destination
    queries.append(f"{destination} safety travel advisory")
    
    # Query 2: Crime rate and security
    queries.append(f"{destination} crime rate tourist safety")
    
    # Query 3: Solo traveler safety (if applicable)
    traveler_type = profile.get("traveler_type", "")
    if "혼자" in traveler_type or "solo" in traveler_type.lower():
        queries.append(f"{destination} solo traveler safety")
    else:
        queries.append(f"{destination} tourist safety precautions")
    
    return queries


@traceable(name="safety_risk_web_search")
def web_search_safety(
    cse_client: GoogleCSE,
    profile: Dict,
    candidate: Dict
) -> List[SearchHit]:
    """
    Perform web search for safety information.
    
    Returns:
        List of search hits
    """
    queries = build_search_queries(profile, candidate)
    
    # Search all queries and combine results
    all_hits = []
    for query in queries:
        # Use safety PSE if available, otherwise fallback to weather PSE
        try:
            if cse_client.cx_safety:
                hits = cse_client.search_safety(query, num_results=3)
            else:
                # Fallback to weather PSE if safety PSE not configured
                hits = cse_client.search_weather(query, num_results=3)
        except (ValueError, AttributeError):
            # If search_safety method doesn't exist, use weather PSE
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


def build_safety_risk_web_validator(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build web-grounded safety risk validator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a safety analyst for travel recommendations. Evaluate general safety and risk factors for the destination based on the provided web search results. Provide balanced, practical advice. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Web search results:
{search_results}

Evaluate safety risk based on the search results:
- General crime rates (petty theft, pickpocketing)
- Tourist-targeted scams
- Nighttime safety
- Solo traveler safety (if applicable)
- Overall safety reputation

IMPORTANT CONSTRAINTS:
- Base your evaluation on the provided search results
- Cite specific information from the search results in your reasons
- Do NOT create excessive fear or panic
- Focus on general precautions, not extreme warnings
- Consider typical tourist experiences
- Provide balanced, practical advice
- If search results are insufficient, note it in assumptions
- Do NOT make up information not found in search results

Return JSON schema exactly:
{{
  "validator": "safety_risk",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
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
- score: 0.0-1.0 (1.0 = very safe, 0.0 = high risk)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
- citations: Include relevant search results that support your evaluation
""")
    ])
    
    return prompt | llm | parser


def run_safety_risk_web_validator(
    chain,
    cse_client: GoogleCSE,
    profile: Dict,
    candidate: Dict,
    candidate_id: str
) -> Dict:
    """
    Execute web-grounded safety risk validator.
    
    Returns validator result with citations and graceful error handling.
    """
    try:
        # Step 1: Web search
        search_hits = web_search_safety(cse_client, profile, candidate)
        
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
            "candidate": safe_json(candidate),
            "candidate_id": candidate_id,
            "search_results": search_results_text
        })
        
        # Step 4: Validate and add citations
        if "validator" not in result:
            result["validator"] = "safety_risk"
        if "candidate_id" not in result:
            result["candidate_id"] = candidate_id
        if "score" not in result:
            result["score"] = 0.0
        if "verdict" not in result:
            result["verdict"] = "fail"
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
        result["_search_queries"] = build_search_queries(profile, candidate)
        result["_num_search_hits"] = len(search_hits)
        
        return result
        
    except Exception as e:
        # Graceful error handling
        return {
            "validator": "safety_risk",
            "candidate_id": candidate_id,
            "score": 0.0,
            "verdict": "fail",
            "reasons": [f"검증 실패: {str(e)}"],
            "citations": [],
            "assumptions": ["검색 실패", "실시간 데이터 아님"],
            "questions_to_user": [],
            "_search_queries": [],
            "_num_search_hits": 0
        }
