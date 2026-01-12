# Travel Guide MVP (Prompt Chaining)

이 프로젝트는 **Prompt Chaining 개념을 실제로 실습**하기 위한  
**Streamlit 기반 여행 추천 MVP**입니다.

하나의 질문으로 여행지를 추천하지 않고,  
**여러 단계의 사고(체인)를 거쳐 점진적으로 추천을 완성**하는 구조를 채택했습니다.

> 목적:  
> - 프롬프트 체이닝을 “개념”이 아니라 “제품 구조”로 이해하기  
> - FastAPI 없이도 LLM 기반 서비스 흐름을 빠르게 검증하기

## ✨ MVP Scope

현재 MVP는 아래 **2가지 기능만** 포함합니다.

1. **여행 조건 입력**
   - 자연어 기반 입력 (예: 시기, 예산, 동행, 목적)
2. **체이닝 기반 여행 추천 결과 출력**
   - 단계별 중간 결과를 그대로 노출 (디버깅/학습 목적)

## 🧠 Prompt Chaining Structure

추천은 아래 **고정된 4단계 체인**으로 수행됩니다.

```

STEP 1. Traveler Profile
→ STEP 2. Destination Candidates (5)
→ STEP 3. Comparison & Scoring
→ STEP 4. Final Recommendation + Itinerary

```

### 핵심 설계 원칙
- **단계 구조는 고정**
- **각 단계 출력은 JSON으로 고정**
- **다음 단계는 이전 단계 JSON을 그대로 입력으로 사용**
- 추천은 **마지막 단계에서만 수행**

## 🧩 Tech Stack (Lean Stack - Option A)

- **Frontend**: Streamlit
- **LLM**: OpenAI (via LangChain)
- **Prompt Orchestration**: LangChain (Chain + PromptTemplate)
- **Observability (Optional)**: LangSmith
- **Backend API**: ❌ 없음 (Streamlit 단독)
- **Deployment**: Docker + GCP Cloud Run

## 📁 Project Structure

```

travel-guide-mvp/
├─ streamlit_app.py      # Streamlit app + Prompt Chaining logic
├─ requirements.txt      # Python dependencies
├─ Dockerfile            # Cloud Run deployment
└─ .streamlit/
└─ secrets.toml       # (로컬 전용) API Key

````

## 🚀 Getting Started (Local)

### 1. Environment Variable 설정

```bash
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
````

또는 `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

### 2. Install & Run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

브라우저에서:

```
http://localhost:8501
```

## 🖥️ Usage

### 입력 예시

```
3월에 혼자 4일 정도 여행,
예산은 150만원,
걷기와 카페 위주,
조용한 휴식 선호,
해외 여행
```

### 출력 구성

* STEP 1: 여행자 성향 요약(JSON)
* STEP 2: 추천 후보 도시 5곳
* STEP 3: 항목별 비교 점수
* STEP 4: 최종 추천 + 3박 4일 일정

모든 결과는 **Streamlit expander**로 단계별 확인 가능.

## 🧪 실습 포인트

이 프로젝트는 **학습용 MVP**이므로 다음을 직접 실험해보는 것을 권장합니다.

* `temperature` 값 조절 → 결과 안정성 vs 다양성 비교
* 후보 생성 기준 수정 → 추천 품질 변화 관찰
* JSON Schema 변경 → 체이닝 안정성 체감
* Step 하나 제거/추가 → UX 변화 확인

## 🔍 Observability (LangSmith)

프롬프트/체인 실행 로그를 LangSmith에서 추적하고 모니터링할 수 있습니다.

### 로컬 개발

`.streamlit/secrets.toml` 파일에 다음을 추가하세요:

```toml
LANGSMITH_TRACING="true"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="YOUR_LANGSMITH_API_KEY"
LANGSMITH_PROJECT="travel-guide"
```

또는 환경변수로 설정:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
export LANGSMITH_API_KEY="YOUR_LANGSMITH_API_KEY"
export LANGSMITH_PROJECT="travel-guide"
```

### LangSmith 대시보드

설정 후 앱을 실행하면 LangSmith 대시보드에서 다음을 확인할 수 있습니다:
- 각 프롬프트 체인 단계별 실행 시간
- LLM 호출 비용 및 토큰 사용량
- 체인 실행 추적 및 디버깅 정보
- 에러 및 예외 로그

LangSmith 대시보드: https://smith.langchain.com

## 🐳 Deployment (GCP Cloud Run)

### Docker Build

```bash
docker build -t travel-guide-mvp .
```

### Run (Local Docker)

```bash
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=YOUR_OPENAI_API_KEY \
  travel-guide-mvp
```

Cloud Run에서는:

* 컨테이너 이미지 지정
* 환경변수에 `OPENAI_API_KEY` 설정
* 포트: `8080`

## 🔮 Next Steps (Out of MVP)

이 MVP는 이후 아래 방향으로 자연스럽게 확장 가능합니다.

* FastAPI 분리 (API / UI 분리)
* 추천 결과 저장 (Capsule)
* Vector DB(Qdrant) 기반 검색
* 사용자 기록(Entries) + RAG
* Supabase Auth 연동
* 비용 최적화 (단계별 모델 분리)

## 🧭 Philosophy

> **프롬프트는 명령어가 아니라,
> 사고를 유도하는 구조다.**

이 프로젝트는
“LLM에게 무엇을 시킬까?” 보다
“어떤 사고 순서를 밟게 할까?”를 고민하는 실험입니다.

## 📄 License

MIT (또는 개인 실습용)

## 👤 Author

Hosung AI Lean Stack
(프롬프트 체이닝 & MVP 실험 프로젝트)
