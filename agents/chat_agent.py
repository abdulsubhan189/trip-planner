# agents/chat_agent.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
from agents.intent_agent import classify_intent

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def handle_casual_chat(message: str, intent_result: dict, history: list) -> dict:
    """Handle casual conversation using Groq."""
    try:
        messages = [
            {
                "role": "system",
                "content": """You are a friendly AI travel assistant called TripBot.
You help users plan trips and answer travel questions.
Keep responses short, friendly, and encouraging.
If user seems interested in travel, gently guide them to plan a trip.
Never be robotic. Be warm and conversational."""
            }
        ]
        # Add conversation history
        for turn in history[-6:]:
            messages.append(turn)
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        return {
            "type": "text",
            "message": response.choices[0].message.content.strip()
        }
    except Exception as e:
        return {
            "type": "text",
            "message": intent_result.get("raw_response", "Hello! How can I help you today?")
        }

def handle_question(message: str, intent_result: dict, history: list) -> dict:
    """Answer travel questions using Groq."""
    try:
        destination = intent_result.get("destination", "")
        messages = [
            {
                "role": "system",
                "content": f"""You are an expert travel assistant.
Answer travel questions accurately and concisely.
Focus on practical, helpful information.
If asked about {destination}, give specific accurate details.
Keep response under 150 words."""
            }
        ]
        for turn in history[-4:]:
            messages.append(turn)
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3,
            max_tokens=300
        )
        return {
            "type": "text",
            "message": response.choices[0].message.content.strip()
        }
    except Exception as e:
        return {
            "type": "text",
            "message": "I can help answer that! Could you provide more details?"
        }

def handle_show_trips(user_id: str) -> dict:
    """Return user's past trips."""
    try:
        from memory.trip_history import get_trip_history
        trips = get_trip_history(user_id, limit=5)
        if not trips:
            return {
                "type": "text",
                "message": "You haven't planned any trips yet! Would you like to plan one now?"
            }
        trip_list = "\n".join([
            f"• {t['destination']} — {t['days']} days, ${t['budget']} (Score: {t.get('plan_score', 'N/A')}/10)"
            for t in trips
        ])
        return {
            "type": "trips",
            "message": f"Here are your recent trips:\n{trip_list}",
            "trips": trips
        }
    except Exception as e:
        return {"type": "text", "message": "Could not load your trips right now."}

def handle_feedback(message: str, intent_result: dict, user_id: str) -> dict:
    """Save user feedback."""
    return {
        "type": "text",
        "message": "Thanks for the feedback! I'll use this to improve your future trip recommendations. 🌟"
    }

def handle_modify_plan(message: str, intent_result: dict, current_plan: dict) -> dict:
    """Handle plan modification requests."""
    if not current_plan:
        return {
            "type": "text",
            "message": "I don't have an active plan to modify. Would you like to plan a new trip?"
        }
    return {
        "type": "text",
        "message": "I'll modify your plan! Could you be more specific about what you'd like to change? For example: 'Make day 2 more adventurous' or 'Reduce the budget by $100'."
    }

def process_chat(
    message: str,
    user_id: str,
    session_id: str,
    conversation_history: list = [],
    current_plan: dict = None
) -> dict:
    """
    Main chat processor.
    Routes message to correct handler based on intent.
    Returns response dict with type and content.
    """
    # Step 1: Classify intent
    intent_result = classify_intent(message, conversation_history)
    intent = intent_result["intent"]

    print(f"Intent: {intent} | Dest: {intent_result.get('destination')} | Days: {intent_result.get('days')}")

    # Step 2: Route to correct handler
    if intent == "casual_chat":
        return handle_casual_chat(message, intent_result, conversation_history)

    elif intent == "plan_trip":
        # Extract planning params
        destination = intent_result.get("destination")
        days = intent_result.get("days")
        budget = intent_result.get("budget")
        preferences = intent_result.get("preferences", [])

        if not destination:
            return {
                "type": "text",
                "message": "I'd love to help plan your trip! Which destination are you thinking of? 🌍"
            }

        # Build query for existing pipeline
        query_parts = [destination]
        if days:
            query_parts.append(f"{days} days")
        if budget:
            query_parts.append(f"budget {budget}")
        if preferences:
            query_parts.append(f"I love {' and '.join(preferences)}")

        return {
            "type": "plan_request",
            "message": f"Perfect! Let me plan your {days or 3}-day trip to {destination}! 🗺️",
            "query": " ".join(query_parts),
            "destination": destination,
            "days": days,
            "budget": budget,
            "preferences": preferences,
            "travelers": intent_result.get("travelers", 1)   # <-- ADDED (Fix 2)
        }

    elif intent == "ask_question":
        return handle_question(message, intent_result, conversation_history)

    elif intent == "show_trips":
        return handle_show_trips(user_id)

    elif intent == "give_feedback":
        return handle_feedback(message, intent_result, user_id)

    elif intent == "modify_plan":
        return handle_modify_plan(message, intent_result, current_plan)

    elif intent in ("book_hotel", "book_flight"):
        return {
            "type": "text",
            "message": f"{'Hotel' if intent == 'book_hotel' else 'Flight'} booking is coming soon! For now, I can help you plan the perfect itinerary. Would you like to plan a trip?"
        }

    else:
        return handle_casual_chat(message, intent_result, conversation_history)