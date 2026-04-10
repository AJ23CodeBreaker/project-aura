"""
Session Manager — STUB

Manages the lifecycle of a companion conversation session.

Responsibilities:
  - session creation and runtime state initialisation
  - loading relationship state from persistent store (STUB)
  - triggering memory write-back on session end (STUB)
  - session teardown

STUB NOTE:
  - Relationship state loading (Phase 4): hardcoded to Level 1 (New).
  - Memory write-back (Phase 4): logged but not yet executed.
  - Transport metadata (Phase 3): empty dict until Pipecat/WebRTC is wired.
"""
import uuid
from datetime import datetime
from typing import Optional

from app.config.settings import settings
from app.core.logging import log_session_end, log_session_start
from app.models.session import SessionModel, SessionStatus
from app.state.session_store import InMemorySessionStore, SessionStore


class SessionManager:

    def __init__(self, session_store: Optional[SessionStore] = None) -> None:
        # STUB: defaults to in-memory store; swap with RedisSessionStore (Phase 2/3)
        self._store: SessionStore = session_store or InMemorySessionStore()

    async def create_session(self, user_id: Optional[str] = None) -> SessionModel:
        """
        Create a new companion session and initialise runtime state.

        STUB: relationship_level is hardcoded to 1 (New) until the
        relationship engine is wired in Phase 4.
        """
        session = SessionModel(
            session_id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            status=SessionStatus.INITIALIZING,
            user_id=user_id,
            adult_mode=settings.adult_mode_enabled,
            relationship_level=1,  # STUB: load from RelationshipState in Phase 4
        )
        await self._store.create(session)
        log_session_start(session.session_id, user_id)
        return session

    async def activate_session(self, session_id: str) -> None:
        """Mark a session as active once the real-time transport is connected."""
        await self._store.update_status(session_id, SessionStatus.ACTIVE)

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        return await self._store.get(session_id)

    async def end_session(self, session_id: str) -> None:
        """
        End a session and trigger post-session memory write-back.

        STUB: memory summarisation and write-back are not yet implemented.
        Logged as a reminder for Phase 4 implementation.
        """
        await self._store.update_status(session_id, SessionStatus.ENDED)
        # TODO Phase 4: generate session summary and write selective memories here
        print(f"[STUB] Session {session_id} ended. Memory write-back not yet implemented.")
        log_session_end(session_id, duration_seconds=0.0)  # STUB: duration not tracked yet
