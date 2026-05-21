from schemas import TripState
from tools import get_real_weather, get_mock_weather
from tools.knowledge_tool import get_destination_info

def weather_agent(state: TripState) -> TripState:
    if not state.destination:
        return state
    # Try to get coordinates from knowledge base
    dest_info = get_destination_info(state.destination)
    coords = dest_info.get("coordinates", {})
    lat = coords.get("lat")
    lon = coords.get("lon")
    # Use real API (fallback to mock)
    try:
        weather = get_real_weather(state.destination, lat, lon)
    except:
        weather = {"condition": get_mock_weather(state.destination), "source": "mock"}
    state.weather_info = weather
    return state