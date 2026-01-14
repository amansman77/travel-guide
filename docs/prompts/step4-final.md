# Step 4: Final Recommendation + Itinerary

## 개요
최종 추천 여행지를 선택하고 3박 4일 일정을 생성합니다.

## 역할 (Role)
**Travel Planner** - 여행 계획을 세우는 전문가

## 입력 (Input)
- `profile`: Step 1에서 생성된 여행자 프로필 JSON
- `comparison`: Step 3에서 생성된 비교 및 점수 JSON

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다 (한국어):

```json
{
  "winner": {
    "name": "도시명",
    "why": ["이유1", "이유2"],
    "best_area_to_stay": "추천 숙박 지역",
    "budget_tip": "예산 팁"
  },
  "itinerary": [
    {"day": 1, "morning": "", "afternoon": "", "evening": ""},
    {"day": 2, "morning": "", "afternoon": "", "evening": ""},
    {"day": 3, "morning": "", "afternoon": "", "evening": ""},
    {"day": 4, "morning": "", "afternoon": "", "evening": ""}
  ]
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel planner. Return ONLY valid JSON in Korean. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Comparison:
{comparison}

Pick the best destination and propose a 3-night 4-day plan.
Be realistic and avoid exaggeration.

Return JSON schema:
{
  "winner": {
    "name": "",
    "why": ["...","..."],
    "best_area_to_stay": "",
    "budget_tip": ""
  },
  "itinerary": [
    {"day": 1, "morning":"", "afternoon":"", "evening":""},
    {"day": 2, "morning":"", "afternoon":"", "evening":""},
    {"day": 3, "morning":"", "afternoon":"", "evening":""},
    {"day": 4, "morning":"", "afternoon":"", "evening":""}
  ]
}
```

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **모든 텍스트는 한국어로 작성**
- 일정은 **3박 4일** (4일치)
- 각 일정은 `morning`, `afternoon`, `evening`으로 구분
- **현실적이고 과장 없는** 추천

## 최종 출력
이 Step의 출력이 사용자에게 최종 결과로 전달됩니다.
