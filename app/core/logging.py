"""
Observability and structured logging for Project Aura.

Uses structlog for JSON-formatted output in production and human-readable
console output in development. Call configure_logging() once at startup
(done in main.py). If configure_logging() is never called, structlog falls
back to its default output — safe for tests.

Per ARCHITECTURE.md §13, tracks:
  - session start / end / duration
  - STT, LLM, TTS, and first-audio latency
  - memory retrieval and write events
  - relationship-state changes
  - connection failures and errors
"""
import time
from typing import Optional

import structlog

_log = structlog.get_logger("aura")


def configure_logging(dev_mode: bool = True) -> None:
    """
    Configure structlog. Call once at application startup.

    dev_mode=True  → human-readable ColourRenderer output (local development)
    dev_mode=False → JSON output (Modal / production)
    """
    renderer = (
        structlog.dev.ConsoleRenderer()
        if dev_mode
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


# ---------------------------------------------------------------------------
# Session events
# ---------------------------------------------------------------------------

def log_session_start(session_id: str, user_id: Optional[str] = None) -> None:
    _log.info("session_start", session_id=session_id, user_id=user_id)


def log_session_end(session_id: str, duration_seconds: float) -> None:
    _log.info("session_end", session_id=session_id, duration_s=round(duration_seconds, 3))


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

def log_latency(event: str, latency_ms: float, session_id: Optional[str] = None) -> None:
    """
    Log a latency measurement.

    event: one of "stt" | "llm" | "tts" | "first_audio" | "interruption"
    """
    _log.info(event, latency_ms=round(latency_ms, 1), session_id=session_id)


# ---------------------------------------------------------------------------
# Memory events
# ---------------------------------------------------------------------------

def log_memory_event(
    event: str,
    user_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Log a memory read or write event. event: "read" | "write" | "miss" """
    _log.info(event, user_id=user_id, detail=detail)


# ---------------------------------------------------------------------------
# Relationship events
# ---------------------------------------------------------------------------

def log_relationship_change(user_id: str, old_level: int, new_level: int) -> None:
    """Log a relationship state level transition."""
    _log.info(
        "relationship_change",
        user_id=user_id,
        old_level=old_level,
        new_level=new_level,
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def log_error(context: str, error: Exception, session_id: Optional[str] = None) -> None:
    _log.error("error", context=context, error=str(error), session_id=session_id)


# ---------------------------------------------------------------------------
# Latency context manager
# ---------------------------------------------------------------------------

class LatencyTimer:
    """Context manager for measuring and logging operation latency."""

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
