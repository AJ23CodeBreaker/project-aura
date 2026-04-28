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
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


def _parse_origins(raw: str) -> List[str]:
    """Parse a comma-separated CORS origins string into a list."""
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass
class Settings:
    # --- STT provider ---
    stt_provider: str = field(default_factory=lambda: os.getenv("STT_PROVIDER", "stub"))
    stt_api_key: Optional[str] = field(default_factory=lambda: os.getenv("STT_API_KEY"))

    # --- LLM provider ---
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "stub"))
    llm_api_key: Optional[str] = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    llm_model: Optional[str] = field(default_factory=lambda: os.getenv("LLM_MODEL"))

    # --- TTS / voice provider ---
    tts_provider: str = field(default_factory=lambda: os.getenv("TTS_PROVIDER", "stub"))
    tts_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TTS_API_KEY"))
    tts_voice_id: Optional[str] = field(default_factory=lambda: os.getenv("TTS_VOICE_ID"))

    # --- Session state (Redis) ---
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))

    # --- Persistent memory store ---
    memory_store_url: Optional[str] = field(default_factory=lambda: os.getenv("MEMORY_STORE_URL"))
    memory_store_key: Optional[str] = field(default_factory=lambda: os.getenv("MEMORY_STORE_KEY"))

    # --- Session security ---
    session_secret_key: str = field(default_factory=lambda: os.getenv("SESSION_SECRET_KEY", "changeme-set-in-env"))

    # --- Adult mode ---
    adult_mode_enabled: bool = field(
        default_factory=lambda: os.getenv("ADULT_MODE_ENABLED", "false").lower() == "true"
    )

    # --- Data directory ---
    data_dir: str = field(
        default_factory=lambda: os.getenv(
            "DATA_DIR",
            str(Path(__file__).parent.parent.parent / "data" / "memory"),
        )
    )

    # --- Demo / investor access ---
    demo_token: Optional[str] = field(
        default_factory=lambda: os.getenv("DEMO_TOKEN")
    )
    demo_starting_closeness: int = field(
        default_factory=lambda: int(os.getenv("DEMO_STARTING_CLOSENESS", "4"))
    )
    llm_demo_model: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_DEMO_MODEL")
    )
    llm_demo_base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_DEMO_BASE_URL")
    )
    llm_demo_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_DEMO_API_KEY")
    )
    llm_demo_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_DEMO_MAX_TOKENS", "300"))
    )

    # --- LiveKit transport (new target path) ---
    # LIVEKIT_URL example:
    #   wss://your-project.livekit.cloud
    livekit_url: Optional[str] = field(
        default_factory=lambda: os.getenv("LIVEKIT_URL")
    )
    livekit_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("LIVEKIT_API_KEY")
    )
    livekit_api_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("LIVEKIT_API_SECRET")
    )

    # Optional room expiry / cleanup window for smoke/demo rooms.
    livekit_room_expiry_seconds: int = field(
        default_factory=lambda: int(os.getenv("LIVEKIT_ROOM_EXPIRY_SECONDS", "3600"))
    )

    # --- Daily WebRTC transport (legacy / being replaced) ---
    # Keep these for now so existing imports do not break while we migrate.
    daily_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DAILY_API_KEY"))
    daily_room_expiry_seconds: int = field(
        default_factory=lambda: int(os.getenv("DAILY_ROOM_EXPIRY_SECONDS", "3600"))
    )

    # --- vLLM — demo lane LLM served on Modal ---
    vllm_base_url: Optional[str] = field(default_factory=lambda: os.getenv("VLLM_BASE_URL"))
    vllm_api_key: str = field(
        default_factory=lambda: os.getenv("VLLM_API_KEY", "no-key-required")
    )
    vllm_model: str = field(
        default_factory=lambda: os.getenv(
            "VLLM_MODEL", "cognitivecomputations/Dolphin3.0-Mistral-24B"
        )
    )
    vllm_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("VLLM_MAX_TOKENS", "300"))
    )

    # --- Fish Audio TTS — self-hosted on Modal ---
    fish_audio_url: Optional[str] = field(
        default_factory=lambda: os.getenv("FISH_AUDIO_URL")
    )
    fish_audio_api_key: str = field(
        default_factory=lambda: os.getenv("FISH_AUDIO_API_KEY", "")
    )
    fish_audio_voice_id: Optional[str] = field(
        default_factory=lambda: os.getenv("FISH_AUDIO_VOICE_ID") or os.getenv("TTS_VOICE_ID")
    )

    # --- Modal ---
    modal_token_id: Optional[str] = field(default_factory=lambda: os.getenv("MODAL_TOKEN_ID"))
    modal_token_secret: Optional[str] = field(default_factory=lambda: os.getenv("MODAL_TOKEN_SECRET"))

    # --- CORS ---
    cors_origins: List[str] = field(
        default_factory=lambda: _parse_origins(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5500,http://127.0.0.1:5500,"
                "http://localhost:8080,http://127.0.0.1:8080",
            )
        )
    )


settings = Settings()