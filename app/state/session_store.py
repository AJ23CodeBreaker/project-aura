"""
Session State Store — STUB

Manages short-term runtime session state during a live conversation.

Target backend: Redis with TTL-based expiry (per ARCHITECTURE.md §7.1).
Current default: InMemorySessionStore for local development.

STUB NOTE: Replace InMemorySessionStore with RedisSessionStore once Redis
is confirmed and wired (Phase 2/3). The interface is designed so that swap
requires no changes to callers.
"""
from typing import Dict, Optional

from app.models.session import SessionModel, SessionStatus


class SessionStore:
    """Abstract interface for session state storage."""

    async def create(self, session: SessionModel) -> None:
        raise NotImplementedError

    async def get(self, session_id: str) -> Optional[SessionModel]:
        raise NotImplementedError

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        raise NotImplementedError

    async def delete(self, session_id: str) -> None:
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """
    STUB: in-memory session store for development and testing.

    NOT suitable for multi-process or deployed use.
    Replace with RedisSessionStore before any Modal deployment.
    """

    def __init__(self) -> None:
        self._store: Dict[str, SessionModel] = {}

    async def create(self, session: SessionModel) -> None:
        self._store[session.session_id] = session

    async def get(self, session_id: str) -> Optional[SessionModel]:
        return self._store.get(session_id)

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        if session_id in self._store:
            self._store[session_id].status = status

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


class RedisSessionStore(SessionStore):
    """
    STUB: Redis-backed session store.

    Not yet implemented. Requires:
    - REDIS_URL environment variable
    - redis[asyncio] package
    - session serialisation strategy (e.g. JSON or msgpack)

    Wire this in Phase 2/3 after Redis connectivity is confirmed.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        # TODO: initialise redis.asyncio.Redis client here
        raise NotImplementedError(
            "RedisSessionStore is not yet implemented. Use InMemorySessionStore."
        )

    async def create(self, session: SessionModel) -> None:
        raise NotImplementedError

    async def get(self, session_id: str) -> Optional[SessionModel]:
        raise NotImplementedError

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        raise NotImplementedError

    async def delete(self, session_id: str) -> None:
        raise NotImplementedError
