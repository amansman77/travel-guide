# Step 2: Destination Candidates

## 개요
여행자 프로필을 기반으로 적합한 여행지 후보 5곳을 생성합니다.

## 역할 (Role)
**Travel Curator** - 여행지를 큐레이션하는 전문가

## 입력 (Input)
- `profile`: Step 1에서 생성된 여행자 프로필 JSON

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "candidates": [
    {
      "name": "City, Country",
      "why_fit": ["이유1", "이유2"],
      "watch_out": ["주의사항"],
      "best_length_days": 3
    }
  ]
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel curator. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile JSON:
{profile}

Generate 5 destination candidates that fit.

Return JSON schema:
{
  "candidates": [
    {
      "name": "City, Country",
      "why_fit": ["...","..."],
      "watch_out": ["..."],
      "best_length_days": 3
    }
  ]
}
```

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- 정확히 **5개의 후보**를 생성해야 함
- 각 후보는 여행자 프로필과 적합한 이유를 명시해야 함
- `best_length_days`는 추천 여행 기간 (일수)

## 다음 단계로 전달
이 Step의 출력은 **Step 3: Comparison & Scoring**의 입력으로 사용됩니다.
