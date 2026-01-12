"""Candidates-only chain that runs only profile and candidates steps."""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_candidates_only_chain(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build candidates-only chain (profile + candidates only)."""
    profile_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel analyst. Return ONLY valid JSON. No markdown."),
        ("user", """
User travel request:
{user_input}

Return JSON schema exactly:
{{
  "tags": ["..."],
  "top_priorities": ["..."],
  "constraints": {{
    "season": "",
    "budget": "",
    "companions": "",
    "pace": "slow|medium|fast",
    "duration_days": 0,
    "domestic_or_international": "domestic|international|either"
  }},
  "avoid": ["..."],
  "notes_for_recommender": ""
}}
""")
    ])

    candidates_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel curator. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile JSON:
{profile}

Generate 5 destination candidates that fit.

Return JSON schema:
{{
  "candidates": [
    {{
      "name": "City, Country",
      "why_fit": ["...","..."],
      "watch_out": ["..."],
      "best_length_days": 3
    }}
  ]
}}
""")
    ])

    profile_chain = profile_prompt | llm | parser
    candidates_chain = candidates_prompt | llm | parser

    def step1_profile(inputs):
        """STEP 1: 여행자 프로필 분석"""
        return {
            "user_input": inputs["user_input"],
            "profile": profile_chain.invoke({"user_input": inputs["user_input"]})
        }
    
    def step2_candidates(inputs):
        """STEP 2: 후보 도시 생성"""
        return {
            **inputs,
            "candidates": candidates_chain.invoke({
                "profile": safe_json(inputs["profile"])
            })
        }
    
    return (
        RunnableLambda(step1_profile)
        | RunnableLambda(step2_candidates)
    )


def run_candidates_only_chain(chain, user_input: str):
    """
    Execute candidates-only chain and return profile and candidates.
    """
    result = chain.invoke({"user_input": user_input})
    
    return {
        "profile": result["profile"],
        "candidates": result["candidates"]
    }
