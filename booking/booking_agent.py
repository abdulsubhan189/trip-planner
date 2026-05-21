# booking/booking_agent.py
import uuid
from datetime import datetime
from typing import Dict, Any, List
from .hotel_booking import search_hotels, book_hotel, cancel_hotel
from .flight_booking import search_flights, book_flight, cancel_flight

# Pending approvals — waiting for user confirmation
pending_approvals: Dict[str, Dict] = {}

def create_booking_request(user_id: str, result: Dict) -> Dict:
    """
    Create a booking request dictionary from a planning result.
    Extracts destination, days, budget, and optionally selected hotel/flight.
    For now, we choose the best options (highest rated hotel, cheapest flight).
    """
    destination = result.get("destination", "")
    days = result.get("days", 3)
    budget = result.get("budget", 500.0)

    # Search hotels and pick the one with highest rating (or best value)
    hotels = search_hotels(destination, days, budget)
    if hotels:
        # Prefer premium if budget allows, else standard, else budget
        preferred_tier = "premium" if budget > 800 else "standard" if budget > 300 else "budget"
        best_hotel = None
        for h in hotels:
            if h["tier"] == preferred_tier:
                best_hotel = h
                break
        if not best_hotel:
            best_hotel = hotels[0]  # fallback
    else:
        best_hotel = None

    # Search flights and pick the cheapest
    flights = search_flights(destination, days, budget)
    best_flight = flights[0] if flights else None

    return {
        "user_id": user_id,
        "destination": destination,
        "days": days,
        "budget": budget,
        "hotel": best_hotel,
        "flight": best_flight,
        "status": "pending"
    }

def execute_booking(booking_request: Dict) -> Dict:
    """
    Execute the booking: book hotel and flight.
    Returns a result with status and booking details.
    Implements rollback: if one booking fails, automatically cancel the other.
    """
    user_id = booking_request["user_id"]
    hotel = booking_request.get("hotel")
    flight = booking_request.get("flight")

    result = {
        "user_id": user_id,
        "destination": booking_request["destination"],
        "hotel_booking": None,
        "flight_booking": None,
        "status": "failed",
        "errors": [],
        "rollback": None
    }

    # Book hotel
    if hotel:
        hotel_result = book_hotel(hotel["hotel_id"], user_id)
        if hotel_result["success"]:
            result["hotel_booking"] = hotel_result
        else:
            result["errors"].append(hotel_result["error"])
    else:
        result["errors"].append("No hotel selected")

    # Book flight
    if flight:
        flight_result = book_flight(flight["flight_id"], user_id)
        if flight_result["success"]:
            result["flight_booking"] = flight_result
        else:
            result["errors"].append(flight_result["error"])
    else:
        result["errors"].append("No flight selected")

    # ---- Rollback logic ----
    if result["hotel_booking"] and result["flight_booking"]:
        result["status"] = "success"
    elif result["hotel_booking"] and not result["flight_booking"]:
        # Flight failed — rollback hotel
        hotel_booking_id = result["hotel_booking"].get("booking_id")
        if hotel_booking_id:
            cancel_result = cancel_hotel(hotel_booking_id)
            result["hotel_booking"] = None
            result["rollback"] = {
                "action": "hotel_cancelled",
                "booking_id": hotel_booking_id,
                "success": cancel_result.get("success", False)
            }
        result["status"] = "failed"
        result["errors"].append("Flight failed — hotel booking rolled back automatically")
    elif result["flight_booking"] and not result["hotel_booking"]:
        # Hotel failed — rollback flight
        flight_booking_id = result["flight_booking"].get("booking_id")
        if flight_booking_id:
            cancel_result = cancel_flight(flight_booking_id)
            result["flight_booking"] = None
            result["rollback"] = {
                "action": "flight_cancelled",
                "booking_id": flight_booking_id,
                "success": cancel_result.get("success", False)
            }
        result["status"] = "failed"
        result["errors"].append("Hotel failed — flight booking rolled back automatically")
    else:
        result["status"] = "failed"

    return result

# ---------------------------------------------------------------------------
# Approval layer
# ---------------------------------------------------------------------------
def create_approval_request(user_id: str, result: Dict) -> Dict:
    """Create booking request and store it pending approval."""
    booking_request = create_booking_request(user_id, result)
    approval_id = str(uuid.uuid4())[:8]
    pending_approvals[approval_id] = {
        "approval_id": approval_id,
        "user_id": user_id,
        "booking_request": booking_request,
        "status": "awaiting_approval",
        "created_at": datetime.now().isoformat(),
        "booking_result": None
    }
    return {"approval_id": approval_id, **booking_request}

def approve_booking(approval_id: str) -> Dict:
    """User approved — execute the booking."""
    approval = pending_approvals.get(approval_id)
    if not approval:
        return {"success": False, "error": "Approval request not found"}
    if approval["status"] != "awaiting_approval":
        return {"success": False, "error": f"Already {approval['status']}"}
    approval["status"] = "processing"
    result = execute_booking(approval["booking_request"])
    approval["status"] = "completed" if result["status"] == "success" else "failed"
    approval["booking_result"] = result
    return result

def reject_booking(approval_id: str) -> Dict:
    """User rejected — cancel everything."""
    approval = pending_approvals.get(approval_id)
    if not approval:
        return {"success": False, "error": "Approval request not found"}
    approval["status"] = "rejected"
    return {"success": True, "message": "Booking cancelled by user"}

def get_approval(approval_id: str) -> Dict:
    """Get current approval status."""
    return pending_approvals.get(approval_id)