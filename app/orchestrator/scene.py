"""
Layer 3 — Session / scene controller

Compact runtime control block for the current turn.
Built fresh each turn from the live session state.

This layer tells the model:
- how close the relationship currently is (using the existing ClosenessLevel enum)
- whether adult content is enabled for this session
- current mood and escalation direction (stubs for Phase 4/5)
- current topic if tracked (stub for Phase 4)

RULES:
- Use ClosenessLevel from app.models.relationship — do not duplicate the enum.
- Keep render() output short; this block must stay prompt-efficient.
- adult_enabled alone does NOT unlock NSFW — relationship state must also support it.
- Escalation pace and mood are placeholders until Phase 4/5 populates them.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.models.relationship import ClosenessLevel
from app.models.session import SessionModel


class EscalationPace(str, Enum):
    HOLD = "hold"          # maintain current intimacy level
    INCREASE = "increase"  # Phase 5: allow gradual escalation if context supports it
    DECREASE = "decrease"  # Phase 5: pull back from current level


@dataclass
class SessionController:
    closeness: ClosenessLevel         # relationship depth — drives tone and gating
    adult_enabled: bool               # session-level adult mode flag
    current_mood: str                 # stub default "neutral"; Phase 4/5 derives dynamically
    escalation_pace: EscalationPace   # stub default HOLD; Phase 5 sets contextually
    current_topic: Optional[str]      # stub None; Phase 4 may track active topics

    @classmethod
    def from_session(cls, session: SessionModel) -> "SessionController":
        """
        Build a SessionController from the current SessionModel.
        Converts the raw relationship_level int to ClosenessLevel.
        Falls back to ClosenessLevel.NEW for any out-of-range value.
        """
        try:
            closeness = ClosenessLevel(session.relationship_level)
        except ValueError:
            closeness = ClosenessLevel.NEW

        return cls(
            closeness=closeness,
            adult_enabled=session.adult_mode,
            current_mood="neutral",               # STUB: Phase 4/5 derives from context
            escalation_pace=EscalationPace.HOLD,  # STUB: Phase 5 sets contextually
            current_topic=None,                   # STUB: Phase 4 may track topic
        )

    def render(self) -> str:
        """
        Format the scene controller into a compact system-prompt block.
        Kept intentionally short — this is a runtime control signal, not prose.
        """
        lines = [
            f"Relationship: {self.closeness.name} (level {self.closeness.value})",
            f"Adult mode: {'enabled' if self.adult_enabled else 'disabled'}",
            f"Mood: {self.current_mood}",
            f"Escalation pace: {self.escalation_pace.value}",
        ]
        if self.current_topic:
            lines.append(f"Current topic: {self.current_topic}")
        return "\n".join(lines)
