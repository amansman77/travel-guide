"""Safety risk validator."""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_safety_risk_validator(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build safety risk validator chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a safety analyst for travel recommendations. Evaluate general safety and risk factors for the destination. Provide balanced, practical advice. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Evaluate safety risk considering:
- General crime rates (petty theft, pickpocketing)
- Tourist-targeted scams
- Nighttime safety
- Solo traveler safety (if applicable)
- Overall safety reputation

IMPORTANT CONSTRAINTS:
- Do NOT create excessive fear or panic
- Focus on general precautions, not extreme warnings
- Consider typical tourist experiences
- Provide balanced, practical advice

Return JSON schema exactly:
{{
  "validator": "safety_risk",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": []
}}

Scoring:
- score: 0.0-1.0 (1.0 = very safe, 0.0 = high risk)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
""")
    ])
    
    return prompt | llm | parser


def run_safety_risk_validator(chain, profile: dict, candidate: dict, candidate_id: str) -> dict:
    """
    Execute safety risk validator.
    
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
            result["assumptions"] = ["실시간 데이터 아님"]
        if "questions_to_user" not in result:
            result["questions_to_user"] = []
            
        return result
    except Exception as e:
        # Graceful error handling
        return {
            "validator": "safety_risk",
            "candidate_id": candidate_id,
            "score": 0.0,
            "verdict": "fail",
            "reasons": [f"검증 실패: {str(e)}"],
            "assumptions": ["실시간 데이터 아님"],
            "questions_to_user": []
        }