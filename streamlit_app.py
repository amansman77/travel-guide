import os
import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda

from router.rules import route_user_input
from router.llm_router import route_with_llm
from router.types import RouteDecision, RouteResult
from chains.full_chain import build_full_chain, run_full_chain, build_full_chain_v2, run_full_chain_v2, safe_json
from chains.clarify import build_clarify_chain, run_clarify_chain
from chains.itinerary_only import build_itinerary_only_chain, run_itinerary_only_chain
from chains.candidates_only import build_candidates_only_chain, run_candidates_only_chain
from observability.langsmith import trace_router_decision, generate_request_id
try:
    from langsmith import traceable
except ImportError:
    # Fallback if langsmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator

# Router functions (not traceable individually, will be part of unified trace)
def run_rule_router(input_text: str) -> RouteDecision:
    """Rule-based router."""
    return route_user_input(input_text)

def run_llm_router(input_text: str, llm_instance: ChatOpenAI, parser_instance: JsonOutputParser) -> RouteDecision:
    """LLM-based router."""
    return route_with_llm(input_text, llm_instance, parser_instance)

load_dotenv()

# ====== LangSmith 설정 (LLM 초기화 전에 먼저 설정) ======
def get_config(config_key: str, default: str = None) -> str:
    """환경변수 또는 Streamlit secrets에서 설정값을 가져옵니다."""
    config_value = os.getenv(config_key)
    if not config_value:
        try:
            config_value = st.secrets.get(config_key, default)
        except (FileNotFoundError, AttributeError, KeyError):
            config_value = default
    return config_value

# LangSmith 설정 로드 (LLM 초기화 전에 먼저 설정해야 함)
langsmith_tracing = get_config("LANGSMITH_TRACING")
if langsmith_tracing and str(langsmith_tracing).lower() in ("true", "1", "yes"):
    # LangSmith 환경변수 설정 (LangChain이 인식하는 모든 변수명 설정)
    langsmith_api_key = get_config("LANGSMITH_API_KEY")
    langsmith_endpoint = get_config("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    langsmith_project = get_config("LANGSMITH_PROJECT", "travel-guide")
    
    if langsmith_api_key:
        # 최신 LangChain은 LANGSMITH_* 사용
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        os.environ["LANGSMITH_ENDPOINT"] = langsmith_endpoint
        os.environ["LANGSMITH_PROJECT"] = langsmith_project
        
        # 하위 호환성을 위한 LANGCHAIN_* 변수도 설정
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_ENDPOINT"] = langsmith_endpoint
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project

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

model_name = st.sidebar.selectbox("LLM 모델", ["gpt-4o-mini", "gpt-4.1-mini"], index=0)
temperature = st.sidebar.slider("temperature", 0.0, 1.0, 0.4, 0.05)

llm = ChatOpenAI(model=model_name, temperature=temperature)
parser = JsonOutputParser()

# Chains 초기화
full_chain_v2 = build_full_chain_v2(llm, parser)  # Use v2 with validators
full_chain = build_full_chain(llm, parser)  # Keep v1 for fallback
clarify_chain = build_clarify_chain(llm, parser)
itinerary_only_chain = build_itinerary_only_chain(llm, parser)
candidates_only_chain = build_candidates_only_chain(llm, parser)

# ====== UI ======
left, right = st.columns([1, 1])

with left:
    st.subheader("1) 여행 조건 입력")
    example = "예: 3월에 혼자 4일, 예산 150만원, 걷기/카페/조용한 휴식 선호, 해외"
    user_input = st.text_area("자연어로 적어줘", height=160, placeholder=example)

    run = st.button("추천 받기", type="primary", use_container_width=True)

with right:
    st.subheader("2) 체이닝 결과")

def execute_route(route_decision: RouteDecision, user_input: str) -> RouteResult:
    """
    Execute chain based on route decision.
    """
    route = route_decision.route
    
    if route == "full":
        # Full v2 chain (5-step with validators)
        print(f"[DEBUG] Running Full Chain v2 with validators...")
        result_data = run_full_chain_v2(full_chain_v2, user_input)
        
        # Debug: Check if v2 structure
        is_v2 = "validators_results" in result_data and "aggregation" in result_data
        print(f"[DEBUG] Full Chain v2 executed: {is_v2}")
        if is_v2:
            print(f"[DEBUG] - Validators results count: {len(result_data.get('validators_results', []))}")
            print(f"[DEBUG] - Aggregation present: {bool(result_data.get('aggregation'))}")
            print(f"[DEBUG] - Final recommendation present: {bool(result_data.get('final'))}")
        
        return RouteResult(
            route=route,
            router_reason=route_decision.reason,
            data=result_data
        )
    elif route == "clarify":
        # Clarify chain
        result_data = run_clarify_chain(clarify_chain, user_input, route_decision.missing_fields)
        return RouteResult(
            route=route,
            router_reason=route_decision.reason,
            data=result_data
        )
    elif route == "candidates_only":
        # Candidates only chain
        result_data = run_candidates_only_chain(candidates_only_chain, user_input)
        return RouteResult(
            route=route,
            router_reason=route_decision.reason,
            data=result_data
        )
    elif route == "itinerary_only":
        # Itinerary only chain
        result_data = run_itinerary_only_chain(itinerary_only_chain, user_input)
        return RouteResult(
            route=route,
            router_reason=route_decision.reason,
            data=result_data
        )
    else:
        # Fallback to full
        result_data = run_full_chain(full_chain, user_input)
        return RouteResult(
            route="full",
            router_reason="알 수 없는 라우트, full로 fallback",
            data=result_data
        )


@traceable(
    name="travel_guide_router_chain",
    run_type="chain"
)
def run_router_and_chain(user_input: str, llm_instance: ChatOpenAI, parser_instance: JsonOutputParser) -> RouteResult:
    """
    Unified router and chain execution as a single traceable sequence.
    This creates one unified trace in LangSmith showing: Router → Selected Chain
    
    All steps (routing, decision, chain execution) are executed within this single trace,
    creating a cohesive view in LangSmith.
    """
    # Step 1: Rule-based routing
    route_decision = run_rule_router(user_input)
    
    # Step 2: LLM router fallback if confidence is low
    if route_decision.confidence < 0.7:
        route_decision = run_llm_router(user_input, llm_instance, parser_instance)
    
    # Step 3: Generate router decision metadata
    router_metadata = trace_router_decision(route_decision, user_input)
    
    # Step 4: Execute route (chain execution happens here)
    route_result = execute_route(route_decision, user_input)
    
    # Add metadata to the trace
    return route_result

if run:
    if not user_input.strip():
        st.warning("여행 조건을 입력해줘.")
        st.stop()

    with st.spinner("라우팅 및 체이닝 실행 중..."):
        try:
            # Unified router and chain execution as single traceable sequence
            route_result = run_router_and_chain(user_input, llm, parser)
            
        except Exception as e:
            st.error("실행 중 오류가 났어. (JSON 파싱/모델 응답 형식 문제일 가능성이 큼)")
            st.exception(e)
            st.stop()

    # Display route info
    route_badge_color = {
        "full": "🟢",
        "clarify": "🟡",
        "candidates_only": "🔵",
        "itinerary_only": "🟣"
    }
    route_labels = {
        "full": "전체 추천",
        "clarify": "조건 확인",
        "candidates_only": "후보만",
        "itinerary_only": "일정만"
    }
    st.markdown(f"**선택된 라우트:** {route_badge_color.get(route_result.route, '⚪')} `{route_labels.get(route_result.route, route_result.route)}` | **이유:** {route_result.router_reason}")

    # Route별 결과 렌더링
    if route_result.route == "full":
        data = route_result.data
        
        # Check if v2 data structure (has validators_results and aggregation)
        is_v2 = "validators_results" in data and "aggregation" in data
        
        # Display version info
        if is_v2:
            st.success("✅ 완료! (Travel Concierge v2 - Validators 실행됨)")
            st.info(f"🔍 검증 완료: {len(data.get('validators_results', []))}개 검증 결과, Aggregation 완료")
        else:
            st.warning("⚠️ v1 구조로 실행됨 (validators_results 또는 aggregation 없음)")
            st.success("완료!")
        
        with st.expander("STEP 1) 여행자 프로필", expanded=False):
            st.code(safe_json(data["profile"]), language="json")
        
        with st.expander("STEP 2) 후보 5곳", expanded=False):
            st.code(safe_json(data["candidates"]), language="json")
        
        if is_v2:
            # STEP 3: Validators Results
            with st.expander("STEP 3) 검증 결과 (Parallel Validators)", expanded=False):
                validators_results = data.get("validators_results", [])
                
                # Group by candidate
                by_candidate = {}
                for result in validators_results:
                    candidate_id = result.get("candidate_id", "unknown")
                    if candidate_id not in by_candidate:
                        by_candidate[candidate_id] = []
                    by_candidate[candidate_id].append(result)
                
                # Display validator summary table
                if by_candidate:
                    st.write("**후보별 검증 요약**")
                    
                    summary_data = []
                    for candidate_id, results in by_candidate.items():
                        candidate_name = next(
                            (c.get("name", candidate_id) for c in data.get("candidates", []) 
                             if f"C{data.get('candidates', []).index(c)+1}" == candidate_id),
                            candidate_id
                        )
                        row = {"후보": candidate_name}
                        for result in results:
                            validator_name = result.get("validator", "unknown")
                            score = result.get("score", 0.0)
                            verdict = result.get("verdict", "fail")
                            row[validator_name] = f"{score:.2f} ({verdict})"
                        summary_data.append(row)
                    
                    if summary_data:
                        df = pd.DataFrame(summary_data)
                        st.dataframe(df, use_container_width=True)
                
                # Detailed results
                st.write("**상세 검증 결과**")
                st.code(safe_json(validators_results), language="json")
            
            # STEP 4: Aggregation
            with st.expander("STEP 4) 검증 결과 종합 (Aggregator)", expanded=True):
                aggregation = data.get("aggregation", {})
                
                # Display ranked candidates
                ranked = aggregation.get("ranked_candidates", [])
                if ranked:
                    st.write("**순위별 후보**")
                    for i, candidate in enumerate(ranked[:3], 1):  # Top 3
                        with st.container():
                            st.markdown(f"### {i}. {candidate.get('name', 'Unknown')} (점수: {candidate.get('total_score', 0):.2f})")
                            st.write(f"**요약:** {candidate.get('summary', '')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if candidate.get("strengths"):
                                    st.write("**강점:**")
                                    for strength in candidate.get("strengths", [])[:3]:
                                        st.write(f"✅ {strength}")
                            with col2:
                                if candidate.get("risks"):
                                    st.write("**리스크:**")
                                    for risk in candidate.get("risks", [])[:3]:
                                        st.write(f"⚠️ {risk}")
                            
                            if candidate.get("watchouts"):
                                st.write("**주의사항:**")
                                for watchout in candidate.get("watchouts", [])[:2]:
                                    st.write(f"🔔 {watchout}")
                            st.divider()
                
                # Final choice
                final_choice = aggregation.get("final_choice", {})
                if final_choice:
                    st.write("**최종 선택**")
                    st.markdown(f"### 🏆 {final_choice.get('name', 'Unknown')}")
                    if final_choice.get("why"):
                        st.write("**선택 이유:**")
                        for reason in final_choice.get("why", []):
                            st.write(f"• {reason}")
                    if final_choice.get("what_to_confirm"):
                        st.write("**확인 필요 사항:**")
                        for confirm in final_choice.get("what_to_confirm", []):
                            st.write(f"❓ {confirm}")
                
                # Disclaimer
                if aggregation.get("disclaimer"):
                    st.info(aggregation.get("disclaimer"))
                
                # Full JSON (expander 중첩 방지를 위해 일반 코드 블록 사용)
                st.write("**전체 Aggregation JSON:**")
                st.code(safe_json(aggregation), language="json")
            
            # STEP 5: Final Recommendation
            with st.expander("STEP 5) 최종 추천 + 3박4일 일정", expanded=True):
                final = data.get("final", {})
                
                # Winner
                winner = final.get("winner", {})
                if winner:
                    st.markdown(f"### 🎯 추천 여행지: {winner.get('name', 'Unknown')}")
                    if winner.get("why"):
                        st.write("**추천 이유:**")
                        for reason in winner.get("why", []):
                            st.write(f"• {reason}")
                    if winner.get("best_area_to_stay"):
                        st.write(f"**추천 숙박 지역:** {winner.get('best_area_to_stay')}")
                    if winner.get("budget_tip"):
                        st.write(f"**예산 팁:** {winner.get('budget_tip')}")
                
                # Validation summary
                validation_summary = final.get("validation_summary", {})
                if validation_summary:
                    st.write("**검증 근거 요약**")
                    col1, col2 = st.columns(2)
                    with col1:
                        if validation_summary.get("key_strengths"):
                            st.write("**핵심 강점:**")
                            for strength in validation_summary.get("key_strengths", [])[:3]:
                                st.write(f"✅ {strength}")
                    with col2:
                        if validation_summary.get("key_risks"):
                            st.write("**핵심 리스크:**")
                            for risk in validation_summary.get("key_risks", [])[:3]:
                                st.write(f"⚠️ {risk}")
                    
                    if validation_summary.get("watchouts"):
                        st.write("**주의사항:**")
                        for watchout in validation_summary.get("watchouts", [])[:3]:
                            st.write(f"🔔 {watchout}")
                
                # Itinerary
                itinerary = final.get("itinerary", [])
                if itinerary:
                    st.write("**3박 4일 일정**")
                    for day_info in itinerary:
                        day = day_info.get("day", 0)
                        st.write(f"**Day {day}**")
                        if day_info.get("morning"):
                            st.write(f"  🌅 오전: {day_info['morning']}")
                        if day_info.get("afternoon"):
                            st.write(f"  ☀️ 오후: {day_info['afternoon']}")
                        if day_info.get("evening"):
                            st.write(f"  🌙 저녁: {day_info['evening']}")
                
                # Full JSON (expander 중첩 방지를 위해 일반 코드 블록 사용)
                st.write("**전체 Final JSON:**")
                st.code(safe_json(final), language="json")
        else:
            # Fallback to v1 display
            with st.expander("STEP 3) 비교표", expanded=False):
                st.code(safe_json(data.get("comparison", {})), language="json")
            with st.expander("STEP 4) 최종 추천 + 3박4일 일정", expanded=True):
                st.code(safe_json(data.get("final", {})), language="json")
    
    elif route_result.route == "clarify":
        st.info("추가 정보가 필요합니다.")
        data = route_result.data
        if data.get("context"):
            st.write(f"**{data['context']}**")
        if data.get("questions"):
            st.write("**다음 질문에 답해주세요:**")
            for i, question in enumerate(data["questions"], 1):
                st.write(f"{i}. {question}")
    
    elif route_result.route == "candidates_only":
        st.success("후보 도시 추천 완료!")
        data = route_result.data
        with st.expander("여행자 프로필", expanded=False):
            st.code(safe_json(data["profile"]), language="json")
        with st.expander("추천 후보 5곳", expanded=True):
            st.code(safe_json(data["candidates"]), language="json")
    
    elif route_result.route == "itinerary_only":
        st.success("일정 생성 완료!")
        data = route_result.data
        st.write(f"**목적지:** {data.get('destination', 'N/A')}")
        if data.get("best_area_to_stay"):
            st.write(f"**추천 숙박 지역:** {data['best_area_to_stay']}")
        if data.get("budget_tip"):
            st.write(f"**예산 팁:** {data['budget_tip']}")
        
        with st.expander("상세 일정", expanded=True):
            for day_info in data.get("itinerary", []):
                day = day_info.get("day", 0)
                st.write(f"**Day {day}**")
                if day_info.get("morning"):
                    st.write(f"  🌅 오전: {day_info['morning']}")
                if day_info.get("afternoon"):
                    st.write(f"  ☀️ 오후: {day_info['afternoon']}")
                if day_info.get("evening"):
                    st.write(f"  🌙 저녁: {day_info['evening']}")
        
        if data.get("tips"):
            with st.expander("여행 팁", expanded=False):
                for tip in data["tips"]:
                    st.write(f"- {tip}")
    
    else:
        st.info(route_result.data.get("message", "기능 구현 중입니다."))
