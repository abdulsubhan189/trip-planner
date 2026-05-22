# clear_cache.py
from database.models import SessionLocal, DestinationCache

db = SessionLocal()
try:
    deleted = db.query(DestinationCache).filter(DestinationCache.destination == "lahore").delete()
    db.commit()
    print(f"Cleared {deleted} cache entry(s) for 'lahore'")
finally:
    db.close()
print("✅ Cache cleared successfully.")