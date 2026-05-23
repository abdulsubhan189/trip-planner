# memory/vector_memory.py
import logging
from typing import List
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from database.models import SessionLocal

logger = logging.getLogger(__name__)
model = SentenceTransformer("all-MiniLM-L6-v2")

def _build_trip_text(destination: str, preferences: List[str], activities: List[str]) -> str:
    prefs = " ".join(preferences) if preferences else ""
    acts = " ".join(activities[:10]) if activities else ""
    return f"{destination} {prefs} {acts}".strip()

def _embed(text_input: str) -> str:
    vec = model.encode(text_input).tolist()
    return "[" + ",".join(str(x) for x in vec) + "]"

def save_trip_embedding(user_id, trip_id, destination, preferences, activities, rating=0.0):
    try:
        embedding = _embed(_build_trip_text(destination, preferences, activities))
        db = SessionLocal()
        try:
            db.execute(text("""
                INSERT INTO trip_embeddings
                (user_id, trip_id, destination, preferences, activities, rating, embedding)
                VALUES (:user_id, :trip_id, :destination, :preferences, :activities, :rating, CAST(:embedding AS vector))
            """), {
                "user_id": user_id,
                "trip_id": trip_id,
                "destination": destination,
                "preferences": preferences,
                "activities": activities,
                "rating": rating,
                "embedding": embedding
            })
            db.commit()
        finally:
            db.close()
        logger.info(f"Saved embedding for {trip_id}")
    except Exception as e:
        logger.warning(f"Save embedding failed: {e}")

def find_similar_trips(user_id, destination, preferences, limit=3):
    try:
        embedding = _embed(_build_trip_text(destination, preferences, []))
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT trip_id, destination, preferences, activities, rating,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM trip_embeddings
                WHERE user_id = :user_id
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """), {
                "user_id": user_id,
                "embedding": embedding,
                "limit": limit
            }).fetchall()
            return [
                {
                    "trip_id": r[0],
                    "destination": r[1],
                    "preferences": r[2],
                    "activities": r[3],
                    "rating": r[4],
                    "similarity": float(r[5])
                }
                for r in rows
            ]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Similarity search failed: {e}")
        return []

def find_similar_trips(user_id, destination, preferences, limit=3):
    try:
        embedding = _embed(_build_trip_text(destination, preferences, []))
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT trip_id, destination, preferences, activities, rating,
                       1 - (embedding <=> :embedding::vector) AS similarity
                FROM trip_embeddings
                WHERE user_id = :user_id
                ORDER BY embedding <=> :embedding::vector
                LIMIT :limit
            """), {
                "user_id": user_id,
                "embedding": embedding,
                "limit": limit
            }).fetchall()
            return [
                {
                    "trip_id": r[0],
                    "destination": r[1],
                    "preferences": r[2],
                    "activities": r[3],
                    "rating": r[4],
                    "similarity": float(r[5])
                }
                for r in rows
            ]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Similarity search failed: {e}")
        return []

def get_liked_activities(user_id, min_rating=3.5):
    try:
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT activities FROM trip_embeddings
                WHERE user_id = :user_id AND rating >= :min_rating
            """), {"user_id": user_id, "min_rating": min_rating}).fetchall()
            liked = set()
            for r in rows:
                for act in (r[0] or []):
                    liked.add(act)
            return list(liked)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"get_liked_activities failed: {e}")
        return []

def get_disliked_activities(user_id, max_rating=2.5):
    try:
        db = SessionLocal()
        try:
            rows = db.execute(text("""
                SELECT activities FROM trip_embeddings
                WHERE user_id = :user_id AND rating <= :max_rating
            """), {"user_id": user_id, "max_rating": max_rating}).fetchall()
            disliked = set()
            for r in rows:
                for act in (r[0] or []):
                    disliked.add(act)
            return list(disliked)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"get_disliked_activities failed: {e}")
        return []