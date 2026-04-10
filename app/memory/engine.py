"""
Memory Engine — STUB

Central interface for reading and writing selective companion memory.

The orchestrator uses this single interface for all memory operations.
Do not scatter memory reads/writes across other modules.

STUB NOTE: All methods raise NotImplementedError. Storage backend is not yet
wired. Implement a concrete backend (e.g. SupabaseMemoryBackend) and inject
it here in Phase 4.

Memory write discipline (per CLAUDE.md §9):
  Store: preferences, milestones, emotionally important moments,
         recurring topics, promises, callbacks.
  Do NOT store: every turn, trivial filler, repetitive low-value details.
"""
from typing import List, Optional

from app.models.memory import (
    EpisodicMemory,
    RelationshipMemory,
    SessionMemory,
    UserSemanticMemory,
)


class MemoryEngine:

    # ------------------------------------------------------------------ #
    # Session memory (Redis, TTL-based)
    # ------------------------------------------------------------------ #

    async def get_session_memory(self, session_id: str) -> Optional[SessionMemory]:
        # STUB
        raise NotImplementedError("Session memory store not yet connected.")

    async def write_session_memory(self, memory: SessionMemory) -> None:
        # STUB
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # User semantic memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_user_memory(self, user_id: str) -> Optional[UserSemanticMemory]:
        # STUB
        raise NotImplementedError("Persistent memory store not yet connected.")

    async def update_user_memory(self, memory: UserSemanticMemory) -> None:
        # STUB
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Relationship memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_relationship_memory(self, user_id: str) -> Optional[RelationshipMemory]:
        # STUB
        raise NotImplementedError

    async def update_relationship_memory(self, memory: RelationshipMemory) -> None:
        # STUB
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Episodic memory (persistent)
    # ------------------------------------------------------------------ #

    async def get_recent_episodes(
        self, user_id: str, limit: int = 5
    ) -> List[EpisodicMemory]:
        # STUB
        raise NotImplementedError

    async def write_episode(self, episode: EpisodicMemory) -> None:
        # STUB — only call this for genuinely high-value moments
        raise NotImplementedError
