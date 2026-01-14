# LLM Router

## 개요
Rule Router에서 명확한 라우팅 결정을 내리지 못한 경우(confidence < 0.7), LLM을 사용하여 사용자 의도를 분석하고 적절한 라우트를 선택합니다.

## 역할 (Role)
**Travel Request Router** - 사용자의 여행 요청을 분석하여 적절한 실행 경로를 결정하는 라우터

## 입력 (Input)
- `user_input`: 사용자의 자연어 여행 요청

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "route": "full|clarify|candidates_only|itinerary_only",
  "reason": "라우트 선택 이유 (한국어)",
  "missing_fields": ["부족한 필드1", "부족한 필드2"] or [],
  "confidence": 0.0-1.0
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel request router. Analyze the user's travel request and determine the most appropriate route. Return ONLY valid JSON. No markdown.
```

### User Message
```
User travel request:
{user_input}

Determine the appropriate route based on:
- "clarify": Insufficient information (less than 2 key fields: duration, budget, companions, purpose)
- "candidates_only": User explicitly asks for destination candidates only
- "itinerary_only": User asks for itinerary/schedule for a specific destination
- "full": User wants full recommendation (default)

Return JSON schema exactly:
{
  "route": "full|clarify|candidates_only|itinerary_only",
  "reason": "Brief explanation in Korean",
  "missing_fields": ["field1", "field2"] or [],
  "confidence": 0.0-1.0
}
```

## 라우트 선택 기준

### `clarify`
- **조건**: 주요 필드(기간, 예산, 동행, 목적) 중 2개 이하만 감지
- **목적**: 추가 정보 수집

### `candidates_only`
- **조건**: 사용자가 명시적으로 "후보만", "여행지 후보" 등을 요청
- **목적**: Profile + Candidates까지만 실행

### `itinerary_only`
- **조건**: "일정", "코스", "3박4일" 등의 키워드 + 목적지 명시
- **목적**: 특정 목적지의 일정만 생성

### `full`
- **조건**: 위 조건에 해당하지 않는 경우 (기본값)
- **목적**: 전체 4-step 체인 실행

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- `route`는 반드시 4가지 중 하나여야 함
- `confidence`는 0.0-1.0 범위
- `reason`은 한국어로 작성
- `missing_fields`는 배열 (없으면 빈 배열)

## Fallback 처리
- JSON 파싱 실패 시: `clarify` 라우트로 fallback
- 잘못된 route 값: `full` 라우트로 fallback
- LLM 호출 실패: `clarify` 라우트로 fallback

## 사용 시점
Rule Router의 confidence가 0.7 미만일 때만 호출됩니다. 이를 통해 비용을 절감하면서도 애매한 케이스를 정확하게 처리할 수 있습니다.

## 모델 설정
- **모델**: `gpt-4o-mini` (비용 효율적)
- **Temperature**: 0.2 (일관성 확보)
