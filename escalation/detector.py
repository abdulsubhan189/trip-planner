# escalation/detector.py
from typing import Tuple, Dict, Any
from schemas import TripState

MAX_ATTEMPTS = 3  # same as in graph

def should_escalate(result: Dict[str, Any], state: TripState) -> Tuple[bool, str]:
    """
    Determine if a planning result needs manual escalation.
    Returns (should_escalate, reason).
    """
    # 1. Destination missing
    if not state.destination:
        return True, "Destination not resolved"

    # 2. Fallback response returned (itinerary present instead of structured plan)
    if "itinerary" in result:
        return True, "Fallback response returned"

    # 3. Max retries reached
    if state.attempt_count >= MAX_ATTEMPTS:
        return True, f"Max retries reached ({state.attempt_count})"

    # 4. Low plan score
    plan_score = result.get("plan_score")
    if plan_score is not None and plan_score < 4.0:
        return True, f"Low quality plan (score {plan_score:.1f})"

    # No escalation needed
    return False, ""