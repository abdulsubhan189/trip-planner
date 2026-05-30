# tools/photo_tool.py
import requests
import logging

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Fallback images per type
FALLBACK_IMAGES = {
    "adventure":   "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/24701-nature-natural-beauty.jpg/640px-24701-nature-natural-beauty.jpg",
    "culture":     "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Empire_State_Building_%28aerial_view%29.jpg/640px-Empire_State_Building_%28aerial_view%29.jpg",
    "nature":      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Lonely_Tree%2C_Buttermere_-_geograph.org.uk_-_901764.jpg/640px-Lonely_Tree%2C_Buttermere_-_geograph.org.uk_-_901764.jpg",
    "food":        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Good_Food_Display_-_NCI_Visuals_Online.jpg/640px-Good_Food_Display_-_NCI_Visuals_Online.jpg",
    "shopping":    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Aiga_gift_shop.svg/640px-Aiga_gift_shop.svg.png",
    "relaxation":  "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/24701-nature-natural-beauty.jpg/640px-24701-nature-natural-beauty.jpg",
    "sightseeing": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Empire_State_Building_%28aerial_view%29.jpg/640px-Empire_State_Building_%28aerial_view%29.jpg",
    "default":     "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/24701-nature-natural-beauty.jpg/640px-24701-nature-natural-beauty.jpg",
}

def get_destination_photo(destination: str) -> str:
    """Get a photo URL for a destination from Wikipedia."""
    try:
        resp = requests.get(
            f"{WIKIPEDIA_API}/{destination.replace(' ', '_')}",
            headers=HEADERS,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            thumbnail = data.get("thumbnail", {})
            if thumbnail.get("source"):
                # Get higher resolution version
                url = thumbnail["source"]
                url = url.replace("/320px-", "/640px-")
                return url
    except Exception as e:
        logger.warning(f"Photo fetch failed for {destination}: {e}")
    return FALLBACK_IMAGES["default"]

def get_activity_photo(activity_name: str, activity_type: str = "default") -> str:
    """Get a photo URL for an activity."""
    try:
        params = {
            "action": "query",
            "titles": activity_name.replace(" ", "_"),
            "prop": "pageimages",
            "pithumbsize": 640,
            "format": "json",
            "redirects": 1
        }
        resp = requests.get(
            WIKIMEDIA_API,
            params=params,
            headers=HEADERS,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                thumbnail = page.get("thumbnail", {})
                if thumbnail.get("source"):
                    return thumbnail["source"]
    except Exception as e:
        logger.warning(f"Activity photo fetch failed for {activity_name}: {e}")

    return FALLBACK_IMAGES.get(activity_type, FALLBACK_IMAGES["default"])

def enrich_plan_with_photos(plan_result: dict) -> dict:
    """Add photo URLs to plan result."""
    destination = plan_result.get("destination", "")

    # Get destination hero photo
    plan_result["destination_photo"] = get_destination_photo(destination)

    # Get photos for each activity
    for day in plan_result.get("daily_plans", []):
        for act in day.get("activities", []):
            act["photo"] = get_activity_photo(
                act["name"],
                act.get("activity_type", "default")
            )

    return plan_result

# --- NEW: Function to get destination description and photo from Wikipedia ---
def get_destination_info_wiki(destination: str) -> dict:
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{destination.replace(' ', '_')}",
            headers=HEADERS,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            description = data.get("extract", "")[:500]
            photo = data.get("thumbnail", {}).get("source", "")

            # Use Groq to extract best time from description
            best_time = _extract_best_time(destination, description)

            return {
                "description": description[:300],
                "photo": photo,
                "best_time_to_visit": best_time
            }
    except Exception as e:
        logger.warning(f"Wiki info failed for {destination}: {e}")
    return {"description": "", "photo": "", "best_time_to_visit": ""}

def _extract_best_time(destination: str, wiki_text: str) -> str:
    """Use Groq to extract best visiting time for a destination."""
    try:
        import os
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a travel expert. Answer in maximum 5 words. Only give the months or season range."
                },
                {
                    "role": "user",
                    "content": f"What is the best time to visit {destination}? Context: {wiki_text[:300]}"
                }
            ],
            temperature=0.1,
            max_tokens=20
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Best time extraction failed: {e}")
        return "Check local weather"