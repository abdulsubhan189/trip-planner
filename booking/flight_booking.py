# booking/flight_booking.py
import random
import uuid
from typing import List, Dict, Any

# In-memory storage for flight bookings
flight_bookings: Dict[str, Dict] = {}

def search_flights(destination: str, days: int, budget: float) -> List[Dict]:
    """Return mock flight options based on destination and budget."""
    dest = destination.lower().strip()
    base_price = 0
    if "skardu" in dest:
        base_price = 200  # Skardu is remote
    elif "hunza" in dest:
        base_price = 180
    else:
        base_price = 250

    # Adjust for budget
    if budget < 300:
        price_multiplier = 0.8
    elif budget < 800:
        price_multiplier = 1.0
    else:
        price_multiplier = 1.3

    airlines = ["PIA", "Serene Air", "Airblue"] if "skardu" in dest else ["PIA", "Serene Air"]

    flights = []
    # Economy (budget)
    flights.append({
        "flight_id": str(uuid.uuid4())[:8],
        "airline": airlines[0],
        "price": int(base_price * 0.8 * price_multiplier),
        "duration_hours": 1.5,
        "departure": "08:00",
        "arrival": "09:30",
        "class": "economy"
    })
    # Business (premium)
    flights.append({
        "flight_id": str(uuid.uuid4())[:8],
        "airline": airlines[-1],
        "price": int(base_price * 1.5 * price_multiplier),
        "duration_hours": 1.5,
        "departure": "14:00",
        "arrival": "15:30",
        "class": "business"
    })
    # Add a third option for high budget
    if budget > 800:
        flights.append({
            "flight_id": str(uuid.uuid4())[:8],
            "airline": "Emirates",
            "price": int(base_price * 2.0 * price_multiplier),
            "duration_hours": 1.2,
            "departure": "11:00",
            "arrival": "12:20",
            "class": "first"
        })
    return flights

def book_flight(flight_id: str, user_id: str) -> Dict:
    """Mock flight booking. 90% success, 10% failure."""
    if random.random() < 0.1:
        return {"success": False, "error": "Flight booking failed – seat unavailable."}
    booking_id = str(uuid.uuid4())[:8]
    flight_bookings[booking_id] = {
        "flight_id": flight_id,
        "user_id": user_id,
        "booking_id": booking_id,
        "status": "confirmed",
        "timestamp": "2026-05-21T00:00:00"
    }
    return {"success": True, "booking_id": booking_id, "flight_id": flight_id}

def cancel_flight(booking_id: str) -> Dict:
    """Mock flight cancellation."""
    if booking_id in flight_bookings:
        del flight_bookings[booking_id]
        return {"success": True, "message": "Flight booking cancelled."}
    return {"success": False, "error": "Booking not found."}