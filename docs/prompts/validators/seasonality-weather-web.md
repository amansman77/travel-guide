# Validator: Seasonality & Weather (Web-Grounded)

## 개요
입력 시기 기준으로 후보 도시의 계절, 날씨, 혼잡도를 평가합니다. **Google CSE를 통해 신뢰 도메인에서 실제 정보를 검색**하여 근거 기반 평가를 수행합니다.

## 역할 (Role)
**Seasonality Analyst (Web-Grounded)** - 웹 검색 결과를 기반으로 여행 시기와 계절 적합성을 분석하는 전문가

## 입력 (Input)
- `profile`: 여행자 프로필 JSON (Step 1 출력, season 정보 포함)
- `candidate`: 후보 도시 정보 (name, why_fit, watch_out 등)
- `candidate_id`: 후보 식별자 (예: "C1", "C2")
- `search_results`: Google CSE 검색 결과 (title, url, snippet)

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "validator": "seasonality_weather",
  "candidate_id": "C1",
  "score": 0.0,
  "verdict": "pass | warn | fail | unknown",
  "reasons": ["이유1", "이유2"],
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
  ],
  "questions_to_user": ["추가 확인 질문(optional)"]
}
```

## 실행 흐름

1. **검색 쿼리 생성**: `build_search_queries(profile, candidate, season)`
   - 예: "{destination} {season} weather climate"
   - 예: "{destination} {season} tourist season crowd level"
   - 예: "{destination} best time to visit {season}"

2. **웹 검색**: Google CSE (Weather PSE)를 통해 검색
   - 신뢰 도메인: weather.go.kr, bom.gov.au, metoffice.gov.uk, weather.gov 등
   - 최대 5개 결과 수집

3. **LLM 판단**: 검색 결과를 기반으로 LLM이 평가
   - 검색 결과의 정보를 근거로 판단
   - 검색 결과에 없는 정보는 추정하지 않음

4. **Citations 포함**: 검색 결과를 citations로 포함

## 프롬프트 템플릿

### System Message
```
You are a seasonality analyst for travel recommendations. Evaluate the destination's weather, season, and crowd levels based on the provided web search results. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Travel period: {season}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Web search results:
{search_results}

Evaluate seasonality and weather based on the search results:
- Typical weather conditions for the travel period
- Temperature and climate comfort
- Rainfall/precipitation patterns
- Tourist crowd levels (high/medium/low season)
- Seasonal events or festivals
- Best/worst aspects of visiting during this period

IMPORTANT:
- Base your evaluation on the provided search results
- Cite specific information from the search results in your reasons
- If search results are insufficient, note it in assumptions
- Do NOT make up information not found in search results

Return JSON schema exactly:
{
  "validator": "seasonality_weather",
  "candidate_id": "",
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
  ],
  "questions_to_user": []
}

Scoring:
- score: 0.0-1.0 (1.0 = perfect season, 0.0 = poor season)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4), "unknown" (insufficient data)
- citations: Include relevant search results that support your evaluation
```

## 평가 기준
1. **날씨 적합성**: 검색 결과에서 확인된 여행 시기의 날씨 정보
2. **온도/기후**: 검색 결과 기반 온도/기후 평가
3. **강수량**: 검색 결과에서 확인된 강수 패턴
4. **혼잡도**: 검색 결과에서 확인된 관광객 혼잡도 정보
5. **계절적 특성**: 검색 결과 기반 해당 시기의 장단점

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **검색 결과 기반 평가**: 검색 결과에 없는 정보는 추정하지 않음
- **Citations 필수**: 검색 결과를 citations에 포함
- **실시간 데이터 아님 명시**: assumptions에 반드시 포함
- `score`는 0.0-1.0 범위
- `verdict`는 `pass`, `warn`, `fail`, `unknown` 중 하나

## 실패 처리
- 검색 실패 시: `verdict: "unknown"`, `citations: []`
- JSON 파싱 실패 시: 1회 repair 시도
- 실패 시 `verdict: "unknown"`, `score: 0.0`, `reasons: ["검증 실패"]` 반환

## 다음 단계로 전달
이 Validator의 출력은 **Aggregator**의 입력으로 사용되며, citations는 `evidence_summary`에 포함됩니다.