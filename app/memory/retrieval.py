"""
Memory Retrieval

Assembles the memory context injected into the system prompt before each
generation turn.

The orchestrator calls build_context() once per turn. The result is passed
to DialogueContext.to_system_prompt() as Layer 2 of the system prompt.

Returns sensible defaults for new or anonymous users — never raises on
missing data.
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
    - session memory for current topic and emotional tone
    - user semantic facts (preferences, personal details)
    - relationship state summary (closeness, affection notes)
    - top episodic moments by emotional weight

    Anonymous sessions ("anonymous" or empty user_id) receive empty context.
    """
    if not user_id or user_id == "anonymous":
        return MemoryContext(relationship_summary="[no user — anonymous session]")

    # --- Session layer: recent topic and emotional tone ---
    session_mem = await engine.get_session_memory(session_id)
    recent_topics: List[str] = []
    emotional_context = "neutral"
    if session_mem:
        if session_mem.current_topic:
            recent_topics = [session_mem.current_topic]
        if session_mem.emotional_tone:
            emotional_context = session_mem.emotional_tone

    # --- User semantic facts: preferences + personal details ---
    user_mem = await engine.get_user_memory(user_id)
    user_facts: Dict[str, str] = {}
    if user_mem:
        user_facts = {**user_mem.preferences, **user_mem.personal_facts}

    # --- Relationship summary ---
    rel_mem = await engine.get_relationship_memory(user_id)
    if rel_mem:
        _level_names = {1: "New", 2: "Familiar", 3: "Close", 4: "Intimate"}
        level_name = _level_names.get(rel_mem.closeness_level, "New")
        relationship_summary = f"Closeness: {level_name}"
        # Surface the two most recent affection notes (skip internal counter entries)
        visible_notes = [
            n for n in rel_mem.affection_notes if not n.startswith("__")
        ]
        if visible_notes:
            relationship_summary += (
                "; noted: " + "; ".join(visible_notes[-2:])
            )
    else:
        relationship_summary = "First session with this user."

    # --- Episodic moments: top 3 by emotional weight ---
    episodes = await engine.get_recent_episodes(user_id, limit=3)
    notable_episodes = [ep.summary for ep in episodes]

    return MemoryContext(
        user_facts=user_facts,
        relationship_summary=relationship_summary,
        recent_topics=recent_topics,
        notable_episodes=notable_episodes,
        emotional_context=emotional_context,
    )
