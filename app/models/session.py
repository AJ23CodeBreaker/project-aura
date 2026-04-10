"""
Session data model for Project Aura.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ENDED = "ended"


@dataclass
class SessionModel:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: SessionStatus = SessionStatus.INITIALIZING
    user_id: Optional[str] = None
    adult_mode: bool = False

    # Snapshot from the relationship engine — populated on session load.
    # STUB: always 1 (New) until Phase 4 wires the relationship engine.
    relationship_level: int = 1  # 1=New, 2=Familiar, 3=Close, 4=Intimate

    # STUB: transport metadata returned to the frontend (WebRTC, Pipecat).
    # Populated in Phase 3 when real-time transport is wired.
    transport_metadata: dict = field(default_factory=dict)
