# database/models.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env file")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── Tables ──────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"
    session_id   = Column(String, primary_key=True)
    user_id      = Column(String, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    last_active  = Column(DateTime, default=datetime.utcnow)
    turns        = Column(JSON, default=list)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id                = Column(String, primary_key=True)
    created_at             = Column(DateTime, default=datetime.utcnow)
    last_active            = Column(DateTime, default=datetime.utcnow)
    total_trips            = Column(Integer, default=0)
    preferred_destinations = Column(JSON, default=list)
    preferences            = Column(JSON, default=list)
    average_budget         = Column(Float, default=0.0)
    average_days           = Column(Float, default=0.0)
    budget_style           = Column(String, default="medium")

class TripHistory(Base):
    __tablename__ = "trip_history"
    trip_id     = Column(String, primary_key=True)
    user_id     = Column(String, nullable=False)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    destination = Column(String)
    days        = Column(Integer)
    budget      = Column(Float)
    plan_score  = Column(Float)
    activities  = Column(JSON, default=list)

class EscalationTicket(Base):
    __tablename__ = "escalation_queue"
    ticket_id      = Column(String, primary_key=True)
    user_id        = Column(String)
    query          = Column(Text)
    result         = Column(JSON)
    reason         = Column(String)
    timestamp      = Column(DateTime, default=datetime.utcnow)
    status         = Column(String, default="pending")
    corrected_plan = Column(JSON, nullable=True)
    resolved_at    = Column(DateTime, nullable=True)

# --- New table for destination knowledge cache ---
class DestinationCache(Base):
    __tablename__ = "destination_cache"
    destination  = Column(String, primary_key=True)
    data         = Column(JSON)
    cached_at    = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Tables created successfully.")