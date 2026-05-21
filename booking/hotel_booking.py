# booking/hotel_booking.py
import random
import uuid
from typing import List, Dict, Any

# In-memory storage for bookings (mock)
hotel_bookings: Dict[str, Dict] = {}

def search_hotels(destination: str, days: int, budget: float) -> List[Dict]:
    """Return mock hotel options based on destination and budget."""
    # Normalise destination string
    dest = destination.lower().strip()
    base_price = 0
    if "skardu" in dest:
        base_price = 80
    elif "hunza" in dest:
        base_price = 70
    else:
        base_price = 100

    # Adjust for budget (low/medium/high)
    if budget < 300:
        price_multiplier = 0.8
    elif budget < 800:
        price_multiplier = 1.0
    else:
        price_multiplier = 1.5

    # Three tiers: budget, standard, premium
    hotels = [
        {
            "hotel_id": str(uuid.uuid4())[:8],
            "name": f"{destination.title()} Guest House",
            "price_per_night": int(base_price * 0.7 * price_multiplier),
            "rating": 3.5,
            "tier": "budget"
        },
        {
            "hotel_id": str(uuid.uuid4())[:8],
            "name": f"{destination.title()} Comfort Inn",
            "price_per_night": int(base_price * price_multiplier),
            "rating": 4.0,
            "tier": "standard"
        },
        {
            "hotel_id": str(uuid.uuid4())[:8],
            "name": f"{destination.title()} Grand Resort",
            "price_per_night": int(base_price * 1.5 * price_multiplier),
            "rating": 4.8,
            "tier": "premium"
        }
    ]
    for hotel in hotels:
        hotel["total_price"] = hotel["price_per_night"] * days
        hotel["currency"] = "USD"
    return hotels

def book_hotel(hotel_id: str, user_id: str) -> Dict:
    """Mock hotel booking. 90% success, 10% failure."""
    # Simulate failure randomly
    if random.random() < 0.1:
        return {"success": False, "error": "Hotel booking failed – no rooms available."}
    booking_id = str(uuid.uuid4())[:8]
    hotel_bookings[booking_id] = {
        "hotel_id": hotel_id,
        "user_id": user_id,
        "booking_id": booking_id,
        "status": "confirmed",
        "timestamp": "2026-05-21T00:00:00"  # would be real timestamp in production
    }
    return {"success": True, "booking_id": booking_id, "hotel_id": hotel_id}

def cancel_hotel(booking_id: str) -> Dict:
    """Mock hotel cancellation."""
    if booking_id in hotel_bookings:
        del hotel_bookings[booking_id]
        return {"success": True, "message": "Hotel booking cancelled."}
    return {"success": False, "error": "Booking not found."}