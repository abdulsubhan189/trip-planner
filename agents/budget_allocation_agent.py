from schemas import TripState, BudgetAllocation

def budget_allocation_agent(state: TripState) -> TripState:
    """Allocate total budget across categories based on budget status and trip length."""
    total = state.budget
    days = state.days if state.days > 0 else 3

    # Base percentages (for medium budget)
    if state.budget_status == "low":
        hotel_pct = 0.25
        flights_pct = 0.15 if days > 2 else 0.10
        food_pct = 0.20
        transport_pct = 0.10
        activities_pct = 0.20
        emergency_pct = 0.10
    elif state.budget_status == "high":
        hotel_pct = 0.30
        flights_pct = 0.20 if days > 2 else 0.15
        food_pct = 0.15
        transport_pct = 0.10
        activities_pct = 0.20
        emergency_pct = 0.05
    else:  # medium
        hotel_pct = 0.25
        flights_pct = 0.15 if days > 2 else 0.10
        food_pct = 0.20
        transport_pct = 0.10
        activities_pct = 0.20
        emergency_pct = 0.10

    allocation = BudgetAllocation(
        total_budget=total,
        hotel=total * hotel_pct,
        flights=total * flights_pct,
        food=total * food_pct,
        transport=total * transport_pct,
        activities=total * activities_pct,
        emergency_reserve=total * emergency_pct,
    )
    state.budget_allocation = allocation
    return state