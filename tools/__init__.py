from .mock_weather import get_mock_weather
from .weather_api import get_real_weather   # add this
from .routing_api import get_travel_time
from .hotel_tool import search_hotels
from .flight_tool import search_flights
from .knowledge_tool import (
    get_destination_info,
    get_attractions,
    load_kb,
    get_real_attractions,
    validate_attraction
)

__all__ = [
    "get_mock_weather",
    "get_real_weather",          # added
    "get_travel_time",
    "search_hotels",
    "search_flights",
    "get_destination_info",
    "get_attractions",
    "load_kb",
    "get_real_attractions",
    "validate_attraction"
]