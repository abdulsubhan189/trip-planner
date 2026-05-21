# api.py
import os
import uuid
import time
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from memory.trip_history import save_trip, get_trip_history, get_visited_activities
from memory.profile_memory import update_profile
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from observability.logger import get_logger
from escalation.detector import should_escalate
from escalation.queue import add_to_queue, get_queue, resolve_ticket, get_ticket

# Booking imports (added)
from booking.booking_agent import (
    create_approval_request, approve_booking,
    reject_booking, get_approval
)

# Load environment and check API key
load_dotenv()
if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY not found. Set it in your .env file.")

# Import graph, state, and session memory
from graph import build_advanced_graph
from schemas import TripState
from memory.session_memory import create_session, load_session, save_turn, get_last_destination

# Build graph once
graph = build_advanced_graph()

# In-memory job store (for async endpoints)
jobs: Dict[str, Dict[str, Any]] = {}
executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# Metrics (in-memory)
# ---------------------------------------------------------------------------
metrics = {
    "total_requests": 0,
    "successful": 0,
    "failed": 0,
    "total_duration_seconds": 0.0,
    "total_plan_score": 0.0,
    "scored_plans": 0,
}

# ---------------------------------------------------------------------------
# Pydantic request model (with session fields)
# ---------------------------------------------------------------------------
class PlanRequest(BaseModel):
    query: str = Field(..., description="Natural language trip request")
    destination: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[float] = None
    preferences: Optional[List[str]] = None
    user_id: str = "anonymous"
    session_id: Optional[str] = None

# ---------------------------------------------------------------------------
# Helper: planning function (used by both sync and async)
# ---------------------------------------------------------------------------
def _run_planning_sync(request: PlanRequest) -> Dict[str, Any]:
    trace_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    api_logger = get_logger("api")
    api_logger.info("Planning started", extra={"agent": "api", "trace_id": trace_id})

    try:
        # --- Session handling ---
        session_id = request.session_id
        if not session_id or not load_session(session_id):
            session_id = create_session(request.user_id)

        query = request.query
        if not request.destination:
            last_dest = get_last_destination(session_id)
            if last_dest and "day" in query.lower():
                query = f"{last_dest} {query}"

        # Build initial state
        state = TripState(user_query=query, user_id=request.user_id, session_id=session_id)
        if request.destination is not None:
            state.destination = request.destination
        if request.days is not None:
            state.days = request.days
        if request.budget is not None:
            state.budget = request.budget
        if request.preferences is not None:
            state.preferences = request.preferences

        # Invoke graph
        final_state = graph.invoke(state)

        # Extract structured plan
        structured_plan = final_state.get("structured_plan")
        if structured_plan is None:
            result = {"itinerary": final_state.get("itinerary", "No itinerary could be generated.")}
            save_turn(session_id, request.query, result)
            result["session_id"] = session_id
            # Update metrics (failure)
            metrics["total_requests"] += 1
            metrics["failed"] += 1
            api_logger.info("Planning completed with fallback (no structured plan)",
                            extra={"agent": "api", "trace_id": trace_id})
            # Escalation check (even for fallback)
            final_state_obj = TripState(**{k: v for k, v in final_state.items() if k in TripState.model_fields})
            escalate, reason = should_escalate(result, final_state_obj)
            if escalate:
                ticket_id = add_to_queue(request.user_id, request.query, result, reason)
                result["escalated"] = True
                result["ticket_id"] = ticket_id
                result["escalation_reason"] = reason
            else:
                result["escalated"] = False
            return result

        # Build JSON response
        response = {
            "destination": structured_plan.destination,
            "days": structured_plan.days,
            "budget": structured_plan.budget,
            "budget_status": structured_plan.budget_status,
            "weather": structured_plan.weather_info,
            "daily_plans": []
        }
        for day in structured_plan.daily_plans:
            day_data = {
                "day_number": day.day_number,
                "title": day.title,
                "total_cost": day.total_cost,
                "activities": []
            }
            for act in day.activities:
                try:
                    parts = act.notes.split("Duration:")
                    if len(parts) > 1:
                        dur_part = parts[1].split("|")[0].strip().replace("h", "")
                        duration = float(dur_part)
                    else:
                        duration = 1.0
                except (ValueError, IndexError, AttributeError):
                    duration = 1.0
                act_data = {
                    "name": act.name,
                    "activity_type": act.activity_type.value,
                    "estimated_cost": act.estimated_cost,
                    "duration_hours": duration,
                    "notes": act.notes
                }
                day_data["activities"].append(act_data)
            response["daily_plans"].append(day_data)

        response["overall_notes"] = structured_plan.overall_notes
        for note in structured_plan.overall_notes:
            if "Plan score:" in note:
                try:
                    score_str = note.split("Plan score:")[1].split("/")[0].strip()
                    response["plan_score"] = float(score_str)
                except ValueError:
                    pass
                break

        # Save to session, profile, trip history
        save_turn(session_id, request.query, response)
        update_profile(request.user_id, response, request.preferences or [])
        save_trip(request.user_id, response)

        response["session_id"] = session_id

        # Update metrics (success)
        duration = time.time() - start_time
        metrics["total_requests"] += 1
        metrics["successful"] += 1
        metrics["total_duration_seconds"] += duration
        if "plan_score" in response:
            metrics["total_plan_score"] += response["plan_score"]
            metrics["scored_plans"] += 1

        api_logger.info(f"Planning completed in {duration:.2f}s, score={response.get('plan_score', 'N/A')}",
                        extra={"agent": "api", "trace_id": trace_id})

        # --- Escalation check ---
        final_state_obj = TripState(**{k: v for k, v in final_state.items() if k in TripState.model_fields})
        escalate, reason = should_escalate(response, final_state_obj)
        if escalate:
            ticket_id = add_to_queue(request.user_id, request.query, response, reason)
            response["escalated"] = True
            response["ticket_id"] = ticket_id
            response["escalation_reason"] = reason
            api_logger.warning(f"Plan escalated: {reason}", extra={"agent": "api", "trace_id": trace_id})
        else:
            response["escalated"] = False

        response["trace_id"] = trace_id
        return response

    except Exception as e:
        # Update metrics on exception
        metrics["total_requests"] += 1
        metrics["failed"] += 1
        duration = time.time() - start_time
        api_logger.error(f"Planning failed after {duration:.2f}s: {e}",
                         extra={"agent": "api", "trace_id": trace_id}, exc_info=True)
        raise

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Trip Planner Agentic API", version="1.0.0")

# --- CORS Middleware (UPDATED: allow all origins) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def status():
    return {"status": "ok", "message": "Trip planner agent is ready"}

# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------
@app.get("/user/{user_id}/history")
async def get_user_history(user_id: str, limit: int = 10):
    history = get_trip_history(user_id, limit=limit)
    return {"user_id": user_id, "trips": history}

# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics")
async def get_metrics():
    avg_duration = (
        metrics["total_duration_seconds"] / metrics["successful"]
        if metrics["successful"] > 0 else 0
    )
    avg_score = (
        metrics["total_plan_score"] / metrics["scored_plans"]
        if metrics["scored_plans"] > 0 else 0
    )
    return {
        "total_requests": metrics["total_requests"],
        "successful": metrics["successful"],
        "failed": metrics["failed"],
        "success_rate": (
            metrics["successful"] / metrics["total_requests"]
            if metrics["total_requests"] > 0 else 0
        ),
        "avg_duration_seconds": round(avg_duration, 2),
        "avg_plan_score": round(avg_score, 2),
    }

# ---------------------------------------------------------------------------
# Escalation endpoints
# ---------------------------------------------------------------------------
@app.get("/escalation/queue")
async def escalation_queue():
    """Return all pending escalation tickets."""
    return {"tickets": get_queue()}

@app.get("/escalation/ticket/{ticket_id}")
async def get_escalation_ticket(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@app.post("/escalation/resolve/{ticket_id}")
async def resolve_escalation(ticket_id: str, corrected_plan: Dict[str, Any]):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    resolve_ticket(ticket_id, corrected_plan)
    return {"status": "resolved", "ticket_id": ticket_id}

# ---------------------------------------------------------------------------
# Booking endpoints (added)
# ---------------------------------------------------------------------------
@app.post("/booking/request")
async def request_booking(user_id: str, plan_result: Dict[str, Any]):
    approval = create_approval_request(user_id, plan_result)
    return approval

@app.post("/booking/confirm/{approval_id}")
async def confirm_booking(approval_id: str):
    result = approve_booking(approval_id)
    if not result.get("success") and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/booking/cancel/{approval_id}")
async def cancel_booking(approval_id: str):
    return reject_booking(approval_id)

@app.get("/booking/{approval_id}")
async def booking_status(approval_id: str):
    approval = get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Booking request not found")
    return approval

# ---------------------------------------------------------------------------
# Async endpoints
# ---------------------------------------------------------------------------
@app.post("/plan/async")
async def plan_trip_async(request: PlanRequest):
    job_id = str(uuid.uuid4())

    session_id = request.session_id
    if not session_id or not load_session(session_id):
        session_id = create_session(request.user_id)
    request_with_session = request.model_copy(update={"session_id": session_id})

    jobs[job_id] = {"status": "queued", "result": None, "error": None}

    def background_task():
        try:
            jobs[job_id]["status"] = "processing"
            result = _run_planning_sync(request_with_session)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

    executor.submit(background_task)

    return {"job_id": job_id, "status": "queued", "session_id": session_id}

@app.get("/plan/status/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "done":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job["error"]
    return response

# ---------------------------------------------------------------------------
# Sync endpoint (kept for quick testing)
# ---------------------------------------------------------------------------
@app.post("/plan")
async def plan_trip_sync(request: PlanRequest):
    try:
        result = _run_planning_sync(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)