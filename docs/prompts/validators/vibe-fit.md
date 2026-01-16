# Validator: Vibe Fit

## 개요
후보 도시가 여행자의 취향과 선호도에 적합한지 검증합니다. 조용함, 카페 문화, 걷기 편의성, 자연 환경 등을 평가합니다.

## 역할 (Role)
**Vibe Analyst** - 여행지 분위기와 취향 적합성을 분석하는 전문가

## 입력 (Input)
- `profile`: 여행자 프로필 JSON (Step 1 출력)
- `candidate`: 후보 도시 정보 (name, why_fit, watch_out 등)
- `candidate_id`: 후보 식별자 (예: "C1", "C2")

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "validator": "vibe_fit",
  "candidate_id": "C1",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["이유1", "이유2"],
  "assumptions": ["실시간 데이터 아님", "일반적인 도시 특성 기준"],
  "questions_to_user": ["추가 확인 질문(optional)"]
}
```

## 프롬프트 템플릿

### System Message
```
You are a vibe analyst for travel recommendations. Evaluate if the destination matches the traveler's preferences and vibe. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Evaluate vibe fit considering:
- Quietness/peacefulness (if traveler prefers quiet)
- Cafe culture and coffee scene
- Walkability and pedestrian-friendly areas
- Natural environment (parks, nature spots)
- Overall atmosphere matching traveler's pace (slow/medium/fast)

Focus on:
- Does the city match the traveler's top priorities?
- Does it avoid what the traveler wants to avoid?
- Is the pace/atmosphere suitable?

Return JSON schema exactly:
{
  "validator": "vibe_fit",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": []
}

Scoring:
- score: 0.0-1.0 (1.0 = perfect match, 0.0 = poor match)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
```

## 평가 기준
1. **조용함**: 여행자가 조용한 휴식을 선호하는 경우
2. **카페 문화**: 카페 위주 여행을 선호하는 경우
3. **걷기 편의성**: 걷기 중심 여행을 선호하는 경우
4. **자연 환경**: 자연/공원 선호도
5. **전체 분위기**: 여행자의 pace (slow/medium/fast)와의 적합성

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **실시간 데이터 아님 명시**: assumptions에 반드시 포함
- `score`는 0.0-1.0 범위
- `verdict`는 `pass`, `warn`, `fail` 중 하나

## 실패 처리
- JSON 파싱 실패 시 1회 repair 시도
- 실패 시 `verdict: "fail"`, `score: 0.0`, `reasons: ["검증 실패"]` 반환

## 다음 단계로 전달
이 Validator의 출력은 **Aggregator**의 입력으로 사용됩니다.