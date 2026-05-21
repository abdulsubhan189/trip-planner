import json
import os
from difflib import get_close_matches

KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "destination_knowledge.json")

def load_kb():
    with open(KNOWLEDGE_PATH, "r") as f:
        return json.load(f)

def get_destination_info(destination: str):
    kb = load_kb()
    dest_norm = destination.lower()
    keys = list(kb.keys())
    if dest_norm in keys:
        return kb[dest_norm]
    matches = get_close_matches(dest_norm, keys, n=1, cutoff=0.6)
    return kb.get(matches[0], {}) if matches else {}

def get_attractions(destination: str, tags: list = None, max_cost: float = None, indoor_only: bool = False):
    """Search attractions by tags, cost, indoor/outdoor."""
    info = get_destination_info(destination)
    attractions = info.get("attractions", [])
    if tags:
        attractions = [a for a in attractions if any(t in info.get("tags", []) for t in tags)]
    if max_cost is not None:
        attractions = [a for a in attractions if a.get("cost_estimate", 0) <= max_cost]
    if indoor_only:
        attractions = [a for a in attractions if a.get("indoor", False)]
    return attractions
# Add this function to your existing file

def get_real_attractions(destination: str) -> list:
    """Return list of attraction names (strings) for a destination."""
    info = get_destination_info(destination)
    attractions = info.get("attractions", [])
    # Return just the names (for compatibility with planner_structured)
    return [a["name"] for a in attractions]

def validate_attraction(destination: str, attraction_name: str) -> bool:
    """Check if an attraction name exists in the destination's real attractions list."""
    real_attractions = get_real_attractions(destination)
    return any(attraction_name.lower() in r.lower() for r in real_attractions)