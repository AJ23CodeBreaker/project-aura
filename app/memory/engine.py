"""
Memory Engine

Central interface for reading and writing selective companion memory.
All memory operations go through this single interface.

Memory write discipline (per CLAUDE.md §9):
  Store: preferences, milestones, emotionally important moments,
         recurring topics, promises, callbacks.
  Do NOT store: every turn, trivial filler, repetitive low-value details.

Storage:
  Session memory    → InMemorySessionMemoryStore (in-process, cleared on exit)
  Everything else   → JsonFileMemoryStore (prototype-grade JSON file persistence)
"""
from typing import List, Optional

from app.memory.store import InMemorySessionMemoryStore, JsonFileMemoryStore
from app.models.memory import (
    EpisodicMemory,
    RelationshipMemory,
    SessionMemory,
    UserSemanticMemory,
)


class MemoryEngine:

    def __init__(
        self,
        session_store: Optional[InMemorySessionMemoryStore] = None,
        persistent_store: Optional[JsonFileMemoryStore] = None,
    ) -> None:
        self._session = session_store or InMemorySessionMemoryStore()
        self._persistent = persistent_store or JsonFileMemoryStore()

    # ------------------------------------------------------------------ #
    # Session memory (in-memory, session-scoped)
    # ------------------------------------------------------------------ #

    async def get_session_memory(self, session_id: str) -> Optional[SessionMemory]:
        return self._session.get(session_id)

    async def write_session_memory(self, memory: SessionMemory) -> None:
        self._session.save(memory)

    async def delete_session_memory(self, session_id: str) -> None:
        self._session.delete(session_id)

    # ------------------------------------------------------------------ #
    # User semantic memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_user_memory(self, user_id: str) -> Optional[UserSemanticMemory]:
        return self._persistent.get_user_memory(user_id)

    async def update_user_memory(self, memory: UserSemanticMemory) -> None:
        self._persistent.save_user_memory(memory)

    # ------------------------------------------------------------------ #
    # Relationship memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_relationship_memory(self, user_id: str) -> Optional[RelationshipMemory]:
        return self._persistent.get_relationship_memory(user_id)

    async def update_relationship_memory(self, memory: RelationshipMemory) -> None:
        self._persistent.save_relationship_memory(memory)

    # ------------------------------------------------------------------ #
    # Episodic memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_recent_episodes(
        self, user_id: str, limit: int = 5
    ) -> List[EpisodicMemory]:
        return self._persistent.get_recent_episodes(user_id, limit)

    async def write_episode(self, episode: EpisodicMemory) -> None:
        # Only call for genuinely high-value moments
        self._persistent.save_episode(episode)
