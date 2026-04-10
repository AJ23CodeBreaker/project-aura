"""
Relationship state model for Project Aura.

The relationship model governs emotional tone, flirtation allowance,
and NSFW eligibility (per ARCHITECTURE.md §8).

RULES:
- State is dynamic — it can progress AND regress based on context.
- This is NOT a simple one-way unlock ladder.
- NSFW requires BOTH adult_mode session config AND sufficient closeness.
- Abrupt jumps from Level 1 to Level 4 must not occur.
"""
from dataclasses import dataclass
from enum import IntEnum


class ClosenessLevel(IntEnum):
    NEW = 1        # warm but reserved, no flirtation, no sexual escalation
    FAMILIAR = 2   # playful, mild affection, light teasing possible
    CLOSE = 3      # emotionally warm, stronger attachment, sustained flirtation natural
    INTIMATE = 4   # romantically close; NSFW may be eligible if session config allows


@dataclass
class RelationshipState:
    user_id: str
    closeness: ClosenessLevel = ClosenessLevel.NEW
    emotional_warmth: float = 0.3        # 0.0–1.0
    flirtation_allowance: float = 0.0    # 0.0–1.0
    nsfw_eligible: bool = False          # set by relationship engine, not directly

    # STUB: these inputs will drive state updates in Phase 4.
    # Not yet computed dynamically.
    cumulative_positive_turns: int = 0
    recent_conflict: bool = False
    user_warmth_signal: float = 0.0

    def can_escalate_to_nsfw(self, adult_mode_enabled: bool) -> bool:
        """
        NSFW requires both an adult-enabled session AND sufficient closeness.
        Neither condition alone is sufficient.
        """
        return (
            adult_mode_enabled
            and self.nsfw_eligible
            and self.closeness >= ClosenessLevel.INTIMATE
        )
