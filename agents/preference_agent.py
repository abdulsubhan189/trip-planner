from schemas import TripState

# Preference to weight mapping (default if not strongly expressed)
DEFAULT_WEIGHTS = {
    "adventure": 0.2,
    "culture": 0.2,
    "nature": 0.2,
    "relaxation": 0.2,
    "mixed": 0.2,
}
# Strong preference boost (when user says "love X")
STRONG_BOOST = 0.6

def preference_agent(state: TripState) -> TripState:
    query = state.user_query.lower()
    detected = []
    # Detect preferences
    if any(w in query for w in ["adventure", "trek", "hike", "jeep", "raft", "climb"]):
        detected.append("adventure")
    if any(w in query for w in ["culture", "museum", "history", "heritage", "fort", "temple"]):
        detected.append("culture")
    if any(w in query for w in ["relax", "peace", "cafe", "lake", "spa", "resort", "garden"]):
        detected.append("relaxation")
    if any(w in query for w in ["nature", "scenic", "viewpoint", "waterfall", "valley"]):
        detected.append("nature")

    if not detected:
        detected = ["mixed"]

    state.preferences = detected

    # Determine weights: if only one preference and strong keyword "love" etc., boost it
    strong_keywords = ["love", "only", "must", "strictly", "prefer"]
    is_strong = any(k in query for k in strong_keywords) and len(detected) == 1

    weights = DEFAULT_WEIGHTS.copy()
    if is_strong:
        main_pref = detected[0]
        for p in weights:
            weights[p] = 0.1
        weights[main_pref] = STRONG_BOOST
        # Normalize to sum 1.0
        total = sum(weights.values())
        for p in weights:
            weights[p] /= total
    else:
        # Equal distribution among detected preferences
        per_pref = 1.0 / len(detected)
        for p in weights:
            weights[p] = per_pref if p in detected else 0.0

    state.preference_weights = weights
    return state