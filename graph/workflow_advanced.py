from langgraph.graph import StateGraph, END
from schemas import TripState
from agents.budget_allocation_agent import budget_allocation_agent
from agents import (
    orchestrator_llm, weather_agent, budget_agent, preference_agent,
    structured_planner, critic_structured, response_synthesizer_structured
)

MAX_ATTEMPTS = 3

def after_critic(state: TripState) -> str:
    if state.plan_valid:
        return "synthesizer"
    if state.attempt_count >= MAX_ATTEMPTS:
        return "fallback"   # go to fallback, not directly to synthesizer
    return "planner"

def safe_fallback(state: TripState) -> TripState:
    if not state.final_response:
        dest = state.destination or "your destination"
        state.final_response = (
            f"We couldn't generate a perfect plan for {dest} "
            f"within your constraints after {MAX_ATTEMPTS} attempts. "
            f"Try adjusting your budget or number of days."
        )
    return state

def build_advanced_graph():
    builder = StateGraph(TripState)
    builder.add_node("orchestrator", orchestrator_llm)
    builder.add_node("weather", weather_agent)
    builder.add_node("budget", budget_agent)
    builder.add_node("budget_allocation", budget_allocation_agent)
    builder.add_node("preference", preference_agent)
    builder.add_node("planner", structured_planner)
    builder.add_node("critic", critic_structured)
    builder.add_node("synthesizer", response_synthesizer_structured)
    builder.add_node("fallback", safe_fallback)   # new

    builder.set_entry_point("orchestrator")
    builder.add_edge("orchestrator", "weather")
    builder.add_edge("weather", "budget")
    builder.add_edge("budget", "budget_allocation")
    builder.add_edge("budget_allocation", "preference")
    builder.add_edge("preference", "planner")
    builder.add_edge("planner", "critic")
    builder.add_conditional_edges("critic", after_critic, {
        "planner": "planner",
        "synthesizer": "synthesizer",
        "fallback": "fallback"
    })
    builder.add_edge("fallback", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile()