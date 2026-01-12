"""Type definitions for router module."""
from typing import List, Optional
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    """Route decision made by router."""
    route: str = Field(..., description="Selected route: 'full', 'clarify', 'candidates_only', 'itinerary_only'")
    reason: str = Field(..., description="Reason for route selection")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    missing_fields: List[str] = Field(default_factory=list, description="Missing fields that need clarification")
    router_type: str = Field(default="rule", description="Router type: 'rule' or 'llm'")


class RouteResult(BaseModel):
    """Standardized result payload from chain execution."""
    route: str = Field(..., description="Route that was executed")
    router_reason: str = Field(..., description="Reason for route selection")
    data: dict = Field(..., description="Chain execution result data")
