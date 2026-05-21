import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_real_weather(destination: str, lat: float = None, lon: float = None) -> dict:
    """Fetch real weather from OpenWeatherMap."""
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY not set in .env")
    # If coordinates not provided, we would need geocoding (simplify: use default)
    # For demo, use a fixed city ID or name; but we'll use lat/lon if available.
    if lat and lon:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    else:
        # fallback to city name
        url = f"https://api.openweathermap.org/data/2.5/weather?q={destination}&appid={OPENWEATHER_API_KEY}&units=metric"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        weather = {
            "condition": data["weather"][0]["description"],
            "temp_c": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "source": "openweathermap"
        }
        return weather
    except Exception as e:
        print(f"Weather API error: {e}. Falling back to mock.")
        from tools.mock_weather import get_mock_weather
        return {"condition": get_mock_weather(destination), "source": "mock"}