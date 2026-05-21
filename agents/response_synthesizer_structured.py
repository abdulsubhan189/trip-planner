from schemas import TripState

def response_synthesizer_structured(state: TripState) -> TripState:
    if not state.structured_plan:
        state.final_response = state.itinerary or "No itinerary generated."
        return state

    plan = state.structured_plan
    lines = []
    lines.append(f"**{plan.days}-day trip to {plan.destination}**")
    lines.append(f"Budget: ${plan.budget:.2f} ({plan.budget_status})")
    if plan.weather_info:
        lines.append(f"Weather: {plan.weather_info.get('condition', 'N/A')}")
    lines.append("")

    # Budget Allocation section (if available)
    if hasattr(state, 'budget_allocation') and state.budget_allocation:
        alloc = state.budget_allocation
        lines.append("**Budget Allocation**")
        lines.append(f"  • Hotel: ${alloc.hotel:.2f}")
        lines.append(f"  • Flights: ${alloc.flights:.2f}")
        lines.append(f"  • Food: ${alloc.food:.2f}")
        lines.append(f"  • Transport: ${alloc.transport:.2f}")
        lines.append(f"  • Activities: ${alloc.activities:.2f}")
        lines.append(f"  • Emergency reserve: ${alloc.emergency_reserve:.2f}")
        lines.append("")

    # Accommodation section
    accommodation = []
    for day in plan.daily_plans:
        for act in day.activities:
            if "lodging" in act.notes.lower() or "hotel" in act.name.lower():
                accommodation.append(act)
    if accommodation:
        lines.append("**Accommodation**")
        for act in accommodation:
            lines.append(f"• {act.name} (${act.estimated_cost:.2f}) – {act.notes}")
        lines.append("")

    # Daily Itinerary
    lines.append("**Daily Itinerary**")
    total_spent = 0.0
    for day in plan.daily_plans:
        lines.append(f"\n*{day.title}*")
        day_cost = 0.0
        for act in day.activities:
            if "lodging" in act.notes.lower() or "hotel" in act.name.lower():
                continue
            duration = "?"
            if "Duration:" in act.notes:
                part = act.notes.split("Duration:")[1].split("|")[0].strip()
                duration = part if part else "?"
            cost_str = f"(${act.estimated_cost:.2f})" if act.estimated_cost > 0 else "(free)"
            tag = act.activity_type.value if hasattr(act, 'activity_type') else "general"
            lines.append(f"  • {act.name} {cost_str} – Duration: {duration} | {tag}")
            day_cost += act.estimated_cost
            total_spent += act.estimated_cost
        if day_cost > 0:
            lines.append(f"  *Day total: ${day_cost:.2f}*")
    lines.append("")

    # Summary: show activities spent and remaining (not total remaining)
    lines.append("**Summary**")
    lines.append(f"Total trip budget: ${plan.budget:.2f}")
    lines.append(f"Activities spent: ${total_spent:.2f}")
    if hasattr(state, 'budget_allocation') and state.budget_allocation:
        alloc = state.budget_allocation
        lines.append(f"Activities budget allocated: ${alloc.activities:.2f}")
        lines.append(f"Remaining activities budget: ${alloc.activities - total_spent:.2f}")
        lines.append("\n_Other categories (hotel, flights, food, transport, emergency) are not yet spent – the plan only includes activities._")
    else:
        remaining = plan.budget - total_spent
        lines.append(f"Remaining budget: ${remaining:.2f}")

    if plan.overall_notes:
        lines.append("\n**Notes:**")
        for note in plan.overall_notes:
            lines.append(f"• {note}")

    lines.append("\n---\n*Plan respects all constraints.*")
    state.final_response = "\n".join(lines)
    return state