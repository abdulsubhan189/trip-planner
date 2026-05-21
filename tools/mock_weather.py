def get_mock_weather(destination: str) -> str:
    dest = destination.lower().strip()
    weather_map = {
        "hunza": "cold, clear, mountain weather",
        "skardu": "cold, windy, unpredictable",
        "naran": "cool, pleasant, occasional rain",
        "murree": "chilly, foggy, light drizzle",
        "islamabad": "mild, partly cloudy",
        "lahore": "warm, sunny",
        "karachi": "hot, humid",
    }
    for key, weather in weather_map.items():
        if key in dest:
            return weather
    return "moderate, fair conditions"