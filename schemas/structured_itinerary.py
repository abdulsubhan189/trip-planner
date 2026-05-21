from pydantic import BaseModel
from typing import List, Optional, Literal
from enum import Enum

class ActivityType(str, Enum):
    SIGHTSEEING = "sightseeing"
    ADVENTURE = "adventure"
    CULTURE = "culture"
    RELAXATION = "relaxation"
    FOOD = "food"
    SHOPPING = "shopping"
    NATURE = "nature"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"

class Activity(BaseModel):
    name: str
    location: str
    activity_type: ActivityType
    estimated_cost: float = 0.0
    weather_suitability: Literal["any", "sunny", "indoor", "avoid_cold", "avoid_rain"] = "any"
    confidence_score: float = 0.0  # 0.0–1.0, 1.0 = from knowledge base
    notes: Optional[str] = None

class DayPlan(BaseModel):
    day_number: int
    title: str
    activities: List[Activity]
    total_cost: float = 0.0

class TripPlan(BaseModel):
    destination: str
    days: int
    budget: float
    budget_status: str
    weather_info: dict
    daily_plans: List[DayPlan]
    overall_notes: List[str] = []