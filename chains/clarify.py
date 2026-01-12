"""Clarify chain for generating clarification questions."""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def build_clarify_chain(llm: ChatOpenAI, parser: JsonOutputParser):
    """Build clarify chain that generates questions to clarify user requirements."""
    clarify_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a travel assistant. Generate clarifying questions to help understand the user's travel needs. Return ONLY valid JSON. No markdown."),
        ("user", """
User travel request:
{user_input}

Missing fields that need clarification:
{missing_fields}

Generate 3-5 specific questions in Korean to help clarify the user's travel requirements.
Do NOT provide recommendations, only ask questions.

Return JSON schema exactly:
{{
  "questions": [
    "질문 1",
    "질문 2",
    "질문 3"
  ],
  "context": "Brief explanation of why these questions are needed"
}}
""")
    ])
    
    return clarify_prompt | llm | parser


def run_clarify_chain(chain, user_input: str, missing_fields: list):
    """
    Execute clarify chain and return questions.
    """
    result = chain.invoke({
        "user_input": user_input,
        "missing_fields": ", ".join(missing_fields) if missing_fields else "추가 정보"
    })
    
    return {
        "questions": result.get("questions", []),
        "context": result.get("context", "")
    }
