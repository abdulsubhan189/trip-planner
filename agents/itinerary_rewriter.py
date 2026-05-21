import os
from groq import Groq
from schemas import TripState

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def itinerary_rewriter(state: TripState) -> TripState:
    if not state.itinerary:
        return state
    prompt = f"""
    Rewrite the following itinerary to be more engaging, clear, and well‑structured. Keep all facts.
    Itinerary:
    {state.itinerary}
    Rewritten version:
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        state.itinerary = response.choices[0].message.content
    except Exception as e:
        print(f"Rewriter error: {e}")
    return state