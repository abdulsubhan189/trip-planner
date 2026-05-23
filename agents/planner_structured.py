import logging
import math
import random
from typing import Dict, List, Tuple

from schemas import Activity, ActivityType, DayPlan, TripPlan, TripState
from tools.knowledge_tool import get_destination_info

logger = logging.getLogger(__name__)

MAX_DAILY_HOURS = 8.0
REST_BUFFER = 0.5
MIN_ACTIVITY_HOURS_PER_DAY = 3.0

# ---------------------------------------------------------------------------
# Smart fillers — last resort only, diverse types
# ---------------------------------------------------------------------------
SMART_FILLERS = [
    {"name": "Sunset viewpoint",         "type": "nature",      "cost_estimate": 0,  "duration_hours": 0.5, "weather_suitability": ["any"], "value_score": 6, "category": "activity"},
    {"name": "Local market stroll",      "type": "shopping",    "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 5, "category": "shopping"},
    {"name": "Café stop with view",      "type": "food",        "cost_estimate": 5,  "duration_hours": 0.5, "weather_suitability": ["any"], "value_score": 6, "category": "dining"},
    {"name": "Short heritage walk",      "type": "culture",     "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 5, "category": "activity"},
    {"name": "Scenic photography break", "type": "nature",      "cost_estimate": 0,  "duration_hours": 0.5, "weather_suitability": ["any"], "value_score": 7, "category": "activity"},
    {"name": "Evening leisure time",     "type": "relaxation",  "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 4, "category": "relaxation"},
    {"name": "Local fruit tasting",      "type": "food",        "cost_estimate": 3,  "duration_hours": 0.5, "weather_suitability": ["any"], "value_score": 6, "category": "dining"},
    {"name": "Short nature trail",       "type": "nature",      "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 6, "category": "activity"},
    {"name": "Riverside relaxation",     "type": "relaxation",  "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 5, "category": "relaxation"},
    {"name": "Cultural music evening",   "type": "culture",     "cost_estimate": 10, "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 7, "category": "entertainment"},
    {"name": "Handicraft workshop",      "type": "culture",     "cost_estimate": 15, "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 6, "category": "activity"},
    {"name": "Morning mountain walk",    "type": "nature",      "cost_estimate": 0,  "duration_hours": 1.0, "weather_suitability": ["any"], "value_score": 6, "category": "activity"},
]

# ---------------------------------------------------------------------------
# Travel time (Euclidean, 40 km/h average)
# ---------------------------------------------------------------------------
def _travel_time_minutes(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return 30.0
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    km = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return (km / 40.0) * 60

# ---------------------------------------------------------------------------
# Day usage
# ---------------------------------------------------------------------------
def compute_day_usage(activities: List[Dict], hotel_coords: Tuple) -> Tuple[float, float, float]:
    if not activities:
        return 0.0, 0.0, 0.0
    h_lat, h_lon = hotel_coords
    activity_hours = sum(a.get("duration_hours", 1.0) for a in activities)
    travel_hours = 0.0
    if h_lat is not None:
        travel_hours += _travel_time_minutes(h_lat, h_lon, activities[0].get("lat"), activities[0].get("lon")) / 60
    for i in range(len(activities) - 1):
        a1, a2 = activities[i], activities[i + 1]
        travel_hours += _travel_time_minutes(a1.get("lat"), a1.get("lon"), a2.get("lat"), a2.get("lon")) / 60
    if h_lat is not None:
        travel_hours += _travel_time_minutes(activities[-1].get("lat"), activities[-1].get("lon"), h_lat, h_lon) / 60
    return activity_hours + travel_hours + REST_BUFFER, travel_hours, activity_hours

# ---------------------------------------------------------------------------
# Weather helpers
# ---------------------------------------------------------------------------
_WEATHER_NORMALIZER = {
    "sunny": "sunny", "clear": "sunny", "clear sky": "sunny",
    "cloudy": "cloudy", "overcast": "cloudy", "overcast clouds": "cloudy",
    "few clouds": "cloudy", "scattered clouds": "cloudy", "broken clouds": "cloudy",
    "mist": "cloudy", "fog": "cloudy", "haze": "cloudy", "moderate": "cloudy",
    "rain": "rain", "rainy": "rain", "light rain": "rain", "heavy rain": "rain", "drizzle": "rain",
    "snow": "snow", "light snow": "snow", "heavy snow": "snow", "sleet": "snow",
}

def _normalize_weather(raw: str) -> str:
    r = raw.strip().lower()
    if r in _WEATHER_NORMALIZER:
        return _WEATHER_NORMALIZER[r]
    for k, v in _WEATHER_NORMALIZER.items():
        if k in r:
            return v
    return "cloudy"

# ---------------------------------------------------------------------------
# ActivityType helpers
# ---------------------------------------------------------------------------
_TYPE_FALLBACK = {
    "historical": "culture", "lodging": "relaxation", "dining": "food",
    "transport": "sightseeing", "tour": "sightseeing",
}
_VALID_SUITS = {"any", "sunny", "indoor", "avoid_cold", "avoid_rain"}
_SUIT_MAP = {
    "cloudy": "any", "overcast": "any", "moderate": "any",
    "clear": "sunny", "rain": "avoid_rain", "rainy": "avoid_rain",
    "snow": "avoid_cold", "snowy": "avoid_cold", "cold": "avoid_cold",
}

def _resolve_activity_type(raw: str) -> ActivityType:
    t = _TYPE_FALLBACK.get(raw.strip().lower(), raw.strip().lower())
    try:
        return ActivityType(t)
    except ValueError:
        return ActivityType.SIGHTSEEING

def _resolve_weather_suit(tokens: List[str]) -> str:
    for token in tokens:
        t = token.strip().lower()
        if t in _VALID_SUITS:
            return t
        if t in _SUIT_MAP:
            return _SUIT_MAP[t]
    return "any"

# ---------------------------------------------------------------------------
# Utility scoring
# ---------------------------------------------------------------------------
def _compute_utility(attraction: Dict, preferences: List[str], weather_cond: str, pref_weights: Dict) -> float:
    score = 5.0
    a_type = attraction.get("type", "sightseeing")
    score += pref_weights.get(a_type, 0.1) * 8
    for p in preferences:
        if p == "adventure" and a_type in ["adventure", "nature"]:
            score += 2
        elif p == "culture" and a_type in ["culture", "shopping", "historical"]:
            score += 2
        elif p == "relaxation" and a_type in ["nature", "relaxation"]:
            score += 2
    intensity = attraction.get("intensity", 2)
    if intensity == 3:
        score += 1
    elif intensity >= 4:
        score -= 1
    if attraction.get("cost_estimate", 0) == 0:
        score += 0.5
    ws = attraction.get("weather_score", {})
    defaults = {"sunny": 7, "cloudy": 5, "rain": 2, "snow": 1}
    w_score = ws.get(weather_cond, defaults.get(weather_cond, 5))
    is_outdoor = not attraction.get("indoor", False)
    if weather_cond in ("rain", "snow") and is_outdoor:
        score *= 0.4 if w_score < 5 else 0.7
    else:
        score *= w_score / 10.0
    return max(0.0, min(10.0, score))

# ---------------------------------------------------------------------------
# Hotel coords
# ---------------------------------------------------------------------------
def _get_hotel_coords(dest_info: Dict) -> Tuple:
    hz = dest_info.get("hotel_zone", {})
    coords = dest_info.get("coordinates", {})
    lat = hz.get("lat") or coords.get("lat")
    lon = hz.get("lon") or coords.get("lon")
    return (lat, lon)

# ---------------------------------------------------------------------------
# Candidate pool — keep ALL attractions, compute utility
# ---------------------------------------------------------------------------
def _get_candidates(destination: str, weather_cond: str, preferences: List[str],
                    pref_weights: Dict, state: TripState) -> List[Dict]:
    dest_info = get_destination_info(destination)
    attractions = dest_info.get("attractions", [])
    if not attractions:
        return [{
            "name": "Local sightseeing", "type": "sightseeing", "cost_estimate": 0,
            "duration_hours": 2, "lat": 0.0, "lon": 0.0,
            "weather_score": {"sunny": 5, "cloudy": 5, "rain": 5, "snow": 5},
            "weather_suitability": ["any"], "intensity": 1, "value_score": 5,
        }]
    result = []
    for a in attractions:
        suit = a.get("weather_suitability", ["any"])
        if not ("any" in suit or weather_cond in suit or (a.get("indoor", False) and weather_cond in ("rain", "snow"))):
            continue
        a = dict(a)  # don't mutate original
        a["utility"] = _compute_utility(a, preferences, weather_cond, pref_weights)
        if "value_score" not in a:
            a["value_score"] = a["utility"] / 2
        result.append(a)

    # --- Boost liked activities ---
    if hasattr(state, 'liked_activities') and state.liked_activities:
        for a in result:
            if a["name"] in state.liked_activities:
                a["value_score"] = min(10, a["value_score"] + 2)

    # --- Remove disliked activities ---
    if hasattr(state, 'disliked_activities') and state.disliked_activities:
        result = [a for a in result if a["name"] not in state.disliked_activities]

    return result
# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _score_plan(days: List[List[Dict]], preferences: List[str], activities_budget: float, hotel_coords: Tuple) -> float:
    all_acts = [a for day in days for a in day]
    if not all_acts:
        return 0.0

    # 1. Enjoyment
    enjoyment = sum(a.get("value_score", 5) for a in all_acts) / len(all_acts) / 10.0

    # 2. Preference match
    if preferences and preferences[0] != "mixed":
        pref_count = sum(1 for a in all_acts if a.get("type") == preferences[0])
        pref_match = pref_count / len(all_acts)
    else:
        pref_match = 0.5

    # 3. Budget utilisation – reward 85%+ as perfect
    total_spent = sum(a.get("cost_estimate", 0) for a in all_acts)
    if activities_budget > 0:
        target = activities_budget * 0.85
        utilisation = min(total_spent / target, 1.0)
        over_penalty = max(0.0, (total_spent - activities_budget) / activities_budget)
        budget_score = utilisation - over_penalty
    else:
        budget_score = 1.0

    # 4. Density – target 5h per day (not 8h)
    densities = [min(1.0, sum(a.get("duration_hours", 1) for a in day) / 5.0) for day in days]
    density = sum(densities) / len(densities) if densities else 0.0

    # 5. Travel efficiency
    total_travel = sum(compute_day_usage(day, hotel_coords)[1] for day in days)
    max_travel = MAX_DAILY_HOURS * len(days)
    travel_eff = 1.0 - min(1.0, total_travel / max_travel) if max_travel > 0 else 1.0

    # 6. Diversity
    types = [a.get("type", "sightseeing") for a in all_acts]
    diversity = len(set(types)) / len(types) if types else 0.0

    # 7. Fill rate – weight increased
    filled_days = sum(1 for day in days if day)
    fill_rate = filled_days / len(days) if days else 0.0

    # Adjusted weights: travel_eff ↓, fill_rate ↑
    raw = (enjoyment * 0.20 + pref_match * 0.25 + budget_score * 0.15 +
           density * 0.15 + travel_eff * 0.05 + diversity * 0.10 + fill_rate * 0.10)
    return max(0.0, min(10.0, raw * 10.0))

# ---------------------------------------------------------------------------
# Day-type tagging
# ---------------------------------------------------------------------------
def _tag_day_types(days: List[List[Dict]], hotel_coords: Tuple) -> List[str]:
    result = []
    for day in days:
        total, _, _ = compute_day_usage(day, hotel_coords)
        if total >= 7.0:
            result.append("Heavy")
        elif total >= 4.0:
            result.append("Medium")
        else:
            result.append("Recovery")
    return result

# ---------------------------------------------------------------------------
# PHASE 1 + 2 — Anchor + Fill distribution
# Every day gets 1 anchor first, then fill remaining slots with mix of paid/free
# ---------------------------------------------------------------------------
def _distribute(
    candidates: List[Dict],
    num_days: int,
    activities_budget: float,
    hotel_coords: Tuple,
    max_per_day: int = 3,
    seed: int = 0,
) -> List[List[Dict]]:
    random.seed(seed)
    days: List[List[Dict]] = [[] for _ in range(num_days)]
    placed_names: set = set()

    free = sorted([c for c in candidates if c.get("cost_estimate", 0) == 0],
                  key=lambda x: x.get("value_score", 0), reverse=True)
    paid = sorted([c for c in candidates if c.get("cost_estimate", 0) > 0],
                  key=lambda x: x.get("value_score", 0), reverse=True)

    # ── PHASE 1: One anchor per day ──────────────────────────────────────
    # Alternate between free and paid anchors so every day has a real activity
    anchor_pool = []
    fi, pi = 0, 0
    while fi < len(free) or pi < len(paid):
        if fi < len(free):
            anchor_pool.append(free[fi]); fi += 1
        if pi < len(paid):
            anchor_pool.append(paid[pi]); pi += 1

    for day_idx in range(num_days):
        for act in anchor_pool:
            if act["name"] in placed_names:
                continue
            days[day_idx].append(act)
            placed_names.add(act["name"])
            break  # one anchor placed, move to next day

    # ── PHASE 2: Fill remaining slots (mix free + paid) ──────────────────
    remaining_free = [a for a in free if a["name"] not in placed_names]
    remaining_paid = [a for a in paid if a["name"] not in placed_names]
    fill_pool = []
    for a in remaining_free + remaining_paid:
        if a["name"] not in placed_names:
            fill_pool.append(a)

    day_pointer = 0
    for act in fill_pool:
        for offset in range(num_days):
            day_idx = (day_pointer + offset) % num_days
            if len(days[day_idx]) >= max_per_day:
                continue
            usage, _, _ = compute_day_usage(days[day_idx] + [act], hotel_coords)
            if usage <= MAX_DAILY_HOURS:
                days[day_idx].append(act)
                placed_names.add(act["name"])
                day_pointer = (day_idx + 1) % num_days
                break

    return days

# ---------------------------------------------------------------------------
# PHASE 3 — Budget enforcement
# Remove most expensive + lowest value activities until within budget
# Never remove the last activity from any day
# Never remove free activities (protected)
# ---------------------------------------------------------------------------
def _enforce_budget(days: List[List[Dict]], activities_budget: float) -> List[List[Dict]]:
    # Remove activities that alone exceed the entire budget
    for day_idx, day in enumerate(days):
        days[day_idx] = [
            a for a in day
            if a.get("cost_estimate", 0) <= activities_budget
        ]

    total = sum(a.get("cost_estimate", 0) for day in days for a in day)
    if total <= activities_budget:
        return days

    # Build list of removable (paid, not the only activity in their day)
    for _ in range(200):
        total = sum(a.get("cost_estimate", 0) for day in days for a in day)
        if total <= activities_budget:
            break

        candidates_to_remove = []
        for d_idx, day in enumerate(days):
            paid_in_day = [(a_idx, a) for a_idx, a in enumerate(day) if a.get("cost_estimate", 0) > 0]
            if not paid_in_day:
                continue
            for a_idx, act in paid_in_day:
                # Don't remove if it's the only activity in this day
                if len(day) == 1:
                    continue
                candidates_to_remove.append((d_idx, a_idx, act))

        if not candidates_to_remove:
            break

        # Remove highest cost + lowest value_score first
        candidates_to_remove.sort(key=lambda x: (-x[2].get("cost_estimate", 0), x[2].get("value_score", 0)))
        d_idx, a_idx, _ = candidates_to_remove[0]
        days[d_idx].pop(a_idx)

    return days

# ---------------------------------------------------------------------------
# PHASE 4 — Fill thin days
# Use remaining budget + real cheap attractions first, then fillers
# ---------------------------------------------------------------------------
def _fill_thin_days(
    days: List[List[Dict]],
    all_candidates: List[Dict],
    hotel_coords: Tuple,
    activities_budget: float,
    used_names: set,
) -> List[List[Dict]]:
    total_spent = sum(a.get("cost_estimate", 0) for day in days for a in day)
    remaining_budget = activities_budget - total_spent

    # Candidates not yet placed, sorted by value_score desc
    unused_real = sorted(
        [c for c in all_candidates if c["name"] not in used_names],
        key=lambda x: x.get("value_score", 0), reverse=True
    )

    for day_idx, day in enumerate(days):
        act_hours = sum(a.get("duration_hours", 1) for a in day)
        if act_hours >= MIN_ACTIVITY_HOURS_PER_DAY + 1.5:
            continue

        usage, _, _ = compute_day_usage(day, hotel_coords)
        capacity = MAX_DAILY_HOURS - usage

        # Try real attractions first
        for act in list(unused_real):
            if act["name"] in used_names:
                continue
            cost = act.get("cost_estimate", 0)
            if cost > remaining_budget and cost > 0:
                continue
            trial_usage, _, _ = compute_day_usage(day + [act], hotel_coords)
            if trial_usage <= MAX_DAILY_HOURS:
                day.append(act)
                used_names.add(act["name"])
                unused_real.remove(act)
                remaining_budget -= cost
                act_hours += act.get("duration_hours", 1)
                if act_hours >= MIN_ACTIVITY_HOURS_PER_DAY:
                    break

        # If still thin, use smart fillers (globally deduplicated)
        if act_hours < MIN_ACTIVITY_HOURS_PER_DAY:
            for filler in SMART_FILLERS:
                if filler["name"] in used_names:
                    continue
                cost = filler.get("cost_estimate", 0)
                if cost > remaining_budget and cost > 0:
                    continue
                trial_usage, _, _ = compute_day_usage(day + [filler], hotel_coords)
                if trial_usage <= MAX_DAILY_HOURS:
                    f = filler.copy()
                    f["lat"] = hotel_coords[0] or 0.0
                    f["lon"] = hotel_coords[1] or 0.0
                    day.append(f)
                    used_names.add(filler["name"])
                    remaining_budget -= cost
                    act_hours += f.get("duration_hours", 1)
                    if act_hours >= MIN_ACTIVITY_HOURS_PER_DAY:
                        break

    return days

# ---------------------------------------------------------------------------
# Fix 2: Nearest‑neighbor route optimisation within a day
# ---------------------------------------------------------------------------
def _optimize_day_route(activities: List[Dict], hotel_coords: Tuple) -> List[Dict]:
    """
    Reorder activities to minimise travel distance starting and ending at hotel.
    Simple greedy nearest‑neighbor.
    """
    if len(activities) <= 1:
        return activities
    # copy
    remaining = activities[:]
    ordered = []
    # start from hotel
    current_lat, current_lon = hotel_coords[0], hotel_coords[1]
    # if hotel coords are None, fallback to first activity's coordinates
    if current_lat is None or current_lon is None:
        return activities  # cannot optimise without hotel coords

    while remaining:
        # find nearest remaining activity to current position
        nearest_idx = 0
        nearest_dist = _travel_time_minutes(current_lat, current_lon,
                                            remaining[0].get("lat"), remaining[0].get("lon"))
        for i, act in enumerate(remaining[1:], 1):
            d = _travel_time_minutes(current_lat, current_lon,
                                     act.get("lat"), act.get("lon"))
            if d < nearest_dist:
                nearest_dist = d
                nearest_idx = i
        chosen = remaining.pop(nearest_idx)
        ordered.append(chosen)
        current_lat, current_lon = chosen.get("lat"), chosen.get("lon")
    return ordered

# ---------------------------------------------------------------------------
# Fix 3: Cap unrealistic travel legs (> 90 min)
# ---------------------------------------------------------------------------
def _fix_long_travel_legs(days: List[List[Dict]], hotel_coords: Tuple) -> List[List[Dict]]:
    """
    If any leg between two consecutive activities in a day exceeds 90 minutes,
    attempt to move the second activity to another day with sufficient capacity.
    """
    max_leg_minutes = 90
    # First compute per-day usage (time capacity) for quick checks
    usage = [compute_day_usage(day, hotel_coords)[0] for day in days]
    for d_idx, day in enumerate(days):
        if len(day) < 2:
            continue
        # Check travel times between consecutive activities
        for i in range(len(day) - 1):
            a1 = day[i]
            a2 = day[i+1]
            leg_time = _travel_time_minutes(a1.get("lat"), a1.get("lon"), a2.get("lat"), a2.get("lon"))
            if leg_time <= max_leg_minutes:
                continue
            # Leg too long – try to move a2 to another day
            moved = False
            for other_idx in range(len(days)):
                if other_idx == d_idx:
                    continue
                # Check if adding a2 fits in other day (time)
                trial = days[other_idx] + [a2]
                new_usage = compute_day_usage(trial, hotel_coords)[0]
                if new_usage <= MAX_DAILY_HOURS:
                    # Also check budget? Not needed, we are moving, not adding cost.
                    days[other_idx].append(a2)
                    # Remove from current day
                    days[d_idx].pop(i+1)
                    # Recompute usage for both days
                    usage[d_idx] = compute_day_usage(days[d_idx], hotel_coords)[0]
                    usage[other_idx] = compute_day_usage(days[other_idx], hotel_coords)[0]
                    moved = True
                    break
            if not moved:
                logger.warning(f"Long travel leg ({leg_time:.0f} min) between {a1['name']} and {a2['name']} in day {d_idx+1} could not be resolved.")
    return days

# ---------------------------------------------------------------------------
# Day diversity check
# ---------------------------------------------------------------------------
def _check_day_diversity(
    days: List[List[Dict]],
    candidates: List[Dict],
    preferences: List[str],
    hotel_coords: Tuple,
    activities_budget: float,
) -> List[List[Dict]]:
    """
    Ensure no two consecutive days have the same primary activity type.
    Also ensure preference type appears on every day if possible.
    """
    top_pref = preferences[0] if preferences else None
    used_names = {a["name"] for day in days for a in day}

    def primary_type(day):
        if not day:
            return None
        type_counts = {}
        for a in day:
            t = a.get("type", "sightseeing")
            type_counts[t] = type_counts.get(t, 0) + 1
        return max(type_counts, key=type_counts.get)

    # Pass 1 — inject preference activity into days that lack it
    if top_pref:
        pref_candidates = sorted(
            [c for c in candidates
             if c.get("type") == top_pref
             and c["name"] not in used_names
             and c.get("cost_estimate", 0) == 0],  # free ones only, safe to add
            key=lambda x: -x.get("value_score", 0)
        )
        for day in days:
            day_types = [a.get("type") for a in day]
            if top_pref not in day_types and pref_candidates:
                candidate = pref_candidates[0]
                trial_usage, _, _ = compute_day_usage(day + [candidate], hotel_coords)
                if trial_usage <= MAX_DAILY_HOURS:
                    day.append(candidate)
                    used_names.add(candidate["name"])
                    pref_candidates.pop(0)

    # Pass 2 — fix consecutive days with same primary type
    for i in range(len(days) - 1):
        if primary_type(days[i]) == primary_type(days[i + 1]):
            # Try to swap a low-value activity on day i+1
            # with an unused candidate of a different type
            current_type = primary_type(days[i + 1])
            day = days[i + 1]
            # Find lowest value non-preferred activity to potentially swap
            swappable = sorted(
                [idx for idx, a in enumerate(day)
                 if a.get("type") == current_type
                 and a.get("cost_estimate", 0) == 0],  # only swap free activities
                key=lambda idx: day[idx].get("value_score", 0)
            )
            if not swappable:
                continue
            swap_idx = swappable[0]
            # Find a free unused candidate of different type
            replacement = next(
                (c for c in candidates
                 if c["name"] not in used_names
                 and c.get("type") != current_type
                 and c.get("cost_estimate", 0) == 0),
                None
            )
            if replacement:
                used_names.discard(day[swap_idx]["name"])
                day[swap_idx] = replacement
                used_names.add(replacement["name"])

    return days

# ---------------------------------------------------------------------------
# Strategy application
# ---------------------------------------------------------------------------
def _apply_strategy(candidates: List[Dict], strategy: str, preferences: List[str], activities_budget: float) -> List[Dict]:
    """Return a re-sorted copy of candidates based on strategy."""
    c = [dict(a) for a in candidates]  # shallow copy, don't mutate originals

    if strategy == "preference_first":
        # Sort by preference match first, then value_score
        top_pref = preferences[0] if preferences else "sightseeing"
        c.sort(key=lambda x: (
            -(1 if x.get("type") == top_pref else 0),
            -x.get("value_score", 0)
        ))

    elif strategy == "budget_first":
        # Sort by cost descending — spend the budget fully
        # Paid activities first, sorted by cost desc within budget
        affordable = [x for x in c if x.get("cost_estimate", 0) <= activities_budget]
        over = [x for x in c if x.get("cost_estimate", 0) > activities_budget]
        affordable.sort(key=lambda x: -x.get("cost_estimate", 0))
        c = affordable + over

    elif strategy == "density_first":
        # Sort by duration descending — fill hours
        c.sort(key=lambda x: -x.get("duration_hours", 1))

    elif strategy == "diversity_first":
        # Interleave different types so each day gets variety
        from collections import defaultdict
        by_type = defaultdict(list)
        for a in sorted(c, key=lambda x: -x.get("value_score", 0)):
            by_type[a.get("type", "sightseeing")].append(a)
        interleaved = []
        while any(by_type.values()):
            for t in list(by_type.keys()):
                if by_type[t]:
                    interleaved.append(by_type[t].pop(0))
        c = interleaved

    elif strategy == "balanced":
        # Default — value_score descending (existing behaviour)
        c.sort(key=lambda x: -x.get("value_score", 0))

    return c

# ---------------------------------------------------------------------------
# Generate best plan from multiple strategies
# ---------------------------------------------------------------------------
STRATEGIES = ["preference_first", "budget_first", "density_first", "diversity_first", "balanced"]

def _generate_best_plan(
    candidates: List[Dict],
    num_days: int,
    activities_budget: float,
    hotel_coords: Tuple,
    preferences: List[str],
    state: TripState,
    num_seeds: int = 3,
) -> Tuple[List[List[Dict]], float]:
    best_plan = None
    best_score = -1.0

    # --- Use attempt count to vary strategy order ---
    attempt = getattr(state, 'attempt_count', 0)
    strategy_start = (attempt * 2) % len(STRATEGIES)
    strategies_to_try = STRATEGIES[strategy_start:] + STRATEGIES[:strategy_start]

    for strategy in strategies_to_try:
        try:
            # Apply strategy — re-sort candidates
            strategy_candidates = _apply_strategy(candidates, strategy, preferences, activities_budget)

            # Phase 1+2: Distribute
            days = _distribute(strategy_candidates, num_days, activities_budget, hotel_coords, max_per_day=3, seed=0)

            # Phase 3: Budget enforcement
            days = _enforce_budget(days, activities_budget)

            # Phase 4: Fill thin days
            used_names = {a["name"] for day in days for a in day}
            days = _fill_thin_days(days, strategy_candidates, hotel_coords, activities_budget, used_names)

            # Spend remaining budget
            total_spent = sum(a.get("cost_estimate", 0) for day in days for a in day)
            remaining = activities_budget - total_spent
            if remaining >= 10:
                unused = sorted(
                    [c for c in strategy_candidates if c["name"] not in used_names
                     and 0 < c.get("cost_estimate", 0) <= remaining],
                    key=lambda x: x.get("value_score", 0), reverse=True
                )
                for act in unused:
                    placed = False
                    for day in days:
                        trial_usage, _, _ = compute_day_usage(day + [act], hotel_coords)
                        if trial_usage <= MAX_DAILY_HOURS:
                            day.append(act)
                            used_names.add(act["name"])
                            remaining -= act.get("cost_estimate", 0)
                            placed = True
                            break
                    if placed and remaining < 10:
                        break

            # Route optimisation per day
            for i, day in enumerate(days):
                if day:
                    days[i] = _optimize_day_route(day, hotel_coords)

            # Fix long travel legs
            days = _fix_long_travel_legs(days, hotel_coords)

            # Ensure no day is empty
            used_names = {a["name"] for day in days for a in day}
            for i, day in enumerate(days):
                if not day:
                    for filler in SMART_FILLERS:
                        if filler["name"] not in used_names:
                            f = filler.copy()
                            f["lat"] = hotel_coords[0] or 0.0
                            f["lon"] = hotel_coords[1] or 0.0
                            days[i] = [f]
                            used_names.add(filler["name"])
                            break

            score = _score_plan(days, preferences, activities_budget, hotel_coords)
            if score > best_score:
                best_score = score
                best_plan = [list(day) for day in days]  # deep copy best plan

        except Exception as e:
            logger.warning(f"Strategy {strategy} failed: {e}")
            continue

    # ---- Apply day diversity check to the best plan ----
    if best_plan:
        best_plan = _check_day_diversity(
            best_plan, candidates, preferences, hotel_coords, activities_budget
        )

    return best_plan, best_score

# ---------------------------------------------------------------------------
# Emergency fallback
# ---------------------------------------------------------------------------
def _simple_fallback(state: TripState, reason: str = "") -> TripState:
    dest = state.destination or "your destination"
    days = max(state.days, 1) if state.days else 3
    lines = [f"📍 Simple itinerary for {dest}", f"Budget: ${state.budget:.2f}", ""]
    for d in range(1, days + 1):
        lines.append(f"Day {d}: Explore local attractions and enjoy free time.")
    state.itinerary = "\n".join(lines)
    state.final_response = state.itinerary
    if reason:
        state.critic_feedback = f"Fallback due to {reason}"
    return state

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def structured_planner(state: TripState) -> TripState:
    try:
        if not state.destination:
            return _simple_fallback(state, "no destination")

        dest_info = get_destination_info(state.destination)
        hotel_coords = _get_hotel_coords(dest_info)

        weather_cond = _normalize_weather(
            state.weather_info.get("condition", "moderate") if state.weather_info else "moderate"
        )

        pref_weights = getattr(state, "preference_weights", {"sightseeing": 0.2})
        candidates = _get_candidates(state.destination, weather_cond, state.preferences, pref_weights, state)
        if not candidates:
            return _simple_fallback(state, "no suitable attractions")

        num_days = state.days if state.days and state.days > 0 else 3

        activities_budget = (
            state.budget_allocation.activities
            if hasattr(state, "budget_allocation") and state.budget_allocation
            else state.budget
        )

        best_plan, best_score = _generate_best_plan(
            candidates, num_days, activities_budget, hotel_coords,
            state.preferences, state, num_seeds=3
        )

        if best_plan is None:
            return _simple_fallback(state, "plan generation failed")

        day_types = _tag_day_types(best_plan, hotel_coords)
        daily_plans = []
        total_spent = 0.0

        for day_num, acts in enumerate(best_plan, 1):
            usage, travel_hours, act_hours = compute_day_usage(acts, hotel_coords)
            travel_mins = travel_hours * 60
            day_type = day_types[day_num - 1]
            title = f"Day {day_num} — {act_hours:.1f}h activities + {travel_mins:.0f} min travel  [{day_type}]"

            activities_objs = []
            day_cost = 0.0
            for act in acts:
                act_type = _resolve_activity_type(act.get("type", "sightseeing"))
                raw_suit = act.get("weather_suitability", ["any"])
                if isinstance(raw_suit, str):
                    raw_suit = [s.strip() for s in raw_suit.split(",")]
                weather_suit = _resolve_weather_suit(raw_suit)
                notes_parts = [f"Duration: {act.get('duration_hours', 1)}h"]
                if act.get("category"):
                    notes_parts.append(act["category"])
                if act.get("notes"):
                    notes_parts.append(act["notes"])

                obj = Activity(
                    name=act["name"],
                    location=state.destination,
                    activity_type=act_type,
                    estimated_cost=act.get("cost_estimate", 0),
                    weather_suitability=weather_suit,
                    confidence_score=act.get("value_score", 5) / 10,
                    notes=" | ".join(notes_parts),
                )
                activities_objs.append(obj)
                day_cost += obj.estimated_cost

            total_spent += day_cost
            daily_plans.append(DayPlan(
                day_number=day_num,
                title=title,
                activities=activities_objs,
                total_cost=day_cost,
            ))

        plan = TripPlan(
            destination=state.destination,
            days=num_days,
            budget=state.budget,
            budget_status=state.budget_status,
            weather_info=state.weather_info or {},
            daily_plans=daily_plans,
            overall_notes=[
                f"Total spent: ${total_spent:.2f}",
                f"Plan score: {best_score:.1f}/10",
                f"Daily capacity: {MAX_DAILY_HOURS}h (activities + travel + {REST_BUFFER}h buffer).",
                "Optimised for density, diversity, travel efficiency, and global balance.",
            ],
        )
        state.structured_plan = plan
        return state

    except Exception as e:
        logger.error(f"Planner error: {e}")
        return _simple_fallback(state, str(e))