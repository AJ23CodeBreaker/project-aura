"""
Tests for app.session.manager — SessionManager lifecycle.

Covers:
  - create_session() defaults for anonymous users
  - create_session() loads stored relationship_level for known users
  - end_session() clears session memory
"""
import pytest

from app.memory.engine import MemoryEngine
from app.models.memory import RelationshipMemory, SessionMemory
from app.models.session import SessionStatus
from app.session.manager import SessionManager


def _make_manager(engine: MemoryEngine) -> SessionManager:
    """Create a SessionManager backed by the test engine."""
    return SessionManager(memory_engine=engine)


class TestCreateSession:
    async def test_anonymous_session_defaults_to_level_1(self, engine):
        manager = _make_manager(engine)
        session = await manager.create_session(user_id=None)
        assert session.relationship_level == 1
        assert session.user_id is None

    async def test_new_user_id_defaults_to_level_1(self, engine):
        manager = _make_manager(engine)
        session = await manager.create_session(user_id="brand-new")
        assert session.relationship_level == 1

    async def test_known_user_loads_stored_level(self, engine):
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="known-user", closeness_level=3)
        )
        manager = _make_manager(engine)
        session = await manager.create_session(user_id="known-user")
        assert session.relationship_level == 3

    async def test_session_has_initializing_status(self, engine):
        manager = _make_manager(engine)
        session = await manager.create_session()
        assert session.status == SessionStatus.INITIALIZING

    async def test_session_id_is_unique(self, engine):
        manager = _make_manager(engine)
        s1 = await manager.create_session()
        s2 = await manager.create_session()
        assert s1.session_id != s2.session_id


class TestGetSession:
    async def test_get_existing_session(self, engine):
        manager = _make_manager(engine)
        created = await manager.create_session()
        retrieved = await manager.get_session(created.session_id)
        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    async def test_get_nonexistent_session_returns_none(self, engine):
        manager = _make_manager(engine)
        result = await manager.get_session("does-not-exist")
        assert result is None


class TestEndSession:
    async def test_end_session_sets_ended_status(self, engine):
        manager = _make_manager(engine)
        session = await manager.create_session()
        await manager.end_session(session.session_id)
        retrieved = await manager.get_session(session.session_id)
        assert retrieved.status == SessionStatus.ENDED

    async def test_end_session_clears_session_memory(self, engine):
        manager = _make_manager(engine)
        session = await manager.create_session()
        # Write some session memory
        await engine.write_session_memory(
            SessionMemory(session_id=session.session_id, emotional_tone="warm")
        )
        await manager.end_session(session.session_id)
        mem = await engine.get_session_memory(session.session_id)
        assert mem is None
