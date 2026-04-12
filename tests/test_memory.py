"""
Tests for memory layer — store, engine, retrieval, and writer.

Covers:
  - JsonFileMemoryStore round-trips for all persistent memory types
  - MemoryEngine delegation to stores
  - build_context() for new and returning users
  - MemoryWriter write discipline:
      session memory: always updated
      user memory: only on personal-fact signal
      relationship memory: only on warmth signal
      anonymous user: no persistent writes
"""
import pytest

from app.memory.engine import MemoryEngine
from app.memory.retrieval import MemoryContext, build_context
from app.memory.store import JsonFileMemoryStore
from app.memory.writer import MemoryWriter
from app.models.memory import (
    EpisodicMemory,
    RelationshipMemory,
    SessionMemory,
    UserSemanticMemory,
)


# ---------------------------------------------------------------------------
# JsonFileMemoryStore — round-trip persistence
# ---------------------------------------------------------------------------

class TestJsonFileMemoryStore:
    def test_user_memory_round_trip(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        mem = UserSemanticMemory(
            user_id="u1",
            preferences={"music": "jazz"},
            personal_facts={"name": "Alex"},
        )
        store.save_user_memory(mem)
        loaded = store.get_user_memory("u1")
        assert loaded is not None
        assert loaded.preferences == {"music": "jazz"}
        assert loaded.personal_facts == {"name": "Alex"}

    def test_relationship_memory_round_trip(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        mem = RelationshipMemory(
            user_id="u2",
            closeness_level=3,
            positive_turn_count=12,
            affection_notes=["they like jazz"],
        )
        store.save_relationship_memory(mem)
        loaded = store.get_relationship_memory("u2")
        assert loaded is not None
        assert loaded.closeness_level == 3
        assert loaded.positive_turn_count == 12
        assert loaded.affection_notes == ["they like jazz"]

    def test_episode_round_trip(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        ep = EpisodicMemory(
            user_id="u3",
            moment_id="ep-001",
            summary="First time they laughed",
            emotional_weight=0.9,
            tags=["humour"],
        )
        store.save_episode(ep)
        loaded = store.get_recent_episodes("u3", limit=5)
        assert len(loaded) == 1
        assert loaded[0].moment_id == "ep-001"
        assert loaded[0].emotional_weight == 0.9

    def test_episodes_sorted_by_emotional_weight(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        for i, weight in enumerate([0.3, 0.9, 0.6]):
            store.save_episode(
                EpisodicMemory(
                    user_id="u4",
                    moment_id=f"ep-{i}",
                    summary=f"moment {i}",
                    emotional_weight=weight,
                )
            )
        loaded = store.get_recent_episodes("u4", limit=5)
        assert loaded[0].emotional_weight == 0.9
        assert loaded[-1].emotional_weight == 0.3

    def test_returns_none_for_unknown_user(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        assert store.get_user_memory("unknown") is None
        assert store.get_relationship_memory("unknown") is None
        assert store.get_recent_episodes("unknown") == []

    def test_episode_deduplication_by_moment_id(self, tmp_data_dir):
        store = JsonFileMemoryStore()
        ep = EpisodicMemory(user_id="u5", moment_id="ep-dup", summary="first", emotional_weight=0.5)
        store.save_episode(ep)
        ep2 = EpisodicMemory(user_id="u5", moment_id="ep-dup", summary="updated", emotional_weight=0.8)
        store.save_episode(ep2)
        loaded = store.get_recent_episodes("u5")
        assert len(loaded) == 1
        assert loaded[0].summary == "updated"


# ---------------------------------------------------------------------------
# MemoryEngine — async delegation
# ---------------------------------------------------------------------------

class TestMemoryEngine:
    async def test_session_memory_round_trip(self, engine):
        mem = SessionMemory(session_id="sess-1", emotional_tone="warm")
        await engine.write_session_memory(mem)
        loaded = await engine.get_session_memory("sess-1")
        assert loaded is not None
        assert loaded.emotional_tone == "warm"

    async def test_session_memory_missing_returns_none(self, engine):
        result = await engine.get_session_memory("does-not-exist")
        assert result is None

    async def test_delete_session_memory(self, engine):
        mem = SessionMemory(session_id="sess-del")
        await engine.write_session_memory(mem)
        await engine.delete_session_memory("sess-del")
        assert await engine.get_session_memory("sess-del") is None

    async def test_user_memory_round_trip(self, engine):
        mem = UserSemanticMemory(user_id="u-eng", preferences={"tone": "playful"})
        await engine.update_user_memory(mem)
        loaded = await engine.get_user_memory("u-eng")
        assert loaded.preferences == {"tone": "playful"}

    async def test_relationship_memory_round_trip(self, engine):
        mem = RelationshipMemory(user_id="u-rel", closeness_level=2)
        await engine.update_relationship_memory(mem)
        loaded = await engine.get_relationship_memory("u-rel")
        assert loaded.closeness_level == 2

    async def test_episode_write_and_retrieve(self, engine):
        ep = EpisodicMemory(user_id="u-ep", moment_id="m1", summary="laughed together", emotional_weight=0.8)
        await engine.write_episode(ep)
        loaded = await engine.get_recent_episodes("u-ep", limit=5)
        assert len(loaded) == 1
        assert loaded[0].summary == "laughed together"


# ---------------------------------------------------------------------------
# build_context() — memory retrieval assembly
# ---------------------------------------------------------------------------

class TestBuildContext:
    async def test_new_user_returns_default_context(self, engine):
        ctx = await build_context(engine, "new-user", "sess-x")
        assert isinstance(ctx, MemoryContext)
        assert ctx.user_facts == {}
        assert "First session" in ctx.relationship_summary

    async def test_anonymous_user_returns_anonymous_context(self, engine):
        ctx = await build_context(engine, "anonymous", "sess-y")
        assert "anonymous" in ctx.relationship_summary.lower() or "no user" in ctx.relationship_summary.lower()

    async def test_empty_user_id_returns_anonymous_context(self, engine):
        ctx = await build_context(engine, "", "sess-z")
        assert "no user" in ctx.relationship_summary.lower()

    async def test_returning_user_surfaces_user_facts(self, engine):
        mem = UserSemanticMemory(user_id="returning", personal_facts={"name": "Alex"})
        await engine.update_user_memory(mem)
        ctx = await build_context(engine, "returning", "sess-ret")
        assert "Alex" in ctx.user_facts.values()

    async def test_returning_user_surfaces_relationship_summary(self, engine):
        mem = RelationshipMemory(user_id="known", closeness_level=2)
        await engine.update_relationship_memory(mem)
        ctx = await build_context(engine, "known", "sess-k")
        assert "Familiar" in ctx.relationship_summary

    async def test_session_memory_populates_emotional_context(self, engine):
        sess_mem = SessionMemory(session_id="sess-mood", emotional_tone="playful")
        await engine.write_session_memory(sess_mem)
        ctx = await build_context(engine, "u-mood", "sess-mood")
        assert ctx.emotional_context == "playful"


# ---------------------------------------------------------------------------
# MemoryWriter — write discipline
# ---------------------------------------------------------------------------

class TestMemoryWriter:
    async def test_session_memory_always_updated(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("sess-w1", "user-x", "hello there", "hi back")
        mem = await engine.get_session_memory("sess-w1")
        assert mem is not None
        assert len(mem.recent_turns) == 2

    async def test_session_memory_rolling_window(self, engine):
        writer = MemoryWriter(engine)
        for i in range(6):
            await writer.process_turn("sess-roll", "user-y", f"user turn {i}", f"assistant {i}")
        mem = await engine.get_session_memory("sess-roll")
        # SESSION_TURN_WINDOW=4 → max 8 entries (4 pairs)
        assert len(mem.recent_turns) <= 8

    async def test_personal_fact_writes_user_memory(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s1", "user-fact", "My name is Jordan", "Nice to meet you, Jordan.")
        loaded = await engine.get_user_memory("user-fact")
        assert loaded is not None
        assert loaded.personal_facts.get("name") == "Jordan"

    async def test_no_personal_fact_no_user_memory_write(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s2", "user-nofact", "how are you", "I'm well, thanks.")
        loaded = await engine.get_user_memory("user-nofact")
        assert loaded is None

    async def test_warmth_signal_writes_relationship_memory(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s3", "user-warm", "I really enjoy talking with you", "That means a lot.")
        loaded = await engine.get_relationship_memory("user-warm")
        assert loaded is not None
        assert len(loaded.affection_notes) > 0

    async def test_no_warmth_no_relationship_memory_write(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s4", "user-neutral", "what's the weather like", "Not sure.")
        loaded = await engine.get_relationship_memory("user-neutral")
        assert loaded is None

    async def test_anonymous_user_no_persistent_writes(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s5", None, "My name is Alex. I enjoy talking.", "Hello Alex.")
        assert await engine.get_user_memory("anonymous") is None

    async def test_emotional_tone_detected_in_session_memory(self, engine):
        writer = MemoryWriter(engine)
        await writer.process_turn("s6", None, "I'm so happy and excited today", "That's wonderful!")
        mem = await engine.get_session_memory("s6")
        assert mem.emotional_tone == "warm"
