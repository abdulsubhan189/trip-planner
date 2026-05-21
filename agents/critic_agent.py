import os
from groq import Groq
from schemas import TripState
from tools import get_destination_info, validate_attraction

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def critic_agent(state: TripState) -> TripState:
    if not state.itinerary:
        return state

    # First, validate against real knowledge base
    dest_info = get_destination_info(state.destination)
    real_attractions = dest_info.get("real_attractions", [])
    issues = []
    hallucinated_places = []

    # Simple check: if any line contains a place name not in real list
    lines = state.itinerary.split("\n")
    for line in lines:
        for word in line.split():
            if word[0].isupper() and len(word) > 3:
                # potential attraction name
                if not validate_attraction(state.destination, word):
                    # Might be false positive, but report as suspicious
                    hallucinated_places.append(word)
    if hallucinated_places:
        issues.append(f"Potential fake or unverified attractions: {', '.join(set(hallucinated_places))}")

    # Weather check (mock)
    weather = state.weather_info.get("condition", "").lower() if state.weather_info else ""
    if "cold" in weather or "wind" in weather:
        if "outdoor" in state.itinerary.lower() and "indoor" not in state.itinerary.lower():
            issues.append("Weather is cold/windy – itinerary may need more indoor activities.")

    # Budget check
    if state.budget_status == "low" and "private" in state.itinerary.lower():
        issues.append("Budget is low but itinerary suggests expensive private services.")

    # Build prompt for LLM critic only if real issues found or we need rewrite
    if not issues and "ITINERARY_VALID" in state.critic_feedback:
        return state

    issues_text = "\n".join(issues) if issues else "No factual issues found, but please refine language if needed."

    prompt = f"""
    You are a travel critic with access to real destination knowledge for {state.destination}.
    Real attractions include: {', '.join(real_attractions)}.
    User preferences: {state.preferences}
    Budget category: {state.budget_status} (constraints: {state.budget_constraints})

    Issues detected (if any):
    {issues_text}

    Original itinerary:
    {state.itinerary}

    Output a corrected, evidence‑based itinerary (plain text, no extra commentary).
    Replace any fake attractions with real ones from the list above.
    Ensure weather and budget are respected.
    Keep the tone friendly and helpful.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        corrected = response.choices[0].message.content.strip()
        if corrected and "ITINERARY_VALID" not in corrected:
            state.itinerary = corrected
            state.critic_feedback = f"Corrected based on evidence. Issues: {issues_text}"
            state.retry_count += 1
        else:
            state.critic_feedback = "Itinerary validated against knowledge base."
    except Exception as e:
        print(f"Critic error: {e}")
        state.critic_feedback = f"Critic unavailable: {e}"
    return state

def check_duplication(state: TripState) -> TripState:
    if not state.structured_plan:
        return state
    plan = state.structured_plan
    all_activities = []
    for day in plan.daily_plans:
        for act in day.activities:
            all_activities.append(act.name)
    duplicates = [name for name in set(all_activities) if all_activities.count(name) > 1]
    if duplicates:
        state.critic_feedback += f"\n⚠️ Duplicate attractions found: {duplicates}. Recommend revisiting."
        # Optionally, we could trigger a replan here.
    return state