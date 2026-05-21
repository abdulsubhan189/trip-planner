from schemas import TripState

def budget_agent(state: TripState) -> TripState:
    budget = state.budget
    if budget <= 0:
        # No budget specified – treat as low to encourage economical tips
        budget = 200
        # Also we can store that it's unspecified
        state.budget_status = "unspecified"
    else:
        if budget < 300:
            state.budget_status = "low"
        elif budget < 1000:
            state.budget_status = "medium"
        else:
            state.budget_status = "high"

    # Recalculate constraints based on actual budget (or the assumed 200)
    b = budget if budget > 0 else 200
    if b < 300:
        constraints = {
            "transport": "public buses, shared jeeps",
            "accommodation": "hostels, guesthouses",
            "dining": "local street food, self-catering",
            "activities": "free walking tours, hiking, public parks, low‑fee museums",
            "luxury_allowed": False
        }
    elif b < 1000:
        constraints = {
            "transport": "private taxis, rental car",
            "accommodation": "mid‑range hotels, boutique stays",
            "dining": "casual restaurants, some fine dining",
            "activities": "paid entry sites, guided tours (moderate)",
            "luxury_allowed": False
        }
    else:
        constraints = {
            "transport": "chauffeur, private driver",
            "accommodation": "5‑star hotels, resorts",
            "dining": "high‑end restaurants, private chefs",
            "activities": "private tours, exclusive experiences, helicopter rides",
            "luxury_allowed": True
        }
    state.budget_constraints = constraints
    return state