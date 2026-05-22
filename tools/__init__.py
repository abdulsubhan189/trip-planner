from .mock_weather import get_mock_weather
from .weather_api import get_real_weather
from .routing_api import get_travel_time
from .hotel_tool import search_hotels
from .flight_tool import search_flights
from .knowledge_tool import get_destination_info

def get_attractions(destination: str) -> list:
    info = get_destination_info(destination)
    return info.get("attractions", [])

def validate_attraction(name: str, destination: str) -> bool:
    attractions = get_attractions(destination)
    return any(a["name"].lower() == name.lower() for a in attractions)

def load_kb():
    return {}

__all__ = [
    "get_mock_weather",
    "get_real_weather",
    "get_travel_time",
    "search_hotels",
    "search_flights",
    "get_destination_info",
    "get_attractions",
    "validate_attraction",
    "load_kb",
]