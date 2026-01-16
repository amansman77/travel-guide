# Validator: Budget Fit

## 개요
후보 도시가 여행자의 예산 제약에 적합한지 검증합니다. 숙박, 식비, 교통비의 난이도를 종합적으로 평가합니다.

## 역할 (Role)
**Budget Analyst** - 여행 예산 적합성을 분석하는 전문가

## 입력 (Input)
- `profile`: 여행자 프로필 JSON (Step 1 출력)
- `candidate`: 후보 도시 정보 (name, why_fit, watch_out 등)
- `candidate_id`: 후보 식별자 (예: "C1", "C2")

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "validator": "budget_fit",
  "candidate_id": "C1",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["이유1", "이유2"],
  "assumptions": ["실시간 데이터 아님", "평균 숙박/식비 기준"],
  "questions_to_user": ["추가 확인 질문(optional)"]
}
```

## 프롬프트 템플릿

### System Message
```
You are a budget analyst for travel recommendations. Evaluate if the destination fits the traveler's budget constraints. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Candidate destination:
{candidate}

Candidate ID: {candidate_id}

Evaluate budget fit considering:
- Accommodation costs (average range)
- Food/dining costs
- Transportation costs
- Overall cost of living

Constraints:
- Do NOT provide specific prices (no real-time data)
- Use general cost ranges (budget-friendly, moderate, expensive)
- Consider the traveler's stated budget from profile

Return JSON schema exactly:
{
  "validator": "budget_fit",
  "candidate_id": "",
  "score": 0.0,
  "verdict": "pass | warn | fail",
  "reasons": ["..."],
  "assumptions": ["실시간 데이터 아님", "..."],
  "questions_to_user": []
}

Scoring:
- score: 0.0-1.0 (1.0 = perfect fit, 0.0 = poor fit)
- verdict: "pass" (score >= 0.7), "warn" (0.4 <= score < 0.7), "fail" (score < 0.4)
```

## 평가 기준
1. **숙박비**: 여행자 예산 대비 적정 수준인가
2. **식비**: 일일 식비가 예산 범위 내인가
3. **교통비**: 도시 내 이동 및 주요 관광지 접근 비용
4. **전체 비용**: 총 예산 대비 여유가 있는가

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **구체적인 가격 금지**: "호텔 10만원" 같은 단정 금지
- **실시간 데이터 아님 명시**: assumptions에 반드시 포함
- `score`는 0.0-1.0 범위
- `verdict`는 `pass`, `warn`, `fail` 중 하나

## 실패 처리
- JSON 파싱 실패 시 1회 repair 시도
- 실패 시 `verdict: "fail"`, `score: 0.0`, `reasons: ["검증 실패"]` 반환

## 다음 단계로 전달
이 Validator의 출력은 **Aggregator**의 입력으로 사용됩니다.