# Clarify Chain

## 개요
사용자의 여행 요청이 불충분할 때, 추가 정보를 얻기 위한 질문을 생성합니다.

## 역할 (Role)
**Travel Assistant** - 여행 요구사항을 명확히 하는 어시스턴트

## 입력 (Input)
- `user_input`: 사용자의 자연어 여행 요청
- `missing_fields`: 부족한 필드 목록 (예: "기간, 예산")

## 출력 (Output)
JSON 형식으로 다음 스키마를 정확히 준수해야 합니다:

```json
{
  "questions": [
    "질문 1",
    "질문 2",
    "질문 3"
  ],
  "context": "이 질문들이 필요한 이유에 대한 간단한 설명"
}
```

## 프롬프트 템플릿

### System Message
```
You are a travel assistant. Generate clarifying questions to help understand the user's travel needs. Return ONLY valid JSON. No markdown.
```

### User Message
```
User travel request:
{user_input}

Missing fields that need clarification:
{missing_fields}

Generate 3-5 specific questions in Korean to help clarify the user's travel requirements.
Do NOT provide recommendations, only ask questions.

Return JSON schema exactly:
{
  "questions": [
    "질문 1",
    "질문 2",
    "질문 3"
  ],
  "context": "Brief explanation of why these questions are needed"
}
```

## 제약사항
- **반드시 유효한 JSON만 반환** (마크다운 코드 블록 없음)
- **3-5개의 구체적인 질문** 생성
- **추천 금지**: 질문만 생성하고 추천은 하지 않음
- 모든 질문은 **한국어**로 작성

## 사용 시점
Router가 사용자 입력에서 충분한 정보(기간, 예산, 동행, 목적 중 2개 이하)를 감지하지 못했을 때 실행됩니다.
