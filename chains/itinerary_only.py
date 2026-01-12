"""Itinerary-only chain for generating schedule for a specific destination."""
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def safe_json(obj) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_itinerary_only_chain(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build itinerary-only chain that generates schedule for a specific destination."""
    itinerary_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel planner. Generate a detailed itinerary for the specified destination. Return ONLY valid JSON in Korean. No markdown."),
        ("user", """
User travel request:
{user_input}

Extract the destination from the user input and create a detailed itinerary.
Focus on practical, realistic suggestions.

Return JSON schema exactly:
{{
  "destination": "City, Country",
  "duration_days": 0,
  "best_area_to_stay": "",
  "budget_tip": "",
  "itinerary": [
    {{"day": 1, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 2, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 3, "morning":"", "afternoon":"", "evening":""}},
    {{"day": 4, "morning":"", "afternoon":"", "evening":""}}
  ],
  "tips": ["팁 1", "팁 2", "팁 3"]
}}
""")
    ])
    
    return itinerary_prompt | llm | parser


def run_itinerary_only_chain(chain, user_input: str):
    """
    Execute itinerary-only chain and return schedule.
    """
    result = chain.invoke({"user_input": user_input})
    
    return {
        "destination": result.get("destination", ""),
        "duration_days": result.get("duration_days", 0),
        "best_area_to_stay": result.get("best_area_to_stay", ""),
        "budget_tip": result.get("budget_tip", ""),
        "itinerary": result.get("itinerary", []),
        "tips": result.get("tips", [])
    }
