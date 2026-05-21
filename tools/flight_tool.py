def search_flights(origin: str = "ISB", destination: str = "SKD") -> list:
    """Mock flight search. Replace with real API (e.g., AviationStack)."""
    # Simulated results
    return [
        {"airline": "PIA", "price": 120, "duration": "1h 20m", "departure": "08:00", "arrival": "09:20"},
        {"airline": "Serene Air", "price": 150, "duration": "1h 15m", "departure": "14:30", "arrival": "15:45"}
    ]