from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .structured_itinerary import TripPlan
from .budget_allocation import BudgetAllocation


class TripState(BaseModel):
    user_query: str
    destination: str = ""
    budget: float = 0.0
    days: int = 0
    weather_info: Optional[dict] = None
    itinerary: str = ""
    final_response: str = ""
    budget_status: str = ""
    budget_constraints: Dict[str, Any] = {}
    preferences: List[str] = []
    activity_styles: Dict[str, List[str]] = {}
    critic_feedback: str = ""
    retry_count: int = 0
    structured_plan: Optional[TripPlan] = None

    # New fields for strict control
    plan_valid: bool = False
    attempt_count: int = 0
    preference_weights: Dict[str, float] = {}
    budget_allocation: Optional[BudgetAllocation] = None

    # --- Step 4.1 session memory ---
    user_id: str = "anonymous"
    session_id: str = ""

    # --- Additional field ---
    last_critic_feedback: str = ""
    liked_activities: List[str] = []
    disliked_activities: List[str] = []