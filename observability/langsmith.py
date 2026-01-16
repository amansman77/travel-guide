"""LangSmith observability helpers for tagging and metadata."""
import os
import hashlib
import uuid
from typing import Dict, Any
try:
    from langsmith import traceable
except ImportError:
    # Fallback if langsmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator

from router.types import RouteDecision


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def hash_user_input(user_input: str) -> str:
    """Generate hash of user input for comparison."""
    return hashlib.sha256(user_input.encode()).hexdigest()[:16]


def trace_router_decision(route_decision: RouteDecision, user_input: str) -> Dict[str, Any]:
    """
    Generate router decision metadata for LangSmith.
    This is called within the unified trace, not as a separate trace.
    """
    request_id = generate_request_id()
    user_input_hash = hash_user_input(user_input)
    
    # Add flow tag for v2
    tags = [
        f"route:{route_decision.route}",
        f"router:{route_decision.router_type}",
    ]
    
    # Add v2 flow tag if full route
    if route_decision.route == "full":
        # Check if web-grounded validators are enabled
        use_web_grounded = os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_CX_WEATHER")
        if use_web_grounded:
            tags.append("flow:concierge_v2_web")
        else:
            tags.append("flow:concierge_v2")
    
    # Return metadata for LangSmith
    return {
        "route": route_decision.route,
        "router_type": route_decision.router_type,
        "reason": route_decision.reason,
        "confidence": route_decision.confidence,
        "request_id": request_id,
        "user_input_hash": user_input_hash,
        "tags": tags,
        "metadata": {
            "missing_fields": route_decision.missing_fields,
            "confidence": route_decision.confidence,
        }
    }


def get_chain_tags(route: str, router_type: str) -> list:
    """Get tags for chain execution."""
    return [
        f"route:{route}",
        f"router:{router_type}",
    ]


def get_chain_metadata(route: str, router_type: str, request_id: str = None) -> dict:
    """Get metadata for chain execution."""
    metadata = {
        "route": route,
        "router_type": router_type,
    }
    if request_id:
        metadata["request_id"] = request_id
    return metadata
