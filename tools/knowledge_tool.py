# tools/knowledge_tool.py
import requests
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "Mozilla/5.0"}

OVERPASS_SERVERS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# ---------------------------------------------------------------------------
# Known coordinates — fast fallback, no API needed
# ---------------------------------------------------------------------------
KNOWN_COORDS = {
    "lahore":      (31.5204, 74.3587),
    "karachi":     (24.8607, 67.0011),
    "islamabad":   (33.6844, 73.0479),
    "peshawar":    (34.0151, 71.5249),
    "quetta":      (30.1798, 66.9750),
    "multan":      (30.1575, 71.5249),
    "faisalabad":  (31.4504, 73.1350),
    "rawalpindi":  (33.5651, 73.0169),
    "gilgit":      (35.9208, 74.3087),
    "muzaffarabad":(34.3700, 73.4700),
    "paris":       (48.8566,  2.3522),
    "london":      (51.5074, -0.1278),
    "dubai":       (25.2048, 55.2708),
    "istanbul":    (41.0082, 28.9784),
    "bangkok":     (13.7563,100.5018),
    "tokyo":       (35.6762,139.6503),
    "new york":    (40.7128, -74.0060),
    "singapore":   ( 1.3521, 103.8198),
    "kuala lumpur":(  3.1390, 101.6869),
    "cairo":       (30.0444,  31.2357),
    "cholistan": (28.7728, 71.3378),
}

# ---------------------------------------------------------------------------
# Category mapping — OSM tag value → (type, cost, duration, value_score)
# ---------------------------------------------------------------------------
OSM_CATEGORY_MAP = {
    "mosque":           ("culture",   0,  1.0, 5),
    "church":           ("culture",   0,  1.0, 5),
    "temple":           ("culture",   0,  1.0, 5),
    "place_of_worship": ("culture",   0,  1.0, 5),
    "museum":           ("culture",  10,  2.0, 9),
    "fort":             ("culture",   5,  2.0, 9),
    "castle":           ("culture",   5,  2.0, 9),
    "ruins":            ("culture",   0,  1.5, 7),
    "monument":         ("culture",   0,  1.0, 7),
    "memorial":         ("culture",   0,  0.5, 6),
    "park":             ("nature",    0,  1.5, 7),
    "garden":           ("nature",    0,  1.5, 7),
    "nature_reserve":   ("adventure", 0,  3.0, 8),
    "viewpoint":        ("nature",    0,  1.0, 7),
    "waterfall":        ("adventure",10,  2.0, 8),
    "peak":             ("adventure", 0,  3.0, 8),
    "beach":            ("nature",    0,  2.0, 7),
    "lake":             ("nature",    0,  2.0, 7),
    "marketplace":      ("shopping", 20,  1.5, 6),
    "mall":             ("shopping", 30,  2.0, 6),
    "bazaar":           ("shopping", 15,  1.5, 6),
    "zoo":              ("nature",   15,  2.0, 7),
    "aquarium":         ("nature",   20,  2.0, 7),
    "theme_park":       ("adventure",30,  3.0, 8),
    "artwork":          ("culture",   0,  0.5, 5),
    "attraction":       ("culture",   0,  1.5, 7),
}

# ---------------------------------------------------------------------------
# Skip keywords — filter out non-tourist places
# ---------------------------------------------------------------------------
SKIP_KEYWORDS = [
    "hostel", "guest house", "hall no", "block no", "office",
    "department", "faculty", "cafeteria", "canteen", "dispensary",
    "laboratory", "sec ", "phase ", "ph ", "colony", "chowk",
    "pumping", "grid station", "transformer", "substation",
    "university block", "committee", "welfare", "association",
]

# ---------------------------------------------------------------------------
# Coordinates lookup
# ---------------------------------------------------------------------------
def _get_coordinates(destination: str):
    dest_lower = destination.lower().strip()
    if dest_lower in KNOWN_COORDS:
        return KNOWN_COORDS[dest_lower]

    # Try multiple Nominatim approaches
    urls_to_try = [
        f"https://nominatim.openstreetmap.org/search?q={destination}&format=json&limit=1",
        f"https://geocode.maps.co/search?q={destination}&api_key=free",
    ]
    
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            logger.warning(f"Geocoding failed for {destination}: {e}")
            continue
    
    return None, None

# ---------------------------------------------------------------------------
# Overpass fetch — tries multiple servers
# ---------------------------------------------------------------------------
def _fetch_attractions(lat: float, lon: float, radius_m: int = 12000) -> list:
    query = f"""
[out:json][timeout:60];
(
  node["tourism"~"attraction|museum|viewpoint|theme_park|zoo|aquarium"](around:{radius_m},{lat},{lon});
  way["tourism"~"attraction|museum|theme_park|zoo"](around:{radius_m},{lat},{lon});
  relation["tourism"~"attraction|museum"](around:{radius_m},{lat},{lon});
  node["historic"~"fort|castle|monument|memorial|ruins|mosque|shrine|tomb|mausoleum"](around:{radius_m},{lat},{lon});
  way["historic"~"fort|castle|monument|ruins|mosque|shrine|tomb|mausoleum"](around:{radius_m},{lat},{lon});
  relation["historic"~"fort|castle|monument|ruins|mosque|shrine"](around:{radius_m},{lat},{lon});
  node["leisure"~"park|garden|nature_reserve"](around:{radius_m},{lat},{lon});
  way["leisure"~"park|garden|nature_reserve"](around:{radius_m},{lat},{lon});
  node["amenity"~"marketplace|place_of_worship"](around:{radius_m},{lat},{lon});
);
out center;
"""
    for server in OVERPASS_SERVERS:
        try:
            resp = requests.post(
                server,
                data={"data": query},
                headers=HEADERS,
                timeout=60
            )
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                logger.info(f"Overpass returned {len(elements)} elements from {server}")
                return elements
        except Exception as e:
            logger.warning(f"Overpass server {server} failed: {e}")
            continue
    logger.warning("All Overpass servers failed")
    return []

# ---------------------------------------------------------------------------
# Normalize element
# ---------------------------------------------------------------------------
def _normalize_element(el: dict, dest_lat: float, dest_lon: float):
    tags = el.get("tags", {})

    # Try English name first
    name = tags.get("name:en") or tags.get("name")
    if not name:
        return None

    # Minimum length
    if len(name) < 4:
        return None

    # Skip non-ASCII
    if not all(ord(c) < 128 for c in name):
        return None

    # Skip low-quality places
    name_lower = name.lower()
    if any(kw in name_lower for kw in SKIP_KEYWORDS):
        return None

    # Coordinates — node, way center, or relation center
    lat = el.get("lat") or el.get("center", {}).get("lat") or dest_lat
    lon = el.get("lon") or el.get("center", {}).get("lon") or dest_lon

    # Category from OSM tags
    act_type, cost, duration, value_score = "sightseeing", 0, 1.0, 5
    for key in ["historic", "tourism", "leisure", "natural", "amenity"]:
        val = tags.get(key, "")
        if val in OSM_CATEGORY_MAP:
            act_type, cost, duration, value_score = OSM_CATEGORY_MAP[val]
            break

    # Boost famous landmark keywords
    famous_keywords = ["fort", "mosque", "palace", "garden", "museum",
                       "mausoleum", "shrine", "cathedral", "temple", "tomb"]
    if any(kw in name_lower for kw in famous_keywords):
        value_score = max(value_score, 8)

    # Weather score
    if act_type == "culture":
        weather_score = {"sunny": 8, "cloudy": 8, "rain": 7, "snow": 6}
        indoor = True
    elif act_type == "adventure":
        weather_score = {"sunny": 9, "cloudy": 6, "rain": 1, "snow": 0}
        indoor = False
    else:
        weather_score = {"sunny": 9, "cloudy": 7, "rain": 3, "snow": 2}
        indoor = False

    return {
        "name": name,
        "type": act_type,
        "cost_estimate": cost,
        "duration_hours": duration,
        "lat": lat,
        "lon": lon,
        "indoor": indoor,
        "intensity": 2,
        "weather_score": weather_score,
        "weather_suitability": ["any"],
        "value_score": value_score,
    }

# ---------------------------------------------------------------------------
# DB cache
# ---------------------------------------------------------------------------
def _load_cache(destination: str):
    try:
        from database.models import SessionLocal, DestinationCache
        db = SessionLocal()
        try:
            row = db.query(DestinationCache).filter(
                DestinationCache.destination == destination.lower()
            ).first()
            return row.data if row else None
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return None

def _save_cache(destination: str, data: dict):
    try:
        from database.models import SessionLocal, DestinationCache
        db = SessionLocal()
        try:
            existing = db.query(DestinationCache).filter(
                DestinationCache.destination == destination.lower()
            ).first()
            if existing:
                existing.data = data
                existing.cached_at = datetime.utcnow()
            else:
                db.add(DestinationCache(
                    destination=destination.lower(),
                    data=data,
                    cached_at=datetime.utcnow()
                ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")

# ---------------------------------------------------------------------------
# Static JSON fallback (Skardu, Hunza)
# ---------------------------------------------------------------------------
def _load_static(destination: str):
    import json, os
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "destination_knowledge.json"
    )
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data.get(destination.lower())
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def get_destination_info(destination: str) -> dict:
    if not destination:
        return {"attractions": [], "coordinates": {}, "hotel_zone": {}}

    dest_lower = destination.lower().strip()

    # 1. Static JSON first (Skardu, Hunza — high quality curated data)
    static = _load_static(dest_lower)
    if static:
        return static

    # 2. DB cache
    cached = _load_cache(dest_lower)
    if cached:
        return cached

    # 3. Fetch from Overpass
    print(f">>> Fetching live data for: {destination}")
    lat, lon = _get_coordinates(destination)
    if lat is None:
        logger.warning(f"Could not resolve coordinates for {destination}")
        return {"attractions": [], "coordinates": {}, "hotel_zone": {}}

    elements = _fetch_attractions(lat, lon)

    # Normalize + deduplicate
    attractions = []
    seen_names = set()
    for el in elements:
        norm = _normalize_element(el, lat, lon)
        if norm and norm["name"] not in seen_names:
            attractions.append(norm)
            seen_names.add(norm["name"])

    # Sort by value_score first
    attractions.sort(key=lambda x: x.get("value_score", 0), reverse=True)

    # Balance types — max 3 per type, but always keep high-score ones
    type_counts = defaultdict(int)
    balanced = []
    for a in attractions:
        t = a.get("type", "sightseeing")
        if type_counts[t] < 3 or a.get("value_score", 0) >= 8:
            balanced.append(a)
            type_counts[t] += 1
    attractions = balanced[:20]

    result = {
        "attractions": attractions,
        "coordinates": {"lat": lat, "lon": lon},
        "hotel_zone": {"lat": lat, "lon": lon},
        "tags": [],
        "source": "overpass"
    }

    if attractions:
        _save_cache(dest_lower, result)

    return result