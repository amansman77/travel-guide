"""LLM-based router for ambiguous cases."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from .types import RouteDecision


def build_llm_router(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build LLM router chain."""
    router_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel request router. Analyze the user's travel request and determine the most appropriate route. Return ONLY valid JSON. No markdown."),
        ("user", """
User travel request:
{user_input}

Determine the appropriate route based on:
- "clarify": Insufficient information (less than 2 key fields: duration, budget, companions, purpose)
- "candidates_only": User explicitly asks for destination candidates only
- "itinerary_only": User asks for itinerary/schedule for a specific destination
- "full": User wants full recommendation (default)

Return JSON schema exactly:
{{
  "route": "full|clarify|candidates_only|itinerary_only",
  "reason": "Brief explanation in Korean",
  "missing_fields": ["field1", "field2"] or [],
  "confidence": 0.0-1.0
}}
""")
    ])
    
    return router_prompt | llm | parser


def route_with_llm(user_input: str, llm: ChatOpenAI, parser: JsonOutputParser) -> RouteDecision:
    """
    Use LLM to route user input when rule-based router is uncertain.
    """
    router_chain = build_llm_router(llm, parser)
    
    try:
        result = router_chain.invoke({"user_input": user_input})
        
        # Validate result
        route = result.get("route", "full")
        if route not in ["full", "clarify", "candidates_only", "itinerary_only"]:
            route = "full"
        
        return RouteDecision(
            route=route,
            reason=result.get("reason", "LLM 라우팅 결과"),
            confidence=float(result.get("confidence", 0.7)),
            missing_fields=result.get("missing_fields", []),
            router_type="llm"
        )
    except Exception as e:
        # Fallback to clarify on error
        return RouteDecision(
            route="clarify",
            reason=f"LLM 라우팅 실패, clarify로 fallback: {str(e)}",
            confidence=0.5,
            missing_fields=[],
            router_type="llm"
        )
