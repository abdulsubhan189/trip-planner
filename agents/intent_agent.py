# agents/intent_agent.py
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def classify_intent(message: str, conversation_history: list = []) -> dict:
    try:
        system_prompt = """You are a JSON-only intent classifier for a travel planning assistant.
NEVER use markdown. NEVER explain. Return ONLY a raw JSON object.

Classify the user message into one of these intents:
- casual_chat: greetings, thanks, how are you, small talk
- plan_trip: wants to plan a trip, visit a place, travel somewhere
- modify_plan: wants to change an existing plan (change day, budget, preference)
- ask_question: asking about weather, distance, best time, visa, cost
- give_feedback: rating a trip, liked or disliked something
- show_trips: wants to see past trips or history
- book_hotel: wants to find or book a hotel
- book_flight: wants to find or book a flight

Extract these entities if present:
- destination: city or country name (string or null)
- days: number of days (integer or null)
- budget: budget in USD (number or null)
- preferences: list of strings from [adventure, culture, nature, relaxation, food]
- travelers: number of people traveling (integer or null)
- travel_start: start date if mentioned (string or null, format: DD Mon YYYY)
- travel_days: duration in days (integer or null)
- raw_response: a short friendly reply to the user

Return ONLY this JSON with no extra text:
{"intent": "...", "confidence": 0.9, "destination": null, "days": null, "budget": null, "preferences": [], "travelers": null, "travel_start": null, "travel_days": null, "modify_target": null, "raw_response": "..."}"""

        user_prompt = f"User message: {message}"

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content.strip()

        # Clean any markdown if model still adds it
        content = content.replace("```json", "").replace("```", "").strip()

        # Extract JSON object
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]

        result = json.loads(content)

        # Ensure all fields exist
        result.setdefault("intent", "casual_chat")
        result.setdefault("confidence", 0.5)
        result.setdefault("destination", None)
        result.setdefault("days", None)
        result.setdefault("budget", None)
        result.setdefault("preferences", [])
        result.setdefault("travelers", None)
        result.setdefault("travel_start", None)
        result.setdefault("travel_days", None)
        result.setdefault("modify_target", None)
        result.setdefault("raw_response", "I'm here to help you plan your trip!")

        return result

    except Exception as e:
        print(f"Intent classification failed: {e}")
        return _fallback_classify(message)


def _fallback_classify(message: str) -> dict:
    msg = message.lower()

    modify_keywords = ["change", "modify", "update", "replace", "make it", "add more", "remove", "cheaper", "shorter"]
    plan_keywords = ["plan", "trip", "travel", "visit", "go to", "tour", "days", "budget", "itinerary", "vacation", "holiday"]
    question_keywords = ["what", "how", "when", "where", "why", "which", "weather", "temperature", "visa", "cost", "best time"]
    casual_keywords = ["hello", "hi", "hey", "thanks", "thank you", "bye", "how are you", "good morning", "good evening"]

    if any(k in msg for k in modify_keywords):
        intent = "modify_plan"
    elif any(k in msg for k in plan_keywords):
        intent = "plan_trip"
    elif any(k in msg for k in question_keywords):
        intent = "ask_question"
    elif any(k in msg for k in casual_keywords):
        intent = "casual_chat"
    else:
        intent = "casual_chat"

    destination = None
    dest_match = re.search(r"(?:to|in|visit|trip to|travel to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", message)
    if dest_match:
        destination = dest_match.group(1)

    days = None
    day_match = re.search(r"(\d+)\s*days?", msg)
    if day_match:
        days = int(day_match.group(1))

    budget = None
    bud_match = re.search(r"\$\s*(\d+)|budget\s*(\d+)|under\s*\$?\s*(\d+)", msg)
    if bud_match:
        budget = float(next(g for g in bud_match.groups() if g))

    # Generate casual response
    if intent == "casual_chat":
        if "hello" in msg or "hi" in msg or "hey" in msg:
            raw_response = "Hello! I'm your AI travel assistant. Where would you like to go?"
        elif "how are you" in msg:
            raw_response = "I'm doing great, thanks for asking! Ready to plan your next adventure?"
        elif "thanks" in msg or "thank you" in msg:
            raw_response = "You're welcome! Let me know if you need anything else."
        else:
            raw_response = "I'm here to help you plan amazing trips! Where would you like to go?"
    else:
        raw_response = "I'm here to help you plan your perfect trip!"

    return {
        "intent": intent,
        "confidence": 0.6,
        "destination": destination,
        "days": days,
        "budget": budget,
        "preferences": [],
        "modify_target": None,
        "raw_response": raw_response
    }