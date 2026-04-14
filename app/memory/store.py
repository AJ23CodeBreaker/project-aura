"""
Memory Store backends — prototype implementations.

Two stores, no external dependencies:

  JsonFileMemoryStore       — persistent, JSON file-based.
                              Stores: UserSemanticMemory, RelationshipMemory,
                              EpisodicMemory under data/memory/.
                              PROTOTYPE ONLY — swap for Supabase/Postgres in production.

  InMemorySessionMemoryStore — in-memory, process-scoped.
                               Stores: SessionMemory (cleared on process exit).
                               Suitable for single-process local use.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.config.settings import settings
from app.models.memory import (
    EpisodicMemory,
    RelationshipMemory,
    SessionMemory,
    UserSemanticMemory,
)

# Location of JSON files — driven by DATA_DIR env var (see settings).
# Local default: data/memory/ relative to project root.
# Modal deployment: /data/memory (Modal Volume mount).
_DATA_DIR = Path(settings.data_dir)


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _path(user_id: str, kind: str) -> Path:
    return _DATA_DIR / f"{user_id}_{kind}.json"


# --------------------------------------------------------------------------- #
# JSON file store — persistent memory
# --------------------------------------------------------------------------- #

class JsonFileMemoryStore:
    """
    Prototype-grade persistent memory store.

    One JSON file per user per memory type:
      data/memory/{user_id}_user.json
      data/memory/{user_id}_relationship.json
      data/memory/{user_id}_episodes.json

    Not suitable for production (no locking, no transactions).
    Replace with database-backed store for deployed use.
    """

    # ------------------------------------------------------------------ #
    # User semantic memory
    # ------------------------------------------------------------------ #

    def get_user_memory(self, user_id: str) -> Optional[UserSemanticMemory]:
        p = _path(user_id, "user")
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return UserSemanticMemory(
            user_id=data["user_id"],
            preferences=data.get("preferences", {}),
            interests=data.get("interests", []),
            personal_facts=data.get("personal_facts", {}),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def save_user_memory(self, memory: UserSemanticMemory) -> None:
        _ensure_dir()
        _path(memory.user_id, "user").write_text(
            json.dumps(
                {
                    "user_id": memory.user_id,
                    "preferences": memory.preferences,
                    "interests": memory.interests,
                    "personal_facts": memory.personal_facts,
                    "updated_at": memory.updated_at.isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    # Relationship memory
    # ------------------------------------------------------------------ #

    def get_relationship_memory(self, user_id: str) -> Optional[RelationshipMemory]:
        p = _path(user_id, "relationship")
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return RelationshipMemory(
            user_id=data["user_id"],
            closeness_level=data.get("closeness_level", 1),
            positive_turn_count=data.get("positive_turn_count", 0),
            affection_notes=data.get("affection_notes", []),
            intimacy_milestones=data.get("intimacy_milestones", []),
            comfort_patterns=data.get("comfort_patterns", []),
            tensions=data.get("tensions", []),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def save_relationship_memory(self, memory: RelationshipMemory) -> None:
        _ensure_dir()
        _path(memory.user_id, "relationship").write_text(
            json.dumps(
                {
                    "user_id": memory.user_id,
                    "closeness_level": memory.closeness_level,
                    "positive_turn_count": memory.positive_turn_count,
                    "affection_notes": memory.affection_notes,
                    "intimacy_milestones": memory.intimacy_milestones,
                    "comfort_patterns": memory.comfort_patterns,
                    "tensions": memory.tensions,
                    "updated_at": memory.updated_at.isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    # Episodic memory
    # ------------------------------------------------------------------ #

    def get_recent_episodes(self, user_id: str, limit: int = 5) -> List[EpisodicMemory]:
        p = _path(user_id, "episodes")
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        episodes = [
            EpisodicMemory(
                user_id=ep["user_id"],
                moment_id=ep["moment_id"],
                summary=ep["summary"],
                emotional_weight=ep.get("emotional_weight", 0.5),
                tags=ep.get("tags", []),
                created_at=datetime.fromisoformat(ep["created_at"]),
                recalled_count=ep.get("recalled_count", 0),
            )
            for ep in data.get("episodes", [])
        ]
        # Return top episodes by emotional weight
        episodes.sort(key=lambda e: e.emotional_weight, reverse=True)
        return episodes[:limit]

    def save_episode(self, episode: EpisodicMemory) -> None:
        _ensure_dir()
        p = _path(episode.user_id, "episodes")
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"episodes": []}
        # Replace existing entry with same moment_id if present
        data["episodes"] = [
            e for e in data["episodes"] if e.get("moment_id") != episode.moment_id
        ]
        data["episodes"].append(
            {
                "user_id": episode.user_id,
                "moment_id": episode.moment_id,
                "summary": episode.summary,
                "emotional_weight": episode.emotional_weight,
                "tags": episode.tags,
                "created_at": episode.created_at.isoformat(),
                "recalled_count": episode.recalled_count,
            }
        )
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# In-memory session store — short-term, process-scoped
# --------------------------------------------------------------------------- #

class InMemorySessionMemoryStore:
    """
    In-memory store for SessionMemory.

    Cleared when the process exits — suitable for local prototype use.
    Replace with Redis-backed store for multi-process or deployed use.
    """

    def __init__(self) -> None:
        self._store: Dict[str, SessionMemory] = {}

    def get(self, session_id: str) -> Optional[SessionMemory]:
        return self._store.get(session_id)

    def save(self, memory: SessionMemory) -> None:
        self._store[memory.session_id] = memory

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)
