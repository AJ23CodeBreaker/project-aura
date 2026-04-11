"""
Session Bootstrap API

Called by the Netlify frontend to start and end companion sessions.

RULES:
  - This endpoint must NEVER return provider secrets to the frontend.
  - Only safe session metadata is returned (session_id, status, adult_mode).
  - Transport details (WebRTC URL / token) will be added in Phase 3.

STUB NOTE:
  - Authentication / tester gating: not yet implemented (Phase 2).
  - Transport bootstrap data: not yet included (Phase 3).
  - adult_mode reflects server-side config only; the frontend cannot override it.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config.settings import settings

from app.session.manager import SessionManager

app = FastAPI(title="Project Aura — Session Bootstrap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_session_manager = SessionManager()


# --------------------------------------------------------------------------- #
# Request / response schemas
# --------------------------------------------------------------------------- #

class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = None
    # STUB: future fields — tester auth token, device info, preferred locale


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    adult_mode: bool
    transport_url: Optional[str] = None  # None until Daily.co transport is wired (Phase 3+)
    # STUB: transport_token added when Daily.co is wired
    # transport_token: Optional[str] = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@app.post("/session/create", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    """
    Create a new companion session.

    Called by the Netlify frontend when the user starts a conversation.
    Returns only safe session metadata — no provider credentials.
    """
    # STUB: add tester authentication and adult-access verification here (Phase 2)
    session = await _session_manager.create_session(user_id=request.user_id)
    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status.value,
        adult_mode=session.adult_mode,
        transport_url=None,  # STUB: populated when DailyTransport is wired (Phase 3+)
    )


@app.post("/session/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """End a session and trigger memory write-back (STUB)."""
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    await _session_manager.end_session(session_id)
    return {"status": "ended", "session_id": session_id}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "project-aura-bootstrap"}
