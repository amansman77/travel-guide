"""Rule-based router for routing user input to appropriate chains."""
import re
from typing import List, Optional
from .types import RouteDecision


def extract_keywords(user_input: str) -> dict:
    """
    Extract key information from user input.
    Returns dict with detected fields.
    """
    user_lower = user_input.lower()
    
    detected = {
        "duration": False,
        "budget": False,
        "companions": False,
        "purpose": False,
        "destination": False,
    }
    
    # Duration detection
    duration_patterns = [
        r'\d+\s*일', r'\d+\s*박\s*\d+\s*일', r'\d+\s*night', r'\d+\s*day',
        r'[가-힣]*\s*박\s*[가-힣]*\s*일', r'[가-힣]*\s*일'
    ]
    if any(re.search(pattern, user_lower) for pattern in duration_patterns):
        detected["duration"] = True
    
    # Budget detection
    budget_patterns = [
        r'\d+[만천]\s*원', r'\d+\s*만원', r'\d+\s*천원', r'budget', r'예산',
        r'\d+[만천]\s*원\s*[이하이상]?', r'[가-힣]*\s*예산'
    ]
    if any(re.search(pattern, user_lower) for pattern in budget_patterns):
        detected["budget"] = True
    
    # Companions detection
    companion_patterns = [
        r'혼자', r'솔로', r'혼자서', r'alone', r'solo',
        r'친구', r'가족', r'연인', r'부부', r'동행', r'with', r'family', r'friend'
    ]
    if any(re.search(pattern, user_lower) for pattern in companion_patterns):
        detected["companions"] = True
    
    # Purpose detection
    purpose_patterns = [
        r'휴식', r'관광', r'여행', r'쇼핑', r'맛집', r'카페', r'걷기', r'힐링',
        r'relax', r'travel', r'tourism', r'shopping', r'food', r'cafe', r'walking'
    ]
    if any(re.search(pattern, user_lower) for pattern in purpose_patterns):
        detected["purpose"] = True
    
    # Destination detection (specific place names)
    destination_patterns = [
        r'[가-힣]+[시도]', r'[가-힣]+[국가]', r'[A-Z][a-z]+\s*[A-Z]?[a-z]*',  # City names
        r'도쿄', r'오사카', r'파리', r'런던', r'뉴욕', r'서울', r'부산',
        r'tokyo', r'osaka', r'paris', r'london', r'new york', r'seoul'
    ]
    if any(re.search(pattern, user_lower) for pattern in destination_patterns):
        detected["destination"] = True
    
    return detected


def route_user_input(user_input: str) -> RouteDecision:
    """
    Route user input to appropriate chain based on rules.
    
    Rules:
    - clarify: Less than 2 key fields detected
    - candidates_only: Keywords like "후보만", "여행지 후보"
    - itinerary_only: Keywords like "일정", "코스", "3박4일" + destination hint
    - full: Default case
    """
    user_lower = user_input.lower()
    detected = extract_keywords(user_input)
    
    # Count detected fields
    field_count = sum([
        detected["duration"],
        detected["budget"],
        detected["companions"],
        detected["purpose"]
    ])
    
    # Rule 1: Clarify - insufficient information
    if field_count <= 2:
        missing_fields = []
        if not detected["duration"]:
            missing_fields.append("기간")
        if not detected["budget"]:
            missing_fields.append("예산")
        if not detected["companions"]:
            missing_fields.append("동행")
        if not detected["purpose"]:
            missing_fields.append("목적")
        
        return RouteDecision(
            route="clarify",
            reason=f"조건 부족 (감지된 필드: {field_count}개)",
            confidence=0.9,
            missing_fields=missing_fields,
            router_type="rule"
        )
    
    # Rule 2: Candidates only - explicit request for candidates
    candidates_keywords = ["후보만", "후보", "여행지 후보", "추천 후보", "candidates", "options"]
    if any(keyword in user_lower for keyword in candidates_keywords):
        return RouteDecision(
            route="candidates_only",
            reason="후보만 요청 키워드 감지",
            confidence=0.95,
            missing_fields=[],
            router_type="rule"
        )
    
    # Rule 3: Itinerary only - explicit request for itinerary with destination
    itinerary_keywords = ["일정", "코스", "스케줄", "itinerary", "schedule", "plan"]
    has_itinerary_keyword = any(keyword in user_lower for keyword in itinerary_keywords)
    
    if has_itinerary_keyword and detected["destination"]:
        return RouteDecision(
            route="itinerary_only",
            reason="일정 요청 + 목적지 명시",
            confidence=0.9,
            missing_fields=[],
            router_type="rule"
        )
    
    # Rule 4: Full chain - default case
    return RouteDecision(
        route="full",
        reason="충분한 조건 + 전체 추천 요청",
        confidence=0.85,
        missing_fields=[],
        router_type="rule"
    )
