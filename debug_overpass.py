# debug_overpass.py
import requests

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

query = """
[out:json][timeout:30];
(
  way["historic"](around:15000,31.5204,74.3587);
  way["tourism"~"attraction|museum"](around:15000,31.5204,74.3587);
);
out center;
"""

resp = requests.post(
    OVERPASS_URL,
    data={"data": query},
    headers={"User-Agent": "Mozilla/5.0"}
)
print("Status:", resp.status_code)
print("Response:", resp.text[:1000])