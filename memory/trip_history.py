# memory/trip_history.py
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from database.models import SessionLocal, TripHistory

def save_trip(user_id: str, result: Dict) -> str:
    activities = [
        act.get("name", "")
        for day in result.get("daily_plans", [])
        for act in day.get("activities", [])
        if act.get("name")
    ]
    trip_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        trip = TripHistory(
            trip_id=trip_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            destination=result.get("destination"),
            days=result.get("days"),
            budget=result.get("budget"),
            plan_score=result.get("plan_score"),
            activities=activities
        )
        db.add(trip)
        db.commit()
    finally:
        db.close()
    return trip_id

def get_trip_history(user_id: str, limit: int = 10) -> List[Dict]:
    db = SessionLocal()
    try:
        trips = (
            db.query(TripHistory)
            .filter(TripHistory.user_id == user_id)
            .order_by(TripHistory.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "trip_id": t.trip_id,
                "user_id": t.user_id,
                "timestamp": t.timestamp.isoformat(),
                "destination": t.destination,
                "days": t.days,
                "budget": t.budget,
                "plan_score": t.plan_score,
                "activities": t.activities or []
            }
            for t in trips
        ]
    finally:
        db.close()

def get_visited_activities(user_id: str) -> List[str]:
    db = SessionLocal()
    try:
        trips = db.query(TripHistory).filter(TripHistory.user_id == user_id).all()
        activities = set()
        for trip in trips:
            for act in (trip.activities or []):
                activities.add(act)
        return list(activities)
    finally:
        db.close()