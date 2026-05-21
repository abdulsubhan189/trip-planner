from schemas import TripState

def response_synthesizer(state: TripState) -> TripState:
    """
    Clean user‑facing response: hide internal reasoning, present only the final polished itinerary.
    """
    # Build a clean, final message
    dest = state.destination or "your destination"
    days = state.days or 3
    budget = state.budget
    weather = state.weather_info.get("condition", "N/A") if state.weather_info else "N/A"

    header = f"**Your {days}-day trip to {dest}**\n"
    if budget > 0:
        header += f"Budget: ${budget:.2f} ({state.budget_status})\n"
    header += f"Weather expectation: {weather}\n\n"
    footer = "\n\n---\n*Plan generated with AI assistance. Enjoy your journey!*"

    # If itinerary already exists, use it; else fallback message
    if state.itinerary:
        # Remove any internal critic commentary (e.g., lines starting with "Issues detected")
        clean_lines = []
        for line in state.itinerary.split("\n"):
            if not line.strip().startswith("Issues detected") and "critic" not in line.lower():
                clean_lines.append(line)
        clean_itinerary = "\n".join(clean_lines)
        state.final_response = header + clean_itinerary + footer
    else:
        state.final_response = header + "Itinerary could not be generated. Please try again with more details." + footer

    return state