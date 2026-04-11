"""
Memory Writer — selective turn-by-turn memory update.

Called by DialoguePipelineService after each completed dialogue turn.

Write discipline (per CLAUDE.md §9):
  - SessionMemory:          updated every turn (rolling window, topic, tone)
  - UserSemanticMemory:     only when a personal fact is detected
  - RelationshipMemory:     only when a warmth signal is detected
  - EpisodicMemory:         infrastructure ready; significance scoring is Phase 5
  - No LLM-based extraction in Phase 4 — rule-based heuristics only
  - No full transcript dumping — rolling window only
"""
import re
from datetime import datetime
from typing import Dict, Optional

from app.core.logging import log_memory_event
from app.memory.engine import MemoryEngine
from app.models.memory import RelationshipMemory, SessionMemory, UserSemanticMemory

# How many user+assistant turn pairs to keep in the rolling session window.
# Each pair = 2 entries; SESSION_TURN_WINDOW=4 keeps 8 entries total.
SESSION_TURN_WINDOW = 4


class MemoryWriter:
    """
    Selective memory writer. One instance per pipeline service.

    Injected into DialoguePipelineService at construction time.
    """

    def __init__(self, engine: MemoryEngine) -> None:
        self._engine = engine

    async def process_turn(
        self,
        session_id: str,
        user_id: Optional[str],
        user_text: str,
        assistant_text: str,
    ) -> None:
        """
        Process one completed dialogue turn.

        Always writes to session memory.
        Only writes persistent memory when a meaningful signal is detected.
        """
        # Session memory: always update
        await self._update_session_memory(session_id, user_text, assistant_text)

        # Persistent memory: only for real (non-anonymous) users
        if not user_id or user_id == "anonymous":
            return

        signals = _extract_signals(user_text)

        if signals["personal_facts"]:
            await self._update_user_memory(user_id, signals["personal_facts"])
            log_memory_event("write", user_id=user_id, detail="personal_fact")

        if signals["warmth_note"]:
            await self._update_relationship_warmth(user_id, signals["warmth_note"])
            log_memory_event("write", user_id=user_id, detail="warmth_signal")

    # ------------------------------------------------------------------ #

    async def _update_session_memory(
        self, session_id: str, user_text: str, assistant_text: str
    ) -> None:
        mem = await self._engine.get_session_memory(session_id)
        if mem is None:
            mem = SessionMemory(session_id=session_id)

        # Rolling turn window — not a transcript
        mem.recent_turns.append({"role": "user", "text": user_text})
        mem.recent_turns.append({"role": "assistant", "text": assistant_text})
        max_entries = SESSION_TURN_WINDOW * 2
        if len(mem.recent_turns) > max_entries:
            mem.recent_turns = mem.recent_turns[-max_entries:]

        mem.emotional_tone = _infer_tone(user_text)

        await self._engine.write_session_memory(mem)

    async def _update_user_memory(
        self, user_id: str, new_facts: Dict[str, str]
    ) -> None:
        mem = await self._engine.get_user_memory(user_id)
        if mem is None:
            mem = UserSemanticMemory(user_id=user_id)
        mem.personal_facts.update(new_facts)
        mem.updated_at = datetime.utcnow()
        await self._engine.update_user_memory(mem)

    async def _update_relationship_warmth(
        self, user_id: str, note: str
    ) -> None:
        mem = await self._engine.get_relationship_memory(user_id)
        if mem is None:
            mem = RelationshipMemory(user_id=user_id)
        # Keep up to 10 recent warmth notes; avoid exact duplicates
        if note not in mem.affection_notes:
            mem.affection_notes.append(note)
            mem.affection_notes = mem.affection_notes[-10:]
        mem.updated_at = datetime.utcnow()
        await self._engine.update_relationship_memory(mem)


# --------------------------------------------------------------------------- #
# Heuristic signal extractors — no LLM, pure regex
# --------------------------------------------------------------------------- #

_WARMTH_RE = re.compile(
    r"\b(like|enjoy|enjoying)\s+(talking|chatting|this|our)\b"
    r"|\b(thank|thanks|grateful)\b"
    r"|\b(happy|glad|lovely|nice)\s+(to|that|talking)\b"
    r"|\b(love|adore)\b",
    re.IGNORECASE,
)

_PERSONAL_PATTERNS = [
    (re.compile(r"\bmy name is (\w+)\b", re.IGNORECASE), "name"),
    (re.compile(r"\bi(?:'m| am) (\d{1,3})(?: years old)?\b", re.IGNORECASE), "age"),
    (re.compile(r"\bi (?:work as|am|'m) (?:a |an )?(\w+(?:\s\w+)?)\b", re.IGNORECASE), "role"),
    (re.compile(r"\bi (?:really )?like (\w[\w\s]{1,25})\b", re.IGNORECASE), "interest"),
]


def _extract_signals(user_text: str) -> dict:
    """
    Extract simple write signals from user text.
    Returns: {"personal_facts": dict, "warmth_note": str | None}
    """
    personal_facts: Dict[str, str] = {}
    for pattern, key in _PERSONAL_PATTERNS:
        m = pattern.search(user_text)
        if m:
            personal_facts[key] = m.group(1).strip()

    warmth_note: Optional[str] = None
    if _WARMTH_RE.search(user_text):
        warmth_note = user_text[:80].strip()

    return {"personal_facts": personal_facts, "warmth_note": warmth_note}


def _infer_tone(user_text: str) -> str:
    lower = user_text.lower()
    if any(w in lower for w in ["happy", "great", "love", "excited", "wonderful", "joy"]):
        return "warm"
    if any(w in lower for w in ["sad", "tired", "bad", "upset", "angry", "frustrated", "lonely"]):
        return "heavy"
    if any(w in lower for w in ["haha", "lol", "funny", "laugh", "silly", "joke"]):
        return "playful"
    return "neutral"
