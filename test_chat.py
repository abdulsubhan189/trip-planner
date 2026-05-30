# test_chat.py
from agents.chat_agent import process_chat

tests = [
    "hello how are you",
    "plan me a 5 day trip to Skardu under $800, I love adventure",
    "what is the best time to visit Hunza?",
    "show me my past trips",
]

history = []
for msg in tests:
    print(f"\nUser: {msg}")
    result = process_chat(msg, "user_001", "session_001", history)
    print(f"Type: {result['type']}")
    print(f"Response: {result['message'][:100]}")
    print("-" * 50)
    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": result["message"]})