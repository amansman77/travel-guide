"""Vibe fit validator."""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_vibe_fit_validator(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build vibe fit validator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a vibe analyst for travel recommendations. Evaluate if the destination matches the traveler's preferences and vibe. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Evaluate vibe fit considering:
- Quietness/peacefulness (if traveler prefers quiet)
- Cafe culture and coffee scene
- Walkability and pedestrian-friendly areas
- Natural environment (parks, nature spots)
- Overall atmosphere matching traveler's pace (slow/medium/fast)

Focus on:
- Does the city match the traveler's top priorities?
- Does it avoid what the traveler wants to avoid?
- Is the pace/atmosphere suitable?

Return JSON schema exactly:
{{
  "validator": "vibe_fit",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": []
}}

Scoring:
- score: 0.0-1.0 (1.0 = perfect match, 0.0 = poor match)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
""")
    ])
    
    return prompt | llm | parser


def run_vibe_fit_validator(chain, profile: dict, candidate: dict, candidate_id: str) -> dict:
    """
    Execute vibe fit validator.
    
    Returns validator result with graceful error handling.
    """
    try:
        result = chain.invoke({
            "profile": safe_json(profile),
            "candidate": safe_json(candidate),
            "candidate_id": candidate_id
        })
        
        # Validate required fields
        if "validator" not in result:
            result["validator"] = "vibe_fit"
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
            "validator": "vibe_fit",
            "candidate_id": candidate_id,
            "score": 0.0,
            "verdict": "fail",
            "reasons": [f"검증 실패: {str(e)}"],
            "assumptions": ["실시간 데이터 아님"],
            "questions_to_user": []
        }