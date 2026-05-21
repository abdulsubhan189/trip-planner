from dotenv import load_dotenv
load_dotenv()   # Loads API key from .env file
import os
import json
import re
import time
from groq import Groq
from schemas import TripState

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def regex_extract(query: str) -> dict:
    """Fallback extraction using regex when LLM fails."""
    q = query.lower()
    destination = ""
    budget = None
    days = None

    # Destination: after "to" or "trip to" – capture until next number or budget
    dest_match = re.search(r"to\s+([a-z\s]+?)(?=\s+\d|\s+day|\s+budget|\s+under|\s+$)", q)
    if dest_match:
        destination = dest_match.group(1).strip().title()
    if not destination:
        # fallback: first capitalized word
        words = query.split()
        for w in words:
            if w[0].isupper() and len(w) > 1:
                destination = w
                break

    # Budget: numbers with $ or "budget"
    bud_match = re.search(r"\$\s*(\d+\.?\d*)", q) or re.search(r"budget\s*[:=]?\s*\$?\s*(\d+\.?\d*)", q)
    if bud_match:
        budget = float(bud_match.group(1))

    # Days
    day_match = re.search(r"(\d+)\s*days?", q)
    if day_match:
        days = int(day_match.group(1))

    return {"destination": destination, "budget": budget, "days": days}

def orchestrator_llm(state: TripState) -> TripState:
    query = state.user_query
    prompt = f"""
    Extract travel information from the user query. Return ONLY JSON with keys: destination, budget, days.
    If a value is not mentioned, use null. Do not guess.
    Query: "{query}"
    Example output: {{"destination": "Hunza", "budget": 500.0, "days": 3}}
    """
    for attempt in range(3):  # up to 3 attempts with backoff
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            if data.get("destination"):
                state.destination = data["destination"]
            if data.get("budget") is not None:
                state.budget = float(data["budget"])
            if data.get("days") is not None:
                state.days = int(data["days"])
            return state  # success
        except Exception as e:
            print(f"LLM extraction attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(1 * (attempt + 1))  # 1s, 2s
            else:
                print("Using regex fallback extraction.")
                extracted = regex_extract(query)
                if extracted["destination"]:
                    state.destination = extracted["destination"]
                if extracted["budget"] is not None:
                    state.budget = extracted["budget"]
                if extracted["days"] is not None:
                    state.days = extracted["days"]
                # If still empty, set a sensible default for destination
                if not state.destination and query:
                    # take first word that looks like a place (capitalised)
                    words = query.split()
                    for w in words:
                        if w[0].isupper() and len(w) > 2:
                            state.destination = w
                            break
                return state
    return state