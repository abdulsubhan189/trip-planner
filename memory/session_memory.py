# memory/session_memory.py
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from database.models import SessionLocal, Session

def create_session(user_id: str) -> str:
    session_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            turns=[]
        )
        db.add(session)
        db.commit()
    finally:
        db.close()
    return session_id

def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session:
            return None
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "last_active": session.last_active.isoformat(),
            "turns": session.turns or []
        }
    finally:
        db.close()

def save_turn(session_id: str, query: str, result: Dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session:
            return
        turns = list(session.turns or [])
        turns.append({
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "destination": result.get("destination"),
            "days": result.get("days"),
            "budget": result.get("budget"),
            "plan_score": result.get("plan_score")
        })
        session.turns = turns
        session.last_active = datetime.utcnow()
        db.commit()
    finally:
        db.close()

def get_last_destination(session_id: str) -> Optional[str]:
    session = load_session(session_id)
    if not session or not session["turns"]:
        return None
    return session["turns"][-1].get("destination")