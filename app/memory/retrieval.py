"""
Memory Retrieval — STUB

Assembles the memory context injected into the system prompt before each
generation turn.

The orchestrator calls build_context() once per turn. The result is
formatted into the system prompt alongside the persona instructions and
relationship-state data.

STUB NOTE: Returns empty placeholder context until the MemoryEngine backend
is connected in Phase 4.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from app.memory.engine import MemoryEngine


@dataclass
class MemoryContext:
    """Assembled memory context ready for system-prompt injection."""
    user_facts: Dict[str, str] = field(default_factory=dict)
    relationship_summary: str = ""
    recent_topics: List[str] = field(default_factory=list)
    notable_episodes: List[str] = field(default_factory=list)
    emotional_context: str = "neutral"


async def build_context(
    engine: MemoryEngine,
    user_id: str,
    session_id: str,
) -> MemoryContext:
    """
    Retrieve and assemble memory context for a single generation turn.

    Pulls:
    - user semantic facts (preferences, personal details)
    - relationship state summary (closeness, emotional history)
    - recent unresolved topics
    - top episodic moments by emotional weight

    STUB: returns empty context. Real retrieval implemented in Phase 4.
    """
    # STUB — replace with real retrieval calls once engine backend is wired
    return MemoryContext(
        user_facts={},
        relationship_summary="[no relationship memory yet]",
        recent_topics=[],
        notable_episodes=[],
        emotional_context="neutral",
    )
