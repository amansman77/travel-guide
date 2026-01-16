# travel-concierge.plan.md

## 0. 목표

현재 **Travel Guide MVP (Router + Prompt Chaining + LangSmith)** 를 기반으로,
주제를 **“여행 추천” → “여행 설계 + 검증(Travel Concierge)”** 으로 확장한다.

핵심 추가 가치는 다음 1가지다:

- **후보 도시 추천 이후, 병렬 검증(Parallel Validators)으로 품질/신뢰도를 높이고**
- **검증 결과를 합의(Aggregation)하여 최종 추천을 만든다.**

## 1. 현재 상태(전제)

- Streamlit 단독 앱
- Router: Rule Router + LLM Router (fallback)
- Routes: `full`, `clarify`, `candidates_only`, `itinerary_only`
- Full chain: STEP1~STEP4 (Profile → Candidates → Comparison → Final)
- LangSmith 추적 및 route tag 필터링 가능

## 2. 확장 MVP 정의 (Travel Concierge v2)

### v2 Full Flow(핵심)
1) Traveler Profile
2) Destination Candidates
3) **Parallel Validators (NEW)**  ← 병렬 처리 핵심
4) Aggregator (NEW)
5) Final Recommendation (+ Itinerary)

### 병렬 검증(Parallel Validators) 목표
후보 도시 3~5개에 대해 “그럴듯한 추천”이 아니라,
**조건/제약을 검증한 추천**이 되도록 근거를 붙인다.

검증 축(기본 5개):
- `budget_fit` : 예산 적합성 (숙박/식비/교통 난이도 관점)
- `vibe_fit` : 취향 적합성 (조용함/카페/걷기/자연 등)
- `transit_complexity` : 이동 난이도/동선 스트레스
- `safety_risk` : 치안/사기/야간 활동 리스크(일반적 주의사항 수준)
- `seasonality_weather` : 입력 시기 기준 계절/날씨/혼잡도(추정 + 주의사항)

> 주의: 웹 크롤링/실시간 데이터는 이번 MVP에서 제외한다. (추후 확장)

## 3. 라우팅 정책(v2)

기존 라우트 유지 + v2 라우트 1개 추가(선택)

### 유지
- `clarify` : 정보 부족 시 질문 3~5개
- `candidates_only` : Profile + Candidates 출력
- `itinerary_only` : 일정만 생성
- `full` : 전체 실행

### 추가(선택)
- `verify_only` : 이미 후보가 주어졌을 때 검증만 수행  
  - 예: “도쿄/오사카/후쿠오카 중 어디가 더 맞을까? 검증해줘”
  - 입력에 후보 리스트가 포함되면 라우팅 가능

## 4. 체인 설계(v2)

### 4.1 Full Chain v2 (추천)
- STEP1: `profile` (기존)
- STEP2: `candidates` (기존) → 후보 5개 생성
- STEP3: `parallel_validators` (NEW)
- STEP4: `aggregator` (NEW)
- STEP5: `final` (기존 step4를 v2 final로 확장)

### 4.2 병렬 실행 단위
- 병렬은 “validator 단위”로 한다.
- 각 validator는 **(profile + candidate + context)** 를 입력으로 받아, **JSON 결과**를 반환한다.

#### Validator Output Contract (공통)
```json
{
  "validator": "budget_fit | vibe_fit | transit_complexity | safety_risk | seasonality_weather",
  "candidate_id": "C1",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["...","..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": ["추가 확인 질문(optional)"]
}
````

### 4.3 Aggregator 역할

* 후보별 validator 결과를 모아,
* 후보별 종합 점수/리스크/추천 이유를 재구성하고,
* “최종 TOP1 + 차선 1개”를 만든다.

Aggregator Output Contract

```json
{
  "ranked_candidates": [
    {
      "candidate_id": "C3",
      "total_score": 0.82,
      "summary": "왜 1등인지 1~2문장",
      "strengths": ["..."],
      "risks": ["..."],
      "watchouts": ["..."]
    }
  ],
  "final_choice": {
    "candidate_id": "C3",
    "why": ["...","..."],
    "what_to_confirm": ["..."]
  }
}
```

### 4.4 Final(v2)

* Aggregator 결과를 받아:

  * 최종 추천 서사(짧게)
  * 3박4일 일정(기존과 동일)
  * “검증 근거 요약(validator 핵심)”을 붙인다.

## 5. 구현 작업 계획(WBS)

### P1. Spec 문서 추가(필수)

* `docs/prompts/validators/` 폴더 생성

  * `budget-fit.md`
  * `vibe-fit.md`
  * `transit-complexity.md`
  * `safety-risk.md`
  * `seasonality-weather.md`
* `docs/prompts/aggregator.md` 생성
* README Mermaid에 validator/aggregator 노드 추가 + spec 링크 연결

**Acceptance**

* 각 spec에 input/output schema, 금지 규칙, 실패 처리 문구 포함

### P2. Validator 체인 구현(필수)

* `chains/validators/` 추가

  * 각 validator chain 파일 분리
  * 공통 parser / json repair(1회) 적용
* 모델/temperature 기본값:

  * validator는 `mini`급 모델 + temperature 낮게(0~0.2) 권장

**Acceptance**

* validator 1개 단독 실행 가능
* JSON 계약 위반 시 1회 repair 후 실패면 graceful error

### P3. 병렬 실행(핵심)

* `chains/parallel_validators.py` 추가
* 후보 5개 × validator 5개 = 25 runs

  * 초기엔 동시성 제한(예: 5~8) 적용
  * OpenAI rate limit 방지

구현 옵션:

* LangChain `RunnableParallel` + 내부 chunking
* 또는 `asyncio.gather` + semaphore

**Acceptance**

* LangSmith에서 validator들이 병렬로 실행된 것이 트리/타임라인으로 확인 가능
* 전체 latency가 직렬 대비 의미 있게 감소(체감 목표)

### P4. Aggregator 추가(필수)

* `chains/aggregator.py` 추가
* 입력: candidates + validators outputs
* 출력: ranked_candidates + final_choice

**Acceptance**

* ranked list + 근거 요약이 일관되게 생성됨
* “실시간 데이터가 아님”을 명시하는 문구가 포함됨

### P5. Full Chain v2 조립(필수)

* `chains/full_chain.py`에 v2 flow 도입 (v1 유지 또는 교체)
* Router에서 `full` 선택 시 v2 실행

**Acceptance**

* `full` 실행 결과에 “검증 요약” 섹션이 포함됨
* 기존 `candidates_only`, `itinerary_only`, `clarify`는 영향 없음

### P6. Observability 개선(권장)

LangSmith metadata/tags:

* `route:<...>`
* `flow:concierge_v2`
* validator run에:

  * `validator:<name>`
  * `candidate_id:C1` 등

**Acceptance**

* LangSmith에서 validator별/후보별 필터링이 가능

### P7. UI 개선(권장)

Streamlit 출력 레이아웃:

* 후보별 카드(도시명)

  * validator 요약 테이블(score/verdict)
* 최종 추천 카드
* (옵션) “검증 근거 펼치기” expander

**Acceptance**

* 사용자가 “왜 이 도시인지”를 10초 내 이해 가능

## 6. 품질/안정성 규칙

* 모든 단계 JSON only
* 모든 단계 “실시간 데이터 아님”을 전제(validator/aggregator에서 명시)
* 금지:

  * 항공권/숙소의 구체 가격 단정
  * 안전/치안에 대한 과도한 공포 조장
* 에러:

  * validator 실패 시 해당 축을 `unknown` 처리하고 aggregator가 감점/주의로 반영

## 7. 테스트 시나리오(최소)

1. Full v2 (해외, 3월, 혼자, 4일, 150만원, 조용+카페+걷기)
2. Full v2 (가족/아이 동반, 예산 제한)
3. candidates_only (변경 없음 확인)
4. itinerary_only (변경 없음 확인)
5. clarify (변경 없음 확인)
6. (선택) verify_only: 후보 3개 입력 후 검증만 수행

## 8. 완료 기준(Definition of Done)

* Full route에서:

  * 후보 5개 생성
  * validator 병렬 검증 수행
  * aggregator가 TOP1 + 차선 1개 도출
  * final 결과에 검증 근거 요약 포함
* LangSmith에서:

  * Router → Full v2 → Parallel validators → Aggregator → Final 흐름이 보임
  * tags로 validator/candidate 필터 가능
* 비용/성능:

  * 동시성 제한 적용되어 rate limit 에러가 거의 없음
  * 직렬 대비 체감 latency 개선

## 9. 추후 확장(Out of MVP)

* 실시간 데이터 연동(날씨/환율/혼잡도)용 FastAPI 분리
* 사용자 선호/기록 저장 + 재추천
* Eval(라우팅 정확도, validator 신뢰도) 자동화
* LangGraph 전환(그래프 선언 + 자동 시각화)
