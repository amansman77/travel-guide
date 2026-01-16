# Aggregator: Validator Results Aggregation

## 개요
각 후보 도시에 대한 5개 Validator 결과를 종합하여, 후보별 종합 점수와 리스크를 재구성하고 최종 TOP1 + 차선 1개를 도출합니다.

## 역할 (Role)
**Travel Recommendation Aggregator** - 검증 결과를 종합하여 최종 추천을 만드는 전문가

## 입력 (Input)
- `profile`: 여행자 프로필 JSON (Step 1 출력)
- `candidates`: 후보 도시들 JSON (Step 2 출력)
- `validators_results`: 모든 Validator 결과 배열
  ```json
  [
    {
      "validator": "budget_fit",
      "candidate_id": "C1",
      "score": 0.8,
      "verdict": "pass",
      "reasons": ["..."],
      ...
    },
    ...
  ]
  ```

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "ranked_candidates": [
    {
      "candidate_id": "C3",
      "name": "도시명",
      "total_score": 0.82,
      "summary": "왜 1등인지 1~2문장",
      "strengths": ["강점1", "강점2"],
      "risks": ["리스크1", "리스크2"],
      "watchouts": ["주의사항1", "주의사항2"]
    }
  ],
  "final_choice": {
    "candidate_id": "C3",
    "name": "도시명",
    "why": ["이유1", "이유2"],
    "what_to_confirm": ["확인사항1", "확인사항2"]
  },
  "disclaimer": "실시간 데이터가 아님을 명시"
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel recommendation aggregator. Synthesize validator results to create a ranked list and final recommendation. Return ONLY valid JSON. No markdown.
```

### User Message
```
Traveler profile:
{profile}

Candidates:
{candidates}

Validator results:
{validators_results}

Task:
1. For each candidate, aggregate all validator scores and verdicts
2. Calculate a total_score (weighted average or your method)
3. Rank candidates by total_score
4. Select the top candidate as final_choice
5. Provide a second choice (runner-up) in ranked_candidates

For each ranked candidate, include:
- total_score: 0.0-1.0
- summary: Why this candidate ranks at this position (1-2 sentences)
- strengths: Key positive points from validators
- risks: Key concerns or warnings from validators
- watchouts: Important things to be aware of

For final_choice, include:
- why: Top 2-3 reasons this is the best choice
- what_to_confirm: Questions or confirmations needed before finalizing

IMPORTANT:
- All validator results are based on general knowledge, NOT real-time data
- Include this disclaimer in the output

Return JSON schema exactly:
{
  "ranked_candidates": [
    {
      "candidate_id": "",
      "name": "",
      "total_score": 0.0,
      "summary": "",
      "strengths": ["..."],
      "risks": ["..."],
      "watchouts": ["..."]
    }
  ],
  "final_choice": {
    "candidate_id": "",
    "name": "",
    "why": ["..."],
    "what_to_confirm": ["..."]
  },
  "disclaimer": "실시간 데이터가 아님을 명시"
}
```

## 종합 방법
1. **점수 계산**: 각 validator의 score를 종합 (평균 또는 가중평균)
2. **verdict 반영**: `fail` verdict가 있으면 감점, `warn`은 주의 표시
3. **리스크 종합**: 모든 validator의 risks/reasons를 종합
4. **순위 결정**: total_score 기준 내림차순 정렬

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **실시간 데이터 아님 명시**: disclaimer 필드에 반드시 포함
- `ranked_candidates`는 최소 2개 이상 (TOP1 + 차선)
- `total_score`는 0.0-1.0 범위

## 실패 처리
- JSON 파싱 실패 시 1회 repair 시도
- 실패 시 기본 구조 반환 (모든 후보를 동일 점수로 처리)

## 다음 단계로 전달
이 Aggregator의 출력은 **Final (v2)**의 입력으로 사용됩니다.