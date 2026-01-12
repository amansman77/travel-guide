import os
import json
import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

st.set_page_config(page_title="Travel Guide MVP", layout="wide")
st.title("✈️ Travel Guide MVP (Prompt Chaining)")

# ====== Config ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
    except (FileNotFoundError, AttributeError, KeyError):
        OPENAI_API_KEY = None

if not OPENAI_API_KEY:
    st.error("⚠️ OPENAI_API_KEY가 없습니다. 환경변수 또는 .streamlit/secrets.toml에 설정하세요.")
    st.info("앱을 사용하려면 API 키가 필요합니다.")
    # Cloud Run에서는 st.stop()이 앱 시작을 막을 수 있으므로 제거
    # st.stop()

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# LangSmith (optional)
# 환경변수로만 켜두는 걸 추천:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=...
# LANGCHAIN_PROJECT=travel-guide-mvp

model_name = st.sidebar.selectbox("LLM 모델", ["gpt-4o-mini", "gpt-4.1-mini"], index=0)
temperature = st.sidebar.slider("temperature", 0.0, 1.0, 0.4, 0.05)

llm = ChatOpenAI(model=model_name, temperature=temperature)
parser = JsonOutputParser()

# ====== Prompts (고정 단계 / JSON 출력 고정) ======
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

profile_chain = profile_prompt | llm | parser
candidates_chain = candidates_prompt | llm | parser
comparison_chain = comparison_prompt | llm | parser
final_chain = final_prompt | llm | parser

# ====== UI ======
left, right = st.columns([1, 1])

with left:
    st.subheader("1) 여행 조건 입력")
    example = "예: 3월에 혼자 4일, 예산 150만원, 걷기/카페/조용한 휴식 선호, 해외"
    user_input = st.text_area("자연어로 적어줘", height=160, placeholder=example)

    run = st.button("추천 받기", type="primary", use_container_width=True)

with right:
    st.subheader("2) 체이닝 결과")

def safe_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

def run_chain(user_input: str):
    profile = profile_chain.invoke({"user_input": user_input})
    candidates = candidates_chain.invoke({"profile": safe_json(profile)})
    comparison = comparison_chain.invoke({
        "profile": safe_json(profile),
        "candidates": safe_json(candidates)
    })
    final = final_chain.invoke({
        "profile": safe_json(profile),
        "comparison": safe_json(comparison)
    })
    return profile, candidates, comparison, final

if run:
    if not user_input.strip():
        st.warning("여행 조건을 입력해줘.")
        st.stop()

    with st.spinner("체이닝 실행 중..."):
        try:
            profile, candidates, comparison, final = run_chain(user_input)
        except Exception as e:
            st.error("체이닝 실행 중 오류가 났어. (JSON 파싱/모델 응답 형식 문제일 가능성이 큼)")
            st.exception(e)
            st.stop()

    st.success("완료!")

    with st.expander("STEP 1) 여행자 프로필", expanded=True):
        st.code(safe_json(profile), language="json")

    with st.expander("STEP 2) 후보 5곳", expanded=False):
        st.code(safe_json(candidates), language="json")

    with st.expander("STEP 3) 비교표", expanded=False):
        st.code(safe_json(comparison), language="json")

    with st.expander("STEP 4) 최종 추천 + 3박4일 일정", expanded=True):
        st.code(safe_json(final), language="json")
