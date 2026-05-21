import os
import math
import json
import hashlib
import requests
from typing import List, Tuple, Dict, Any
from threading import Lock
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

_travel_time_cache: Dict[str, float] = {}
_cache_lock = Lock()
CACHE_FILE = "travel_times_cache.json"

def load_cache():
    global _travel_time_cache
    try:
        with open(CACHE_FILE, "r") as f:
            _travel_time_cache = json.load(f)
    except FileNotFoundError:
        pass

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_travel_time_cache, f, indent=2)

def _make_key(lat1, lon1, lat2, lon2):
    points = sorted([(round(lat1,3), round(lon1,3)), (round(lat2,3), round(lon2,3))])
    return hashlib.md5(f"{points[0]}{points[1]}".encode()).hexdigest()

def haversine_distance(lat1, lon1, lat2, lon2, speed_kmh=40):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    km = R * c
    return (km / speed_kmh) * 60

def get_travel_time_google(lat1, lon1, lat2, lon2):
    """Use Google Maps Directions API."""
    if not GOOGLE_MAPS_API_KEY:
        return None
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{lat1},{lon1}",
        "destination": f"{lat2},{lon2}",
        "key": GOOGLE_MAPS_API_KEY,
        "mode": "driving"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data["status"] == "OK":
            # duration in seconds
            dur_sec = data["routes"][0]["legs"][0]["duration"]["value"]
            return dur_sec / 60.0
    except Exception:
        pass
    return None

def get_travel_time(lat1, lon1, lat2, lon2, profile="driving-car") -> float:
    key = _make_key(lat1, lon1, lat2, lon2)
    with _cache_lock:
        if key in _travel_time_cache:
            return _travel_time_cache[key]
    if not _travel_time_cache:
        load_cache()
        with _cache_lock:
            if key in _travel_time_cache:
                return _travel_time_cache[key]

    tt = None
    # Primary: Google Maps
    if GOOGLE_MAPS_API_KEY:
        tt = get_travel_time_google(lat1, lon1, lat2, lon2)
    # Fallback: Euclidean
    if tt is None:
        tt = haversine_distance(lat1, lon1, lat2, lon2)

    with _cache_lock:
        _travel_time_cache[key] = tt
        if len(_travel_time_cache) % 50 == 0:
            save_cache()
    return round(tt, 1)

def get_travel_time_matrix(coords: List[Tuple[float, float]]) -> List[List[float]]:
    """Batch travel times using Google Maps Distance Matrix API."""
    n = len(coords)
    matrix = [[0.0] * n for _ in range(n)]
    if not GOOGLE_MAPS_API_KEY:
        # fallback to pairwise Euclidean
        for i in range(n):
            for j in range(i+1, n):
                tt = haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
                matrix[i][j] = matrix[j][i] = round(tt, 1)
        return matrix
    # Build origins and destinations as coordinate strings
    loc_strings = [f"{lat},{lon}" for lat, lon in coords]
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "|".join(loc_strings),
        "destinations": "|".join(loc_strings),
        "key": GOOGLE_MAPS_API_KEY,
        "mode": "driving"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data["status"] == "OK":
            rows = data["rows"]
            for i in range(n):
                for j in range(n):
                    elem = rows[i]["elements"][j]
                    if elem["status"] == "OK":
                        dur_sec = elem["duration"]["value"]
                        matrix[i][j] = round(dur_sec / 60.0, 1)
                    else:
                        matrix[i][j] = haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            return matrix
    except Exception:
        pass
    # fallback
    return [[get_travel_time(coords[i][0], coords[i][1], coords[j][0], coords[j][1]) for j in range(n)] for i in range(n)]

def clear_cache():
    with _cache_lock:
        _travel_time_cache.clear()
        save_cache()