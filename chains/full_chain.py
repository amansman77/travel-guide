"""Full chain implementation (v1: 4-step, v2: 5-step with validators)."""
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda

from chains.parallel_validators import run_parallel_validators
from chains.aggregator import build_aggregator_chain, run_aggregator

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


def build_full_chain(llm: ChatOpenAI, parser: JsonOutputParser):
    """
    Build the full 4-step unified chain.
    LangSmith will track this as a single runnable sequence.
    """
    # Prompts
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

    comparison_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a pragmatic travel evaluator. Return ONLY valid JSON. No markdown."),
        ("user", """
Traveler profile:
{profile}

Candidates:
{candidates}

Compare and score each (1-10):
- fit
- cost
- walking_friendliness
- quietness
- cafe_scene

Return JSON schema:
{{
  "table": [
    {{
      "name": "",
      "scores": {{
        "fit": 0,
        "cost": 0,
        "walking_friendliness": 0,
        "quietness": 0,
        "cafe_scene": 0
      }},
      "summary": ""
    }}
  ],
  "top2": ["",""]
}}
""")
    ])

    final_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel planner. Return ONLY valid JSON in Korean. No markdown."),
        ("user", """
Traveler profile:
{profile}

Comparison:
{comparison}

Pick the best destination and propose a 3-night 4-day plan.
Be realistic and avoid exaggeration.

Return JSON schema:
{{
  "winner": {{
    "name": "",
    "why": ["...","..."],
    "best_area_to_stay": "",
    "budget_tip": ""
  }},
  "itinerary": [
    {{"day": 1, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 2, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 3, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 4, "morning":"", "afternoon":"", "evening":""}}
  ]
}}
""")
    ])

    # Individual chains
    profile_chain = profile_prompt | llm | parser
    candidates_chain = candidates_prompt | llm | parser
    comparison_chain = comparison_prompt | llm | parser
    final_chain = final_prompt | llm | parser

    # Step functions
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
    
    def step3_comparison(inputs):
        """STEP 3: 비교 및 점수화"""
        return {
            **inputs,
            "comparison": comparison_chain.invoke({
                "profile": safe_json(inputs["profile"]),
                "candidates": safe_json(inputs["candidates"])
            })
        }
    
    def step4_final(inputs):
        """STEP 4: 최종 추천 및 일정"""
        return {
            **inputs,
            "final": final_chain.invoke({
                "profile": safe_json(inputs["profile"]),
                "comparison": safe_json(inputs["comparison"])
            })
        }
    
    # Unified chain
    return (
        RunnableLambda(step1_profile)
        | RunnableLambda(step2_candidates)
        | RunnableLambda(step3_comparison)
        | RunnableLambda(step4_final)
    )


def run_full_chain(chain, user_input: str):
    """
    Execute the full chain (v1) and return results.
    """
    result = chain.invoke({"user_input": user_input})
    
    return {
        "profile": result["profile"],
        "candidates": result["candidates"],
        "comparison": result["comparison"],
        "final": result["final"]
    }


def build_full_chain_v2(llm: ChatOpenAI, parser: JsonOutputParser):
    """
    Build the full 5-step v2 chain with validators and aggregator.
    LangSmith will track this as a single runnable sequence.
    """
    # Prompts (STEP 1, 2, 5 are same as v1)
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

    final_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel planner. Return ONLY valid JSON in Korean. No markdown."),
        ("user", """
Traveler profile:
{profile}

Aggregator result:
{aggregation}

Pick the final destination from aggregator's final_choice and propose a 3-night 4-day plan.
Include validation summary (key validator insights) in the output.
Be realistic and avoid exaggeration.

Return JSON schema:
{{
  "winner": {{
    "name": "",
    "why": ["...","..."],
    "best_area_to_stay": "",
    "budget_tip": ""
  }},
  "itinerary": [
    {{"day": 1, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 2, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 3, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 4, "morning":"", "afternoon":"", "evening":""}}
  ],
  "validation_summary": {{
    "key_strengths": ["..."],
    "key_risks": ["..."],
    "watchouts": ["..."]
  }}
}}
""")
    ])

    # Individual chains
    profile_chain = profile_prompt | llm | parser
    candidates_chain = candidates_prompt | llm | parser
    aggregator_chain = build_aggregator_chain(llm, parser)
    final_chain = final_prompt | llm | parser

    # Step functions
    def step1_profile(inputs):
        """STEP 1: 여행자 프로필 분석"""
        return {
            "user_input": inputs["user_input"],
            "profile": profile_chain.invoke({"user_input": inputs["user_input"]})
        }
    
    def step2_candidates(inputs):
        """STEP 2: 후보 도시 생성"""
        candidates_result = candidates_chain.invoke({
            "profile": safe_json(inputs["profile"])
        })
        return {
            **inputs,
            "candidates": candidates_result.get("candidates", [])
        }
    
    def step3_parallel_validators(inputs):
        """STEP 3: 병렬 검증"""
        validators_results = run_parallel_validators(
            llm,
            parser,
            inputs["profile"],
            inputs["candidates"],
            max_concurrent=5
        )
        return {
            **inputs,
            "validators_results": validators_results
        }
    
    def step4_aggregator(inputs):
        """STEP 4: 검증 결과 종합"""
        aggregation = run_aggregator(
            aggregator_chain,
            inputs["profile"],
            inputs["candidates"],
            inputs["validators_results"]
        )
        return {
            **inputs,
            "aggregation": aggregation
        }
    
    def step5_final(inputs):
        """STEP 5: 최종 추천 및 일정"""
        return {
            **inputs,
            "final": final_chain.invoke({
                "profile": safe_json(inputs["profile"]),
                "aggregation": safe_json(inputs["aggregation"])
            })
        }
    
    # Unified chain
    return (
        RunnableLambda(step1_profile)
        | RunnableLambda(step2_candidates)
        | RunnableLambda(step3_parallel_validators)
        | RunnableLambda(step4_aggregator)
        | RunnableLambda(step5_final)
    )


def run_full_chain_v2(chain, user_input: str):
    """
    Execute the full chain v2 and return results.
    LangSmith tracing is handled by the chain itself.
    """
    # Chain invoke will be automatically traced by LangSmith
    # if LANGSMITH_TRACING is enabled
    result = chain.invoke({"user_input": user_input})
    
    return {
        "profile": result["profile"],
        "candidates": result["candidates"],
        "validators_results": result["validators_results"],
        "aggregation": result["aggregation"],
        "final": result["final"]
    }
