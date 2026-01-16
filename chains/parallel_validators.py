"""Parallel validators execution."""
import asyncio
import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

from chains.validators import (
    build_budget_fit_validator,
    run_budget_fit_validator,
    build_vibe_fit_validator,
    run_vibe_fit_validator,
    build_transit_complexity_validator,
    run_transit_complexity_validator,
    build_safety_risk_validator,
    run_safety_risk_validator,
    build_safety_risk_web_validator,
    run_safety_risk_web_validator,
    build_seasonality_weather_validator,
    run_seasonality_weather_validator,
    build_seasonality_weather_web_validator,
    run_seasonality_weather_web_validator,
)

# Try to import Google CSE (optional)
try:
    from tools.google_cse import GoogleCSE
    HAS_GOOGLE_CSE = True
except ImportError:
    HAS_GOOGLE_CSE = False
    GoogleCSE = None

try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator


# Validator configurations
# Use web-grounded validator if Google CSE is available, otherwise fallback to LLM-only
def get_validators(use_web_grounded: bool = True):
    """
    Get validator configurations.
    
    Args:
        use_web_grounded: If True, use web-grounded validators when available
    
    Returns:
        List of (validator_name, build_func, run_func) tuples
    """
    validators = [
        ("budget_fit", build_budget_fit_validator, run_budget_fit_validator),
        ("vibe_fit", build_vibe_fit_validator, run_vibe_fit_validator),
        ("transit_complexity", build_transit_complexity_validator, run_transit_complexity_validator),
    ]
    
    # Use web-grounded validators if available
    if use_web_grounded and HAS_GOOGLE_CSE:
        # Check if Google CSE credentials are available
        has_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY")
        has_weather_cx = os.getenv("GOOGLE_CSE_CX_WEATHER")
        has_safety_cx = os.getenv("GOOGLE_CSE_CX_SAFETY")
        
        # Use web-grounded safety_risk if Safety PSE is available, otherwise use LLM-only
        if has_cse_api_key and (has_safety_cx or has_weather_cx):
            validators.append(("safety_risk", build_safety_risk_web_validator, run_safety_risk_web_validator))
        else:
            validators.append(("safety_risk", build_safety_risk_validator, run_safety_risk_validator))
        
        # Use web-grounded seasonality_weather if Weather PSE is available
        if has_cse_api_key and has_weather_cx:
            validators.append(("seasonality_weather", build_seasonality_weather_web_validator, run_seasonality_weather_web_validator))
        else:
            validators.append(("seasonality_weather", build_seasonality_weather_validator, run_seasonality_weather_validator))
    else:
        # Fallback to LLM-only validators
        validators.append(("safety_risk", build_safety_risk_validator, run_safety_risk_validator))
        validators.append(("seasonality_weather", build_seasonality_weather_validator, run_seasonality_weather_validator))
    
    return validators


async def run_validator_async(
    validator_name: str,
    validator_chain: Any,
    run_validator_func: callable,
    profile: Dict,
    candidate: Dict,
    candidate_id: str,
    semaphore: asyncio.Semaphore,
    cse_client: Optional[Any] = None
) -> Dict:
    """
    Run a single validator asynchronously with semaphore control.
    
    Args:
        validator_name: Name of the validator
        validator_chain: Validator chain instance
        run_validator_func: Function to run the validator
        profile: Traveler profile
        candidate: Candidate destination
        candidate_id: Candidate ID
        semaphore: Semaphore for concurrency control
        cse_client: Optional Google CSE client for web-grounded validators
    """
    async with semaphore:
        try:
            # Run validator in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Web-grounded validators need CSE client
            if validator_name in ("seasonality_weather", "safety_risk") and cse_client is not None:
                result = await loop.run_in_executor(
                    None,
                    run_validator_func,
                    validator_chain,
                    cse_client,
                    profile,
                    candidate,
                    candidate_id
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    run_validator_func,
                    validator_chain,
                    profile,
                    candidate,
                    candidate_id
                )
            
            # Add metadata for LangSmith
            result["_validator_name"] = validator_name
            result["_candidate_id"] = candidate_id
            
            return result
        except Exception as e:
            # Graceful error handling
            return {
                "validator": validator_name,
                "candidate_id": candidate_id,
                "score": 0.0,
                "verdict": "fail",
                "reasons": [f"검증 실패: {str(e)}"],
                "assumptions": ["실시간 데이터 아님"],
                "questions_to_user": [],
                "citations": [],
                "_validator_name": validator_name,
                "_candidate_id": candidate_id,
            }


async def run_parallel_validators_async(
    llm: ChatOpenAI,
    parser: JsonOutputParser,
    profile: Dict,
    candidates: List[Dict],
    max_concurrent: int = 5,
    use_web_grounded: bool = True
) -> List[Dict]:
    """
    Run all validators for all candidates in parallel with concurrency control.
    
    Args:
        llm: LLM instance
        parser: JSON parser
        profile: Traveler profile
        candidates: List of candidate destinations
        max_concurrent: Maximum concurrent validator runs (default: 5)
        use_web_grounded: If True, use web-grounded validators when available
    
    Returns:
        List of all validator results
    """
    # Initialize Google CSE client if available
    cse_client = None
    if use_web_grounded and HAS_GOOGLE_CSE:
        try:
            cse_client = GoogleCSE()
        except (ValueError, Exception):
            # CSE not configured, fallback to LLM-only
            cse_client = None
    
    # Get validator configurations
    validators = get_validators(use_web_grounded=use_web_grounded)
    
    # Build all validator chains
    validator_chains = {}
    validator_runners = {}
    
    for validator_name, build_func, run_func in validators:
        validator_chains[validator_name] = build_func(llm, parser)
        validator_runners[validator_name] = run_func
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Generate candidate IDs
    candidate_ids = [f"C{i+1}" for i in range(len(candidates))]
    
    # Create all tasks: candidates × validators
    tasks = []
    for candidate_idx, candidate in enumerate(candidates):
        candidate_id = candidate_ids[candidate_idx]
        for validator_name, build_func, run_func in validators:
            task = run_validator_async(
                validator_name,
                validator_chains[validator_name],
                validator_runners[validator_name],
                profile,
                candidate,
                candidate_id,
                semaphore,
                cse_client
            )
            tasks.append(task)
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    validated_results = []
    for result in results:
        if isinstance(result, Exception):
            validated_results.append({
                "validator": "unknown",
                "candidate_id": "unknown",
                "score": 0.0,
                "verdict": "fail",
                "reasons": [f"예외 발생: {str(result)}"],
                "assumptions": ["실시간 데이터 아님"],
                "questions_to_user": [],
                "citations": [],
            })
        else:
            validated_results.append(result)
    
    return validated_results


def run_parallel_validators(
    llm: ChatOpenAI,
    parser: JsonOutputParser,
    profile: Dict,
    candidates: List[Dict],
    max_concurrent: int = 5,
    use_web_grounded: bool = True
) -> List[Dict]:
    """
    Synchronous wrapper for parallel validators execution.
    
    Args:
        llm: LLM instance
        parser: JSON parser
        profile: Traveler profile
        candidates: List of candidate destinations
        max_concurrent: Maximum concurrent validator runs (default: 5)
        use_web_grounded: If True, use web-grounded validators when available
    
    Returns:
        List of all validator results
    """
    # Create new event loop if needed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run async function
    return loop.run_until_complete(
        run_parallel_validators_async(llm, parser, profile, candidates, max_concurrent, use_web_grounded)
    )