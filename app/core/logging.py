"""
Observability and structured logging — STUB

Provides latency and event logging hooks for the backend runtime.

Per ARCHITECTURE.md §13, the system must track:
  - session start / end / duration
  - STT, LLM, TTS, and first-audio latency
  - memory retrieval and write counts
  - relationship-state changes
  - connection failures

STUB NOTE: Logging currently uses plain print(). Replace with structlog
configured for JSON output before Modal deployment (Phase 3).
"""
import time
from typing import Optional


def log_session_start(session_id: str, user_id: Optional[str] = None) -> None:
    # STUB
    print(f"[LOG] session_start  session_id={session_id}  user_id={user_id}")


def log_session_end(session_id: str, duration_seconds: float) -> None:
    # STUB
    print(f"[LOG] session_end  session_id={session_id}  duration={duration_seconds:.2f}s")


def log_latency(event: str, latency_ms: float, session_id: Optional[str] = None) -> None:
    """
    Log a latency measurement.

    event: one of "stt" | "llm" | "tts" | "first_audio" | "interruption"
    """
    # STUB
    print(f"[LOG] latency  event={event}  latency_ms={latency_ms:.1f}  session_id={session_id}")


def log_memory_event(
    event: str,
    user_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Log a memory read or write event. event: "read" | "write" | "miss" """
    # STUB
    print(f"[LOG] memory  event={event}  user_id={user_id}  detail={detail}")


def log_relationship_change(user_id: str, old_level: int, new_level: int) -> None:
    """Log a relationship state level transition."""
    # STUB
    print(f"[LOG] relationship_change  user_id={user_id}  {old_level} -> {new_level}")


def log_error(context: str, error: Exception, session_id: Optional[str] = None) -> None:
    # STUB
    print(f"[LOG] error  context={context}  error={error}  session_id={session_id}")


class LatencyTimer:
    """Context manager for measuring and logging latency."""

    def __init__(self, event: str, session_id: Optional[str] = None):
        self.event = event
        self.session_id = session_id
        self._start: Optional[float] = None

    def __enter__(self) -> "LatencyTimer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_) -> None:
        if self._start is not None:
            elapsed_ms = (time.monotonic() - self._start) * 1000
            log_latency(self.event, elapsed_ms, self.session_id)
