"""
Memory models for Project Aura.

Four selective memory layers (per PRD §9 and ARCHITECTURE.md §7):

  SessionMemory       short-term, current conversation  (Redis, TTL-based)
  UserSemanticMemory  stable user facts and preferences  (persistent)
  RelationshipMemory  closeness, milestones, emotional history  (persistent)
  EpisodicMemory      notable moments worth recalling later  (persistent)

RULE: Do not use raw full-transcript storage as the primary memory model.
Store selectively — preferences, milestones, emotionally meaningful moments,
unresolved threads, and promises. Not every turn.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SessionMemory:
    """
    Short-term memory for the current session.
    Stored in Redis with a TTL. Cleared when the session ends.
    """
    session_id: str
    # Recent turns kept as a short rolling window — not a full transcript.
    recent_turns: List[dict] = field(default_factory=list)
    current_topic: Optional[str] = None
    emotional_tone: Optional[str] = None  # e.g. "warm", "playful", "neutral"
    # STUB: populated from relationship engine each session start (Phase 4).
    relationship_snapshot: dict = field(default_factory=dict)


@dataclass
class UserSemanticMemory:
    """
    Stable facts about the user. Persists across all sessions.
    Keep concise and normalized — not an autobiography.
    """
    user_id: str
    preferences: Dict[str, str] = field(default_factory=dict)   # e.g. {"music": "jazz"}
    interests: List[str] = field(default_factory=list)
    personal_facts: Dict[str, str] = field(default_factory=dict)  # things user has shared
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RelationshipMemory:
    """
    Relational history and closeness state. The backbone of continuity.
    Persists across all sessions.
    """
    user_id: str
    closeness_level: int = 1              # mirrors RelationshipState.closeness
    affection_notes: List[str] = field(default_factory=list)
    intimacy_milestones: List[str] = field(default_factory=list)
    comfort_patterns: List[str] = field(default_factory=list)
    tensions: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EpisodicMemory:
    """
    A single notable moment worth recalling in future sessions.
    Only high-value moments should become episodic memories.
    """
    user_id: str
    moment_id: str
    summary: str                          # brief natural-language description
    emotional_weight: float = 0.5         # 0.0–1.0; higher = more worth recalling
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    recalled_count: int = 0
