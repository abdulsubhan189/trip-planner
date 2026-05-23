# check_embeddings.py
from sqlalchemy import text
from database.models import SessionLocal

db = SessionLocal()
rows = db.execute(text("SELECT trip_id, user_id, destination, rating FROM trip_embeddings")).fetchall()
print(f"Total embeddings: {len(rows)}")
for r in rows:
    print(f"  trip_id={r[0]}, user_id={r[1]}, destination={r[2]}, rating={r[3]}")
db.close()