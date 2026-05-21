from schemas import TripState
from tools import get_destination_info

MAX_DAILY_HOURS = 8.0

# Fillers are valid even if not in knowledge base
KNOWN_FILLERS = {
    "sunset viewpoint", "local market stroll", "café stop with view",
    "short heritage walk", "scenic photography break", "evening leisure time",
    "local fruit tasting", "short nature trail", "riverside relaxation",
    "cultural music evening", "handicraft workshop", "morning mountain walk",
    "free time / rest"
}

def critic_structured(state: TripState) -> TripState:
    if not state.structured_plan:
        state.plan_valid = False
        state.critic_feedback = "No structured plan to validate."
        state.last_critic_feedback = state.critic_feedback   # added
        return state

    plan = state.structured_plan
    issues = []

    # Get activities budget
    activities_budget = (
        state.budget_allocation.activities
        if state.budget_allocation
        else state.budget
    )

    # Get hotel coords safely
    from agents.planner_structured import compute_day_usage
    try:
        dest_info = get_destination_info(plan.destination)
        hz = dest_info.get("hotel_zone", {})
        coords = dest_info.get("coordinates", {})
        hotel_coords = (
            hz.get("lat") or coords.get("lat"),
            hz.get("lon") or coords.get("lon")
        )
    except Exception:
        hotel_coords = (None, None)

    # 1. Empty day check
    for i, day in enumerate(plan.daily_plans):
        if not day.activities:
            issues.append(f"Day {i+1} has no activities")

    # 2. Daily capacity check
    for i, day in enumerate(plan.daily_plans):
        if not day.activities:
            continue
        usage, _, _ = compute_day_usage(
            [act.dict() for act in day.activities], hotel_coords
        )
        if usage > MAX_DAILY_HOURS + 0.1:
            issues.append(f"Day {i+1} exceeds capacity: {usage:.1f}h > {MAX_DAILY_HOURS}h")

    # 3. Budget check against activities budget
    total_spent = sum(
        act.estimated_cost
        for day in plan.daily_plans
        for act in day.activities
    )
    if total_spent > activities_budget * 1.10:  # allow 10% buffer
        issues.append(
            f"Activities cost ${total_spent:.2f} exceeds "
            f"activities budget ${activities_budget:.2f}"
        )

    # 4. Duplicate check
    all_names = [act.name for day in plan.daily_plans for act in day.activities]
    if len(set(all_names)) != len(all_names):
        issues.append("Duplicate attractions found across days")

    # 5. Grounding check (skip known fillers)
    real_attractions = {
        a["name"].lower()
        for a in dest_info.get("attractions", [])
    }
    for name in all_names:
        if name.lower() in KNOWN_FILLERS:
            continue
        if name.lower() not in real_attractions:
            issues.append(f"Ungrounded attraction: {name}")

    if issues:
        state.plan_valid = False
        state.critic_feedback = "\n".join(issues)
        state.last_critic_feedback = state.critic_feedback   # added
        state.attempt_count += 1
    else:
        state.plan_valid = True
        state.critic_feedback = "Plan validation passed."
        state.last_critic_feedback = state.critic_feedback   # added

    return state