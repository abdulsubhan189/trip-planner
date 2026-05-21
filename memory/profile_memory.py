# memory/profile_memory.py
from datetime import datetime
from typing import Dict, List, Optional
from database.models import SessionLocal, UserProfile

def load_profile(user_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return None
        return {
            "user_id": profile.user_id,
            "created_at": profile.created_at.isoformat(),
            "last_active": profile.last_active.isoformat(),
            "total_trips": profile.total_trips,
            "preferred_destinations": profile.preferred_destinations or [],
            "preferences": profile.preferences or [],
            "average_budget": profile.average_budget,
            "average_days": profile.average_days,
            "budget_style": profile.budget_style
        }
    finally:
        db.close()

def create_profile(user_id: str) -> Dict:
    db = SessionLocal()
    try:
        profile = UserProfile(
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            total_trips=0,
            preferred_destinations=[],
            preferences=[],
            average_budget=0.0,
            average_days=0.0,
            budget_style="medium"
        )
        db.add(profile)
        db.commit()
        return load_profile(user_id)
    finally:
        db.close()

def update_profile(user_id: str, result: Dict, preferences: List[str] = []) -> None:
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(
                user_id=user_id,
                created_at=datetime.utcnow(),
                total_trips=0,
                preferred_destinations=[],
                preferences=[],
                average_budget=0.0,
                average_days=0.0,
                budget_style="medium"
            )
            db.add(profile)

        destination = result.get("destination")
        budget = result.get("budget")
        days = result.get("days")

        profile.total_trips += 1

        # Update destinations
        dests = list(profile.preferred_destinations or [])
        if destination and destination not in dests:
            dests.insert(0, destination)
            profile.preferred_destinations = dests[:10]

        # Update preferences
        prefs = list(profile.preferences or [])
        for p in preferences:
            if p not in prefs:
                prefs.append(p)
        profile.preferences = prefs[:5]

        # Update averages
        n = profile.total_trips
        if budget is not None:
            profile.average_budget = (
                budget if n == 1
                else ((profile.average_budget * (n-1)) + budget) / n
            )
        if days is not None:
            profile.average_days = (
                days if n == 1
                else ((profile.average_days * (n-1)) + days) / n
            )

        # Budget style
        if profile.average_budget < 300:
            profile.budget_style = "low"
        elif profile.average_budget < 1000:
            profile.budget_style = "medium"
        else:
            profile.budget_style = "high"

        profile.last_active = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def get_preferences(user_id: str) -> List[str]:
    profile = load_profile(user_id)
    if not profile:
        return []
    return profile.get("preferences", [])