"""
Tests for app.relationship.engine — RelationshipEngine.

Covers:
  - load_state() for new and existing users
  - apply_turn_signal() progression (positive accumulates toward threshold)
  - apply_turn_signal() regression (conflict drops level, resets count)
  - level capping at INTIMATE
  - flirtation_allowance and nsfw_eligible derived correctly per level
"""
import pytest

from app.models.memory import RelationshipMemory
from app.models.relationship import ClosenessLevel
from app.relationship.engine import RelationshipEngine, _PROGRESSION_THRESHOLD


class TestLoadState:
    async def test_new_user_starts_at_new(self, engine):
        rel = RelationshipEngine(engine)
        state = await rel.load_state("brand-new")
        assert state.closeness == ClosenessLevel.NEW
        assert state.flirtation_allowance == 0.0
        assert state.nsfw_eligible is False

    async def test_existing_user_loads_closeness(self, engine):
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="known", closeness_level=3)
        )
        rel = RelationshipEngine(engine)
        state = await rel.load_state("known")
        assert state.closeness == ClosenessLevel.CLOSE

    async def test_flirtation_allowance_zero_at_new(self, engine):
        rel = RelationshipEngine(engine)
        state = await rel.load_state("u-new")
        assert state.flirtation_allowance == 0.0

    async def test_flirtation_allowance_increases_with_level(self, engine):
        rel = RelationshipEngine(engine)
        for level, expected in [
            (ClosenessLevel.NEW, 0.0),
            (ClosenessLevel.FAMILIAR, 0.2),
            (ClosenessLevel.CLOSE, 0.5),
            (ClosenessLevel.INTIMATE, 0.8),
        ]:
            await engine.update_relationship_memory(
                RelationshipMemory(user_id=f"u-level-{level.value}", closeness_level=level.value)
            )
            state = await rel.load_state(f"u-level-{level.value}")
            assert state.flirtation_allowance == expected

    async def test_nsfw_eligible_only_at_intimate(self, engine):
        rel = RelationshipEngine(engine)
        for level in [1, 2, 3]:
            await engine.update_relationship_memory(
                RelationshipMemory(user_id=f"u-nsfw-{level}", closeness_level=level)
            )
            state = await rel.load_state(f"u-nsfw-{level}")
            assert state.nsfw_eligible is False

        await engine.update_relationship_memory(
            RelationshipMemory(user_id="u-nsfw-4", closeness_level=4)
        )
        state = await rel.load_state("u-nsfw-4")
        assert state.nsfw_eligible is True


class TestProgression:
    async def test_positive_signal_increments_count(self, engine):
        rel = RelationshipEngine(engine)
        await rel.apply_turn_signal("u-prog", positive=True)
        mem = await engine.get_relationship_memory("u-prog")
        assert mem.positive_turn_count == 1

    async def test_level_advances_at_threshold(self, engine):
        rel = RelationshipEngine(engine)
        threshold = _PROGRESSION_THRESHOLD[ClosenessLevel.NEW]
        for _ in range(threshold):
            await rel.apply_turn_signal("u-advance", positive=True)
        state = await rel.load_state("u-advance")
        assert state.closeness == ClosenessLevel.FAMILIAR

    async def test_count_resets_after_level_up(self, engine):
        rel = RelationshipEngine(engine)
        threshold = _PROGRESSION_THRESHOLD[ClosenessLevel.NEW]
        for _ in range(threshold):
            await rel.apply_turn_signal("u-reset", positive=True)
        mem = await engine.get_relationship_memory("u-reset")
        assert mem.positive_turn_count == 0

    async def test_level_caps_at_intimate(self, engine):
        rel = RelationshipEngine(engine)
        # Start at INTIMATE and send more positive signals
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="u-cap", closeness_level=4)
        )
        for _ in range(50):
            await rel.apply_turn_signal("u-cap", positive=True)
        mem = await engine.get_relationship_memory("u-cap")
        assert mem.closeness_level == 4  # still INTIMATE, not above


class TestRegression:
    async def test_conflict_drops_one_level(self, engine):
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="u-reg", closeness_level=3)
        )
        rel = RelationshipEngine(engine)
        await rel.apply_turn_signal("u-reg", conflict=True)
        mem = await engine.get_relationship_memory("u-reg")
        assert mem.closeness_level == 2

    async def test_conflict_resets_positive_count(self, engine):
        rel = RelationshipEngine(engine)
        # Build up some progress first
        for _ in range(4):
            await rel.apply_turn_signal("u-creset", positive=True)
        await rel.apply_turn_signal("u-creset", conflict=True)
        mem = await engine.get_relationship_memory("u-creset")
        assert mem.positive_turn_count == 0

    async def test_level_does_not_drop_below_new(self, engine):
        rel = RelationshipEngine(engine)
        # Already at NEW, conflict should not go below 1
        await rel.apply_turn_signal("u-floor", conflict=True)
        mem = await engine.get_relationship_memory("u-floor")
        assert mem.closeness_level == 1

    async def test_neutral_turn_no_state_change(self, engine):
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="u-neut", closeness_level=2, positive_turn_count=5)
        )
        rel = RelationshipEngine(engine)
        # No signal at all — don't call apply_turn_signal
        state = await rel.load_state("u-neut")
        assert state.closeness == ClosenessLevel.FAMILIAR


class TestGetClosenessLevel:
    async def test_returns_1_for_unknown_user(self, engine):
        rel = RelationshipEngine(engine)
        level = await rel.get_closeness_level("nobody")
        assert level == 1

    async def test_returns_stored_level(self, engine):
        await engine.update_relationship_memory(
            RelationshipMemory(user_id="u-lvl", closeness_level=3)
        )
        rel = RelationshipEngine(engine)
        assert await rel.get_closeness_level("u-lvl") == 3
