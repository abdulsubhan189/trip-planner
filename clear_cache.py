# clear_cache.py
from database.models import SessionLocal, DestinationCache

destination = "cholistan"  # change this as needed

db = SessionLocal()
deleted = db.query(DestinationCache).filter(
    DestinationCache.destination == destination
).delete()
db.commit()
db.close()
print(f"Cleared {deleted} cache entry(s) for '{destination}'")
print("✅ Cache cleared successfully.")