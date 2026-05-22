import os
from dotenv import load_dotenv
from schemas import TripState
from graph import build_advanced_graph

# Load environment variables from .env file
load_dotenv()

# Optionally hardcode key here ONLY if .env is not used (not recommended)
# os.environ["GROQ_API_KEY"] = "your_key_here"

def run_test(query: str):
    print("\n" + "="*60)
    print(f"QUERY: {query}")
    print("="*60)
    state = TripState(user_query=query)
    graph = build_advanced_graph()
    final = graph.invoke(state)
    print("\n✅ FINAL ITINERARY:\n")
    print(final.get("final_response", "No response."))

if __name__ == "__main__":
    # Ensure API key is set
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ ERROR: GROQ_API_KEY not found. Set it in .env file or environment variables.")
    else:
        # run_test("Skardu 5 days budget 800, I love adventure")
        # run_test("Hunza 3 days budget 300, prefer culture")
        run_test("Lahore 3 days budget 500, prefer culture")