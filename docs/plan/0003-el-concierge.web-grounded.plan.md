# travel-concierge.web-grounded.plan.md

## 0. 목적

본 계획서는 기존 **Travel Concierge v2 (Router + Prompt Chaining + Parallel Validators)** 구조에  
**신뢰 도메인 기반 웹 검색(Google Programmable Search Engine)** 을 결합하여,

- LLM의 추정이 아닌 **실제 정보에 근거한 검증**
- 병렬처리가 “필요해서” 자연스럽게 작동하는 구조
- 추천 결과에 **출처(citation)를 포함한 신뢰 가능한 설명**

을 제공하는 **Web-Grounded Travel Concierge** 로 확장하는 것을 목표로 한다.

## 1. 현재 상태 요약 (전제)

- Streamlit 단독 MVP
- AI Agent Router (Rule + LLM fallback)
- Routes: `full`, `clarify`, `candidates_only`, `itinerary_only`
- Full v2:
  1. Traveler Profile
  2. Destination Candidates
  3. Parallel Validators (LLM 기반)
  4. Aggregator
  5. Final Recommendation
- LangSmith Observability 적용 완료

## 2. 확장 목표 (이번 단계)

### 핵심 확장
- Validator 일부를 **Web-Grounded Validator** 로 전환
- Google 검색 API를 통해 **신뢰 도메인에서 정보 수집**
- 수집된 정보를 근거로 LLM이 판단(JSON) 수행
- 결과에 **출처(citations)** 포함

### 이번 단계 범위
- Web-Grounded Validator 1~2개만 적용 (점진적 확장)
  - 1차: `seasonality_weather`
  - 2차: `safety_risk`
- 나머지 validator는 기존 LLM 기반 유지

## 3. 웹 검색 전략

### 3.1 검색 원칙
- LLM이 검색 ❌
- 코드가 검색 → LLM은 **요약/판단만 수행**
- Retrieve → Ground → Judge 패턴 적용

### 3.2 검색 제공자
- **Google Programmable Search Engine (PSE)**
- API: Custom Search JSON API
- 검색 범위는 **PSE에서 신뢰 도메인으로 제한**

## 4. 신뢰 도메인 전략

### 4.1 PSE 분리 전략 (추천)

초기 품질을 위해 **축별 PSE 분리**:

#### PSE-WEATHER
- 목적: 계절/날씨/강수/혼잡도
- 예시 도메인:
  - weather.go.kr
  - bom.gov.au
  - metoffice.gov.uk
  - weather.gov
  - worldweather.wmo.int

#### PSE-SAFETY
- 목적: 여행 안전/주의사항
- 예시 도메인:
  - 0404.go.kr (외교부 해외안전여행)
  - travel.state.gov
  - gov.uk/foreign-travel-advice
  - smartraveller.gov.au
  - who.int

> 초기엔 도메인 수를 10개 이하로 유지해  
> Site Restricted API 전환 가능성도 열어둔다.

## 5. 시스템 구성 변경

### 5.1 환경 변수

```env
GOOGLE_CSE_API_KEY=...
GOOGLE_CSE_CX_WEATHER=...
GOOGLE_CSE_CX_SAFETY=...
````

### 5.2 파일 구조 추가

```
tools/
  google_cse.py        # Google CSE client (search only)
chains/
  validators/
    seasonality_weather.py  # web-grounded
    safety_risk.py          # web-grounded (후속)
docs/
  prompts/
    validators/
      seasonality-weather.md
      safety-risk.md
```

## 6. Web-Grounded Validator 구조

### 6.1 실행 흐름

```
validator(profile, candidate)
  ├─ build_search_queries()
  ├─ web_search (Google CSE)
  ├─ normalize_hits (title, url, snippet)
  └─ llm_judge(snippets) → JSON verdict
```

### 6.2 Validator Output Contract (v2)

```json
{
  "validator": "seasonality_weather",
  "candidate_id": "C1",
  "score": 0.0,
  "verdict": "pass | warn | fail | unknown",
  "reasons": ["..."],
  "citations": [
    {
      "title": "...",
      "url": "...",
      "snippet": "..."
    }
  ],
  "assumptions": [
    "검색 결과 요약 기반",
    "실시간 데이터 아님"
  ]
}
```

## 7. 병렬 처리 설계

### 병렬 축

* 후보 도시 단위 병렬
* validator 단위 병렬
* (선택) 검색 쿼리 단위 병렬

### 동시성 제한 (권장 초기값)

* Web Search: max 5~8
* LLM Judge: max 3~5

### 구현 옵션

* LangChain `RunnableParallel`
* 또는 `asyncio.gather + semaphore`

## 8. Aggregator 확장

Aggregator는 다음을 수행한다:

* 후보별 validator 결과 집계
* 점수/리스크/주의사항 재구성
* citations를 유지한 채 요약

### Aggregator Output (요약)

```json
{
  "ranked_candidates": [...],
  "final_choice": {...},
  "evidence_summary": [
    {
      "axis": "seasonality_weather",
      "sources": ["url1", "url2"]
    }
  ]
}
```

## 9. Observability (LangSmith)

### Metadata / Tags

* `flow=concierge_v2_web`
* `validator=seasonality_weather`
* `candidate_id=C1`
* `search_queries=[...]`
* `num_hits=3`

### 목표

* 검색 → 판단 → 집계 흐름이 트리로 명확히 보일 것
* validator/후보/축별 필터 가능

## 10. UI 변경 (Streamlit)

* 후보 카드:

  * validator별 verdict + score 요약
* Expander:

  * “검증 근거 보기”
  * citation 링크 리스트
* 최종 추천:

  * “왜 이 도시인가” + “주의할 점” + “출처”

## 11. 단계별 작업 계획 (WBS)

### P1. Google CSE Client

* `tools/google_cse.py` 구현
* 표준 SearchHit 반환

### P2. seasonality_weather Web-Grounded 전환

* search → judge 구조 구현
* citations 포함

### P3. 병렬 실행 + 동시성 제한

* validator 병렬화
* rate limit 안정화

### P4. Aggregator 연결

* web-grounded 결과 반영

### P5. LangSmith 태깅

* search/validator 정보 추적

## 12. 테스트 시나리오

1. 3월, 혼자, 4일, 150만원, 해외
2. 여름 성수기 여행
3. 우기/태풍 가능성 있는 지역
4. `candidates_only` / `itinerary_only` 영향 없음 확인

## 13. 완료 기준 (Definition of Done)

* Web-grounded validator 1개 이상 정상 동작
* 검색 출처가 결과에 포함됨
* 병렬 처리로 체감 latency 개선
* LangSmith에서 검색/검증 흐름이 명확히 관측됨
* “실시간 데이터 아님” 가정이 모든 결과에 명시됨

## 14. 철학

> **AI Agent는 판단을 대신하는 존재가 아니라,
> 판단을 돕는 근거를 조직하는 존재다.**

이 단계의 목적은
“더 똑똑해 보이는 추천”이 아니라
**“왜 그렇게 말하는지 설명할 수 있는 추천”이다.
