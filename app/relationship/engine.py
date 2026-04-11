"""
Relationship Engine

Loads, computes, and persists RelationshipState based on turn-by-turn signals.

Key rules (per CLAUDE.md §10 and TASKS.md §7):
  - State can progress AND regress — not a one-way unlock ladder.
  - Progression requires sustained positive signals (turn-count threshold).
  - Regression occurs on explicit conflict signal.
  - NSFW eligibility is computed here but actual NSFW behavior is Phase 5.
  - adult_mode session config alone is never sufficient for escalation.
"""
from datetime import datetime
from typing import Optional

from app.core.logging import log_relationship_change
from app.memory.engine import MemoryEngine
from app.models.memory import RelationshipMemory
from app.models.relationship import ClosenessLevel, RelationshipState

# Positive turn count required to advance one closeness level.
# These are cumulative counts that reset on each level-up.
_PROGRESSION_THRESHOLD: dict = {
    ClosenessLevel.NEW: 8,         # 8 warm turns → FAMILIAR
    ClosenessLevel.FAMILIAR: 20,   # 20 more warm turns → CLOSE
    ClosenessLevel.CLOSE: 40,      # 40 more warm turns → INTIMATE
}

# How much flirtation is allowed at each closeness level.
# Actual flirtation behavior is gated in Phase 5; this is the allowance value only.
_FLIRTATION_BY_LEVEL: dict = {
    ClosenessLevel.NEW: 0.0,
    ClosenessLevel.FAMILIAR: 0.2,
    ClosenessLevel.CLOSE: 0.5,
    ClosenessLevel.INTIMATE: 0.8,
}


class RelationshipEngine:
    """
    Manages relationship state for a single user.

    Usage:
      state = await engine.load_state(user_id)
      state = await engine.apply_turn_signal(user_id, positive=True)
    """

    def __init__(self, memory_engine: MemoryEngine) -> None:
        self._engine = memory_engine

    async def load_state(self, user_id: str) -> RelationshipState:
        """
        Load current RelationshipState from persistent memory.
        New users start at ClosenessLevel.NEW with safe defaults.
        """
        rel_mem = await self._engine.get_relationship_memory(user_id)
        if rel_mem is None:
            return RelationshipState(user_id=user_id)

        try:
            closeness = ClosenessLevel(rel_mem.closeness_level)
        except ValueError:
            closeness = ClosenessLevel.NEW

        return RelationshipState(
            user_id=user_id,
            closeness=closeness,
            emotional_warmth=min(0.3 + (closeness.value - 1) * 0.2, 1.0),
            flirtation_allowance=_FLIRTATION_BY_LEVEL[closeness],
            # NSFW eligibility computed here — actual behavior gated in Phase 5
            nsfw_eligible=(closeness >= ClosenessLevel.INTIMATE),
        )

    async def apply_turn_signal(
        self,
        user_id: str,
        positive: bool = False,
        conflict: bool = False,
    ) -> RelationshipState:
        """
        Update relationship state based on a completed turn signal.

        positive=True  — warm, engaged, friendly turn
        conflict=True  — tension or rejection detected

        Saves updated RelationshipMemory and returns the new RelationshipState.
        A turn can be neither positive nor conflict (neutral) — no change recorded.
        """
        rel_mem = await self._engine.get_relationship_memory(user_id)
        if rel_mem is None:
            rel_mem = RelationshipMemory(user_id=user_id, closeness_level=1)

        old_level = rel_mem.closeness_level

        if conflict:
            # Regression: drop one level
            new_level = max(1, rel_mem.closeness_level - 1)
            if new_level != old_level:
                rel_mem.closeness_level = new_level
                rel_mem.positive_turn_count = 0  # reset progress on regression
                log_relationship_change(user_id, old_level, new_level)

        elif positive:
            rel_mem.positive_turn_count += 1
            current = ClosenessLevel(min(rel_mem.closeness_level, 4))
            threshold = _PROGRESSION_THRESHOLD.get(current)

            if (
                threshold is not None
                and rel_mem.positive_turn_count >= threshold
                and rel_mem.closeness_level < int(ClosenessLevel.INTIMATE)
            ):
                rel_mem.closeness_level = min(4, rel_mem.closeness_level + 1)
                rel_mem.positive_turn_count = 0  # reset after level-up
                log_relationship_change(user_id, old_level, rel_mem.closeness_level)

        rel_mem.updated_at = datetime.utcnow()
        await self._engine.update_relationship_memory(rel_mem)
        return await self.load_state(user_id)

    async def get_closeness_level(self, user_id: str) -> int:
        """
        Return the current closeness level integer for a user.
        Returns 1 (NEW) for unknown users.
        """
        rel_mem = await self._engine.get_relationship_memory(user_id)
        if rel_mem is None:
            return 1
        return rel_mem.closeness_level
