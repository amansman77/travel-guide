# Step 1: Traveler Profile

## 개요
사용자의 자연어 입력을 분석하여 구조화된 여행자 프로필을 생성합니다.

## 역할 (Role)
**Travel Analyst** - 여행 요구사항을 분석하는 전문가

## 입력 (Input)
- `user_input`: 사용자의 자연어 여행 요청

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "tags": ["태그1", "태그2"],
  "top_priorities": ["우선순위1", "우선순위2"],
  "constraints": {
    "season": "시기 (예: 3월, 봄)",
    "budget": "예산 (예: 150만원)",
    "companions": "동행 (예: 혼자, 가족, 친구)",
    "pace": "slow|medium|fast",
    "duration_days": 0,
    "domestic_or_international": "domestic|international|either"
  },
  "avoid": ["피하고 싶은 것들"],
  "notes_for_recommender": "추천자에게 전달할 추가 메모"
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel analyst. Return ONLY valid JSON. No markdown.
```

### User Message
```
User travel request:
{user_input}

Return JSON schema exactly:
{
  "tags": ["..."],
  "top_priorities": ["..."],
  "constraints": {
    "season": "",
    "budget": "",
    "companions": "",
    "pace": "slow|medium|fast",
    "duration_days": 0,
    "domestic_or_international": "domestic|international|either"
  },
  "avoid": ["..."],
  "notes_for_recommender": ""
}
```

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- 모든 필드는 필수
- `pace`는 `slow`, `medium`, `fast` 중 하나
- `domestic_or_international`는 `domestic`, `international`, `either` 중 하나

## 다음 단계로 전달
이 Step의 출력은 **Step 2: Destination Candidates**의 입력으로 사용됩니다.
