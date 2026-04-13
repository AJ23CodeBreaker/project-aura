"""
Tests for app.orchestrator.dialogue_runner — text-in / text-out turn execution.

All tests use StubDialogueAdapter explicitly so no ANTHROPIC_API_KEY is
required and responses are deterministic. Memory isolation is provided by the
shared engine fixture (tmp_data_dir monkeypatches _DATA_DIR to a temp dir).
"""
import pytest

from app.adapters.llm import StubDialogueAdapter
from app.models.relationship import ClosenessLevel
from app.models.session import SessionModel
from app.orchestrator.context import HISTORY_MAX_TURNS, build_dialogue_context
from app.orchestrator.dialogue_runner import (
    _session_histories,
    clear_session_history,
    run_text_turn,
)
from app.relationship.engine import RelationshipEngine


# ---------------------------------------------------------------------------
# Basic response
# ---------------------------------------------------------------------------

class TestBasicResponse:
    async def test_returns_non_empty_string(self, engine):
        session = SessionModel()
        result = await run_text_turn(session, "Hello", engine, StubDialogueAdapter())
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_returns_string_type(self, engine):
        session = SessionModel()
        result = await run_text_turn(session, "How are you?", engine, StubDialogueAdapter())
        assert isinstance(result, str)

    async def test_stub_response_content(self, engine):
        session = SessionModel()
        result = await run_text_turn(session, "hi", engine, StubDialogueAdapter())
        # StubDialogueAdapter always returns the same canned response
        assert "wired" in result.lower() or len(result) > 0


# ---------------------------------------------------------------------------
# History management
# ---------------------------------------------------------------------------

class TestHistory:
    async def test_history_accumulates_user_turns(self, engine):
        session = SessionModel()
        sid = session.session_id

        await run_text_turn(session, "first message", engine, StubDialogueAdapter())
        await run_text_turn(session, "second message", engine, StubDialogueAdapter())

        history = _session_histories[sid]
        user_texts = [h["text"] for h in history if h["role"] == "user"]
        assert "first message" in user_texts
        assert "second message" in user_texts

    async def test_history_contains_assistant_entries(self, engine):
        session = SessionModel()
        sid = session.session_id

        await run_text_turn(session, "hello", engine, StubDialogueAdapter())

        history = _session_histories[sid]
        roles = {h["role"] for h in history}
        assert "assistant" in roles

    async def test_history_entries_are_paired(self, engine):
        session = SessionModel()
        sid = session.session_id

        await run_text_turn(session, "hello", engine, StubDialogueAdapter())

        history = _session_histories[sid]
        # One user + one assistant entry per turn
        assert len(history) == 2

    async def test_history_capped_at_max_turns(self, engine):
        session = SessionModel()
        sid = session.session_id

        # Each call adds 2 entries; push well past the cap (HISTORY_MAX_TURNS = 6)
        for i in range(HISTORY_MAX_TURNS + 4):
            await run_text_turn(session, f"turn {i}", engine, StubDialogueAdapter())

        assert len(_session_histories[sid]) <= HISTORY_MAX_TURNS

    async def test_separate_sessions_have_separate_histories(self, engine):
        s1 = SessionModel()
        s2 = SessionModel()

        await run_text_turn(s1, "session one", engine, StubDialogueAdapter())
        await run_text_turn(s2, "session two", engine, StubDialogueAdapter())

        h1_texts = [h["text"] for h in _session_histories.get(s1.session_id, [])]
        h2_texts = [h["text"] for h in _session_histories.get(s2.session_id, [])]
        assert "session one" in h1_texts
        assert "session one" not in h2_texts


# ---------------------------------------------------------------------------
# clear_session_history
# ---------------------------------------------------------------------------

class TestClearHistory:
    async def test_clear_removes_history(self, engine):
        session = SessionModel()
        sid = session.session_id

        await run_text_turn(session, "hello", engine, StubDialogueAdapter())
        assert sid in _session_histories

        clear_session_history(sid)
        assert sid not in _session_histories

    async def test_clear_missing_session_is_safe(self):
        # Must not raise for a session that has no history
        clear_session_history("nonexistent-session-id-xyz")


# ---------------------------------------------------------------------------
# Memory writes
# ---------------------------------------------------------------------------

class TestMemoryWrites:
    async def test_personal_fact_stored_after_turn(self, engine):
        user_id = "dr-test-fact-user"
        session = SessionModel(user_id=user_id)

        await run_text_turn(
            session, "My name is Sam.", engine, StubDialogueAdapter()
        )

        ctx = await build_dialogue_context(session, engine)
        assert ctx.memory.user_facts.get("name") == "Sam"

    async def test_anonymous_session_skips_memory_write(self, engine):
        session = SessionModel(user_id=None)
        # Must complete without error; no disk writes for anonymous users
        result = await run_text_turn(
            session, "My name is Sam.", engine, StubDialogueAdapter()
        )
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Relationship signals
# ---------------------------------------------------------------------------

class TestRelationshipSignals:
    async def test_positive_signals_advance_relationship(self, engine):
        user_id = "dr-test-positive-user"
        session = SessionModel(user_id=user_id)
        rel = RelationshipEngine(engine)

        # NEW → FAMILIAR threshold is 8 positive turns
        for _ in range(8):
            await run_text_turn(
                session, "I enjoy talking with you", engine, StubDialogueAdapter()
            )

        state = await rel.load_state(user_id)
        assert state.closeness >= ClosenessLevel.FAMILIAR

    async def test_conflict_signal_regresses_relationship(self, engine):
        user_id = "dr-test-conflict-user"
        session = SessionModel(user_id=user_id)
        rel = RelationshipEngine(engine)

        # Advance to FAMILIAR first
        for _ in range(8):
            await run_text_turn(
                session, "I enjoy talking with you", engine, StubDialogueAdapter()
            )
        mid_state = await rel.load_state(user_id)

        await run_text_turn(session, "leave me alone", engine, StubDialogueAdapter())
        after_state = await rel.load_state(user_id)

        assert after_state.closeness.value < mid_state.closeness.value

    async def test_neutral_turn_does_not_change_relationship(self, engine):
        user_id = "dr-test-neutral-user"
        session = SessionModel(user_id=user_id)
        rel = RelationshipEngine(engine)

        before = await rel.load_state(user_id)
        await run_text_turn(session, "how was your day", engine, StubDialogueAdapter())
        after = await rel.load_state(user_id)

        assert after.closeness == before.closeness
