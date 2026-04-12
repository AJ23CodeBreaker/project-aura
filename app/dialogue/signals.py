"""
Turn Signal Classifier

Classifies a completed user turn as positive, conflict, or neutral.
Used by DialoguePipelineService to decide whether to call
RelationshipEngine.apply_turn_signal().

Rules:
  - Pure heuristic — no LLM, no external calls.
  - Conflict takes priority over positive if both patterns match.
  - Most turns are neutral (both flags False) — no state change triggered.
  - Conflict patterns are deliberately conservative to avoid false positives.
    Under-detecting conflict is safer than triggering unwanted regression.
"""
import re
from dataclasses import dataclass


@dataclass
class TurnSignal:
    positive: bool = False
    conflict: bool = False


# Conflict: explicit rejection, frustration, or boundary-setting.
# Kept narrow — only clear, unambiguous pushback phrases.
_CONFLICT_RE = re.compile(
    r"\b("
    r"leave me alone"
    r"|go away"
    r"|stop it"
    r"|stop that"
    r"|please stop"
    r"|don't do that"
    r"|don't touch"
    r"|back off"
    r"|not okay with (this|that)"
    r"|that'?s not okay"
    r"|you'?re (annoying|being weird)"
    r"|i hate (this|you|when you)"
    r")\b",
    re.IGNORECASE,
)

# Positive: warmth, expressed enjoyment, gratitude, felt connection.
_POSITIVE_RE = re.compile(
    r"\b("
    r"thank(s| you)"
    r"|enjoy(ed)? (talking|chatting|this|our)"
    r"|like talking"
    r"|glad (you|to|that)"
    r"|happy (to|that|talking)"
    r"|love (this|talking|chatting)"
    r"|means a lot"
    r"|you'?re (great|amazing|wonderful|sweet|the best)"
    r")\b",
    re.IGNORECASE,
)


def classify_turn(user_text: str) -> TurnSignal:
    """
    Classify one user turn.

    Conflict is checked first — if the user both expressed warmth and
    set a boundary in the same message, the boundary wins.
    """
    if _CONFLICT_RE.search(user_text):
        return TurnSignal(conflict=True)
    if _POSITIVE_RE.search(user_text):
        return TurnSignal(positive=True)
    return TurnSignal()
