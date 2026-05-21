import json
import os
from difflib import get_close_matches

HOTEL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hotels.json")

def load_hotels():
    with open(HOTEL_DB_PATH, "r") as f:
        return json.load(f)

def search_hotels(destination: str, budget_status: str = "medium"):
    """Retrieve hotels matching destination and budget."""
    hotels = load_hotels()
    dest_norm = destination.lower()
    budget_map = {"low": "budget", "medium": "medium", "high": "luxury"}
    budget_type = budget_map.get(budget_status, "medium")
    matches = [h for h in hotels if h["destination"] == dest_norm and h["type"] == budget_type]
    if not matches:
        # fallback to any hotel in destination
        matches = [h for h in hotels if h["destination"] == dest_norm]
    return matches[:3]  # top 3