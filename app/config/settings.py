"""
Configuration loader for Project Aura backend.

All secrets are read from environment variables.
Never hardcode credentials here. Never expose these values in frontend code.

Usage:
    from app.config.settings import settings
    if settings.adult_mode_enabled: ...
"""
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # --- STT provider ---
    # STUB: provider not yet selected
    stt_provider: str = field(default_factory=lambda: os.getenv("STT_PROVIDER", "stub"))
    stt_api_key: Optional[str] = field(default_factory=lambda: os.getenv("STT_API_KEY"))

    # --- LLM provider ---
    # STUB: provider not yet selected
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "stub"))
    llm_api_key: Optional[str] = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    llm_model: Optional[str] = field(default_factory=lambda: os.getenv("LLM_MODEL"))

    # --- TTS / voice provider ---
    # STUB: provider not yet selected
    tts_provider: str = field(default_factory=lambda: os.getenv("TTS_PROVIDER", "stub"))
    tts_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TTS_API_KEY"))
    tts_voice_id: Optional[str] = field(default_factory=lambda: os.getenv("TTS_VOICE_ID"))

    # --- Session state (Redis) ---
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))

    # --- Persistent memory store ---
    # STUB: backend not yet selected
    memory_store_url: Optional[str] = field(default_factory=lambda: os.getenv("MEMORY_STORE_URL"))
    memory_store_key: Optional[str] = field(default_factory=lambda: os.getenv("MEMORY_STORE_KEY"))

    # --- Session security ---
    session_secret_key: str = field(default_factory=lambda: os.getenv("SESSION_SECRET_KEY", "changeme-set-in-env"))

    # --- Adult mode ---
    # Must be explicitly enabled. False by default.
    # Only approved private testers should run sessions with adult_mode=True.
    adult_mode_enabled: bool = field(
        default_factory=lambda: os.getenv("ADULT_MODE_ENABLED", "false").lower() == "true"
    )

    # --- Modal ---
    modal_token_id: Optional[str] = field(default_factory=lambda: os.getenv("MODAL_TOKEN_ID"))
    modal_token_secret: Optional[str] = field(default_factory=lambda: os.getenv("MODAL_TOKEN_SECRET"))


# Singleton — import this everywhere instead of re-constructing
settings = Settings()
