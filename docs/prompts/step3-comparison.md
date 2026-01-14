# Step 3: Comparison & Scoring

## 개요
여행지 후보들을 비교하고 각 항목별로 점수를 매깁니다.

## 역할 (Role)
**Pragmatic Travel Evaluator** - 실용적인 여행 평가 전문가

## 입력 (Input)
- `profile`: Step 1에서 생성된 여행자 프로필 JSON
- `candidates`: Step 2에서 생성된 후보 도시들 JSON

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "table": [
    {
      "name": "도시명",
      "scores": {
        "fit": 0,
        "cost": 0,
        "walking_friendliness": 0,
        "quietness": 0,
        "cafe_scene": 0
      },
      "summary": "요약 설명"
    }
  ],
  "top2": ["도시1", "도시2"]
}
```

## 프롬프트 템플릿

### System Message
```
You are a pragmatic travel evaluator. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Candidates:
{candidates}

Compare and score each (1-10):
- fit
- cost
- walking_friendliness
- quietness
- cafe_scene

Return JSON schema:
{
  "table": [
    {
      "name": "",
      "scores": {
        "fit": 0,
        "cost": 0,
        "walking_friendliness": 0,
        "quietness": 0,
        "cafe_scene": 0
      },
      "summary": ""
    }
  ],
  "top2": ["",""]
}
```

## 평가 항목
각 후보는 다음 5가지 항목으로 평가됩니다 (1-10점):
1. **fit**: 여행자 프로필과의 적합도
2. **cost**: 비용 효율성
3. **walking_friendliness**: 걷기 편의성
4. **quietness**: 조용함/휴식 가능성
5. **cafe_scene**: 카페 문화/분위기

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- 각 점수는 **1-10 범위**
- `top2`는 점수가 가장 높은 상위 2개 도시

## 다음 단계로 전달
이 Step의 출력은 **Step 4: Final Recommendation**의 입력으로 사용됩니다.
