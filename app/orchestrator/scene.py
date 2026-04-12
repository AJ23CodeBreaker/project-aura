"""
Layer 3 — Session / scene controller

Compact runtime control block for the current turn.
Built fresh each turn from live session state, then updated with memory
context by build_dialogue_context() before rendering.

This layer tells the model HOW to behave — not just what the relationship
label is. Closeness-level instructions, mood direction, NSFW gating,
and escalation pace are all rendered as prose behavioral guidance.

RULES:
  - Use ClosenessLevel from app.models.relationship — do not duplicate.
  - Render output must be prompt-efficient: specific, not verbose.
  - adult_enabled alone does NOT unlock explicit content.
  - All three gates must pass: adult_enabled AND closeness >= INTIMATE
    AND nsfw_eligible. If any gate fails, explicit content is prohibited.
  - Even when the gate passes, the model is never instructed to open
    with explicit content unprompted.
  - Escalation pace INCREASE is set externally (build_dialogue_context);
    scene.py never sets it itself.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.models.relationship import ClosenessLevel
from app.models.session import SessionModel


class EscalationPace(str, Enum):
    HOLD = "hold"          # maintain current intimacy level
    INCREASE = "increase"  # allow gradual escalation if context supports it
    DECREASE = "decrease"  # pull back from current level


# ---------------------------------------------------------------------------
# Per-level behavioral instructions
# ---------------------------------------------------------------------------

_CLOSENESS_INSTRUCTION: dict = {
    ClosenessLevel.NEW: (
        "You're warm and genuinely curious, but keep a natural emotional distance — "
        "this relationship is just beginning. Do not flirt. "
        "Let the connection develop through honest conversation."
    ),
    ClosenessLevel.FAMILIAR: (
        "You're comfortable with this person. Light playfulness and gentle teasing "
        "are natural. Warmth can show more openly. "
        "Mild flirtation is fine if the moment genuinely invites it."
    ),
    ClosenessLevel.CLOSE: (
        "You're emotionally close and openly warm. Sustained affection and "
        "flirtation feel natural at this level. Let the closeness show in how you speak."
    ),
    ClosenessLevel.INTIMATE: (
        "You're deeply and romantically connected. Be openly affectionate and "
        "flirtatious. The emotional bond is real — let that come through."
    ),
}

_MOOD_INSTRUCTION: dict = {
    "warm": "Mood right now: warm — match it and lean into the good feeling.",
    "heavy": "Mood right now: heavy — be present and grounding, not playful.",
    "playful": "Mood right now: playful — be light, fun, and responsive to the energy.",
}

_NSFW_GATE_PASS = (
    "Adult content: enabled. Intimate and sexual content may arise naturally "
    "in context. Keep it emotionally present and grounded — "
    "do not open with explicit content unprompted."
)

_NSFW_GATE_FAIL = (
    "Adult content: not permitted in this session. Keep all intimacy tasteful "
    "and non-explicit, regardless of how the conversation develops."
)


# ---------------------------------------------------------------------------
# SessionController
# ---------------------------------------------------------------------------

@dataclass
class SessionController:
    closeness: ClosenessLevel         # relationship depth — drives tone and gating
    adult_enabled: bool               # session-level adult mode flag
    nsfw_eligible: bool               # computed by relationship engine at INTIMATE level
    current_mood: str                 # set from memory.emotional_context each turn
    escalation_pace: EscalationPace   # set by build_dialogue_context based on state
    current_topic: Optional[str]      # tracked topic if available (Phase 4+)

    @classmethod
    def from_session(cls, session: SessionModel) -> "SessionController":
        """
        Build a SessionController from the current SessionModel.
        current_mood and escalation_pace are set to safe defaults here;
        build_dialogue_context() updates them from live memory context.
        """
        try:
            closeness = ClosenessLevel(session.relationship_level)
        except ValueError:
            closeness = ClosenessLevel.NEW

        return cls(
            closeness=closeness,
            adult_enabled=session.adult_mode,
            # nsfw_eligible is True only at INTIMATE level — matches RelationshipEngine logic
            nsfw_eligible=(closeness >= ClosenessLevel.INTIMATE),
            current_mood="neutral",
            escalation_pace=EscalationPace.HOLD,
            current_topic=None,
        )

    def render(self) -> str:
        """
        Format the scene controller into behavioral guidance for the system prompt.

        Always includes: closeness instruction, NSFW gate result.
        Conditionally includes: mood override, escalation direction.
        """
        parts = []

        # Closeness-level behavioral instruction
        parts.append(_CLOSENESS_INSTRUCTION[self.closeness])

        # Mood direction — only emit when non-neutral
        mood_line = _MOOD_INSTRUCTION.get(self.current_mood)
        if mood_line:
            parts.append(mood_line)

        # Escalation pace — only emit non-HOLD states
        if self.escalation_pace == EscalationPace.INCREASE:
            parts.append(
                "Escalation: gradual intimacy can develop if the conversation "
                "naturally invites it."
            )
        elif self.escalation_pace == EscalationPace.DECREASE:
            parts.append(
                "Escalation: pull back from any elevated intimacy — "
                "the mood calls for more distance right now."
            )

        # NSFW gate — all three conditions must pass
        if (
            self.adult_enabled
            and self.closeness >= ClosenessLevel.INTIMATE
            and self.nsfw_eligible
        ):
            parts.append(_NSFW_GATE_PASS)
        else:
            parts.append(_NSFW_GATE_FAIL)

        return "\n".join(parts)
