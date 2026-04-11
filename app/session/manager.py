"""
Session Manager

Manages the lifecycle of a companion conversation session.

Responsibilities:
  - session creation with relationship-level loading (Phase 4)
  - session state updates (activate, end)
  - session-scoped memory clean-up on end

STUB NOTE:
  - Transport metadata: empty dict until DailyTransport is wired (Phase 3+).
  - Session duration tracking: not yet implemented.
"""
import uuid
from datetime import datetime
from typing import Optional

from app.config.settings import settings
from app.core.logging import log_session_end, log_session_start
from app.memory.engine import MemoryEngine
from app.models.session import SessionModel, SessionStatus
from app.state.session_store import InMemorySessionStore, SessionStore


class SessionManager:

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        memory_engine: Optional[MemoryEngine] = None,
    ) -> None:
        # STUB: defaults to in-memory store; swap with RedisSessionStore later
        self._store: SessionStore = session_store or InMemorySessionStore()
        self._engine: MemoryEngine = memory_engine or MemoryEngine()

    async def create_session(self, user_id: Optional[str] = None) -> SessionModel:
        """
        Create a new companion session.

        Loads the user's current relationship level from persistent memory
        if a user_id is provided. New or anonymous users start at level 1.
        """
        relationship_level = 1
        if user_id:
            rel_mem = await self._engine.get_relationship_memory(user_id)
            if rel_mem is not None:
                relationship_level = rel_mem.closeness_level

        session = SessionModel(
            session_id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            status=SessionStatus.INITIALIZING,
            user_id=user_id,
            adult_mode=settings.adult_mode_enabled,
            relationship_level=relationship_level,
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
        End a session and clean up session-scoped memory.

        Relationship and user memory are already written turn-by-turn by
        MemoryWriter, so no batch write-back is needed here.
        Session memory is cleared from the in-process store.
        """
        await self._store.update_status(session_id, SessionStatus.ENDED)
        await self._engine.delete_session_memory(session_id)
        log_session_end(session_id, duration_seconds=0.0)  # STUB: duration not tracked yet
