# Candidates Only Chain

## 개요
사용자가 여행지 후보만 요청한 경우, Profile과 Candidates 단계까지만 실행합니다. Comparison과 Final 단계는 건너뜁니다.

## 역할 (Role)
**Travel Curator** - 여행지 후보를 큐레이션하는 전문가

## 입력 (Input)
- `user_input`: 사용자의 자연어 여행 요청

## 실행 단계

이 Chain은 다음 2단계로 구성됩니다:

1. **STEP 1: Traveler Profile** - [프롬프트 명세](step1-profile.md)
2. **STEP 2: Destination Candidates** - [프롬프트 명세](step2-candidates.md)

## 출력 (Output)

```json
{
  "profile": {
    "tags": ["..."],
    "top_priorities": ["..."],
    "constraints": {...},
    "avoid": ["..."],
    "notes_for_recommender": ""
  },
  "candidates": {
    "candidates": [
      {
        "name": "City, Country",
        "why_fit": ["...","..."],
        "watch_out": ["..."],
        "best_length_days": 3
      }
    ]
  }
}
```

## 프롬프트 구조

### Step 1: Traveler Profile
- **프롬프트 명세**: [step1-profile.md](step1-profile.md)
- **입력**: `user_input`
- **출력**: Profile JSON

### Step 2: Destination Candidates
- **프롬프트 명세**: [step2-candidates.md](step2-candidates.md)
- **입력**: Step 1의 Profile JSON
- **출력**: Candidates JSON

## 제약사항
- **Comparison 단계 실행 안 함**: 후보 비교 및 점수화는 수행하지 않음
- **Final 단계 실행 안 함**: 최종 추천 및 일정 생성은 수행하지 않음
- **Profile + Candidates만 반환**: 사용자가 요청한 후보 정보만 제공

## 사용 시점
Router가 다음 키워드를 감지했을 때 실행됩니다:
- "후보만"
- "후보"
- "여행지 후보"
- "추천 후보"
- "candidates"
- "options"

## Full Chain과의 차이점

| 항목 | Candidates Only | Full Chain |
|------|----------------|------------|
| Step 1 (Profile) | ✅ 실행 | ✅ 실행 |
| Step 2 (Candidates) | ✅ 실행 | ✅ 실행 |
| Step 3 (Comparison) | ❌ 건너뜀 | ✅ 실행 |
| Step 4 (Final) | ❌ 건너뜀 | ✅ 실행 |

이를 통해 사용자가 후보만 원할 때 불필요한 LLM 호출을 줄여 비용을 절감할 수 있습니다.
