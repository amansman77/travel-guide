"""Seasonality and weather validator."""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_seasonality_weather_validator(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build seasonality and weather validator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a seasonality analyst for travel recommendations. Evaluate the destination's weather, season, and crowd levels for the specified travel period. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Travel period: {season}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Evaluate seasonality and weather considering:
- Typical weather conditions for the travel period
- Temperature and climate comfort
- Rainfall/precipitation patterns
- Tourist crowd levels (high/medium/low season)
- Seasonal events or festivals
- Best/worst aspects of visiting during this period

IMPORTANT:
- Use general seasonal patterns, NOT real-time weather data
- Consider typical conditions for the month/season
- Note any seasonal advantages or disadvantages

Return JSON schema exactly:
{{
  "validator": "seasonality_weather",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": []
}}

Scoring:
- score: 0.0-1.0 (1.0 = perfect season, 0.0 = poor season)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
""")
    ])
    
    return prompt | llm | parser


def run_seasonality_weather_validator(chain, profile: dict, candidate: dict, candidate_id: str) -> dict:
    """
    Execute seasonality and weather validator.
    
    Returns validator result with graceful error handling.
    """
    try:
        season = profile.get("constraints", {}).get("season", "알 수 없음")
        result = chain.invoke({
            "profile": safe_json(profile),
            "season": season,
            "candidate": safe_json(candidate),
            "candidate_id": candidate_id
        })
        
        # Validate required fields
        if "validator" not in result:
            result["validator"] = "seasonality_weather"
        if "candidate_id" not in result:
            result["candidate_id"] = candidate_id
        if "score" not in result:
            result["score"] = 0.0
        if "verdict" not in result:
            result["verdict"] = "fail"
        if "reasons" not in result:
            result["reasons"] = ["검증 실패"]
        if "assumptions" not in result:
            result["assumptions"] = ["실시간 데이터 아님"]
        if "questions_to_user" not in result:
            result["questions_to_user"] = []
            
        return result
    except Exception as e:
        # Graceful error handling
        return {
            "validator": "seasonality_weather",
            "candidate_id": candidate_id,
            "score": 0.0,
            "verdict": "fail",
            "reasons": [f"검증 실패: {str(e)}"],
            "assumptions": ["실시간 데이터 아님"],
            "questions_to_user": []
        }