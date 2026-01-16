"""Aggregator for validator results."""
import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

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


def build_aggregator_chain(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build aggregator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel recommendation aggregator. Synthesize validator results to create a ranked list and final recommendation. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Candidates:
{candidates}

Validator results:
{validators_results}

Task:
1. For each candidate, aggregate all validator scores and verdicts
2. Calculate a total_score (weighted average or your method)
3. Rank candidates by total_score
4. Select the top candidate as final_choice
5. Provide a second choice (runner-up) in ranked_candidates

For each ranked candidate, include:
- total_score: 0.0-1.0
- summary: Why this candidate ranks at this position (1-2 sentences)
- strengths: Key positive points from validators
- risks: Key concerns or warnings from validators
- watchouts: Important things to be aware of

For final_choice, include:
- why: Top 2-3 reasons this is the best choice
- what_to_confirm: Questions or confirmations needed before finalizing

IMPORTANT:
- All validator results are based on general knowledge, NOT real-time data
- Include this disclaimer in the output

Return JSON schema exactly:
{{
  "ranked_candidates": [
    {{
      "candidate_id": "",
      "name": "",
      "total_score": 0.0,
      "summary": "",
      "strengths": ["..."],
      "risks": ["..."],
      "watchouts": ["..."]
    }}
  ],
  "final_choice": {{
    "candidate_id": "",
    "name": "",
    "why": ["..."],
    "what_to_confirm": ["..."]
  }},
  "disclaimer": "실시간 데이터가 아님을 명시"
}}
""")
    ])
    
    return prompt | llm | parser


def run_aggregator(
    chain,
    profile: Dict,
    candidates: List[Dict],
    validators_results: List[Dict]
) -> Dict:
    """
    Execute aggregator to synthesize validator results.
    
    Returns aggregated result with graceful error handling.
    """
    try:
        result = chain.invoke({
            "profile": safe_json(profile),
            "candidates": safe_json(candidates),
            "validators_results": safe_json(validators_results)
        })
        
        # Validate required fields
        if "ranked_candidates" not in result:
            result["ranked_candidates"] = []
        if "final_choice" not in result:
            result["final_choice"] = {}
        if "disclaimer" not in result:
            result["disclaimer"] = "실시간 데이터가 아님을 명시"
            
        return result
    except Exception as e:
        # Graceful error handling - create basic structure
        candidate_ids = [f"C{i+1}" for i in range(len(candidates))]
        candidate_names = [c.get("name", f"Candidate {i+1}") for i, c in enumerate(candidates)]
        
        return {
            "ranked_candidates": [
                {
                    "candidate_id": candidate_ids[0] if candidate_ids else "C1",
                    "name": candidate_names[0] if candidate_names else "Unknown",
                    "total_score": 0.5,
                    "summary": f"Aggregation failed: {str(e)}",
                    "strengths": [],
                    "risks": ["집계 실패"],
                    "watchouts": []
                }
            ],
            "final_choice": {
                "candidate_id": candidate_ids[0] if candidate_ids else "C1",
                "name": candidate_names[0] if candidate_names else "Unknown",
                "why": ["집계 실패로 인한 기본 선택"],
                "what_to_confirm": []
            },
            "disclaimer": "실시간 데이터가 아님을 명시"
        }