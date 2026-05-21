# escalation/queue.py
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from database.models import SessionLocal, EscalationTicket

def add_to_queue(user_id: str, query: str, result: Dict, reason: str) -> str:
    ticket_id = str(uuid.uuid4())[:8]
    db = SessionLocal()
    try:
        ticket = EscalationTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            query=query,
            result=result,
            reason=reason,
            timestamp=datetime.utcnow(),
            status="pending",
            corrected_plan=None
        )
        db.add(ticket)
        db.commit()
    finally:
        db.close()
    return ticket_id

def get_queue() -> List[Dict]:
    db = SessionLocal()
    try:
        tickets = (
            db.query(EscalationTicket)
            .filter(EscalationTicket.status == "pending")
            .order_by(EscalationTicket.timestamp.desc())
            .all()
        )
        return [_ticket_to_dict(t) for t in tickets]
    finally:
        db.close()

def resolve_ticket(ticket_id: str, corrected_plan: Dict) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(EscalationTicket).filter(
            EscalationTicket.ticket_id == ticket_id
        ).first()
        if ticket:
            ticket.status = "resolved"
            ticket.corrected_plan = corrected_plan
            ticket.resolved_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

def get_ticket(ticket_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        ticket = db.query(EscalationTicket).filter(
            EscalationTicket.ticket_id == ticket_id
        ).first()
        return _ticket_to_dict(ticket) if ticket else None
    finally:
        db.close()

def _ticket_to_dict(ticket: EscalationTicket) -> Dict:
    return {
        "ticket_id": ticket.ticket_id,
        "user_id": ticket.user_id,
        "query": ticket.query,
        "result": ticket.result,
        "reason": ticket.reason,
        "timestamp": ticket.timestamp.isoformat(),
        "status": ticket.status,
        "corrected_plan": ticket.corrected_plan,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None
    }