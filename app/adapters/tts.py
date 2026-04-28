"""
TTS / Live Voice Adapter Interface

Defines the contract for the canonical live voice renderer.

ARCHITECTURE RULE: There must be exactly ONE canonical live voice path in v1.
Do not stack multiple live TTS layers. Offline voice experiments and asset
generation belong in app/voice/offline (Phase 4+), not here.

Phase 12A: FishAudioTTSAdapter is the live implementation, targeting the
           Fish Audio S2 Pro model served by modal_fish.py.
"""

import audioop
import io
import logging
import os
import wave
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


def _mask_id(value: str) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 10:
        return value[:2] + "***"
    return value[:6] + "..." + value[-6:]


class TTSAdapter(ABC):

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """
        Convert a streaming text input into streaming audio bytes.

        Yields:
            Raw PCM audio bytes suitable for streaming back to the client.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class StubTTSAdapter(TTSAdapter):
    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        async for _ in text_stream:
            pass
        yield b""

    async def close(self) -> None:
        pass


class FishAudioTTSAdapter(TTSAdapter):
    """
    Fish Audio S2 Pro TTS adapter.

    Sends buffered text to Fish, receives WAV audio, decodes it, converts it
    to 16 kHz mono linear16 PCM, and yields PCM bytes in small chunks.

    Important demo-safety rule:
      FISH_AUDIO_VOICE_ID must be configured. If it is missing, fail loudly
      instead of allowing Fish to fall back to a default/random voice.
    """

    _SPEED_MAP = {
        "playful": 1.1,
        "warm": 1.0,
        "soft": 0.9,
        "intimate": 0.85,
        "heavy": 0.9,
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        audio_format: str = "wav",
    ) -> None:
        try:
            import httpx as _httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is not installed. Run: pip install 'httpx>=0.25.0'"
            ) from exc

        self._base_url = (base_url or os.getenv("FISH_AUDIO_URL", "")).rstrip("/")
        if not self._base_url:
            raise ValueError(
                "FISH_AUDIO_URL is not set. Point it at the modal_fish.py service URL."
            )

        self._api_key = api_key or os.getenv("FISH_AUDIO_API_KEY", "")

        self._voice_id = (
            voice_id
            or os.getenv("FISH_AUDIO_VOICE_ID")
            or os.getenv("TTS_VOICE_ID")
            or ""
        ).strip()

        if not self._voice_id:
            raise ValueError(
                "FISH_AUDIO_VOICE_ID is not set. "
                "Set it to the Fish voice/model reference_id so Aura does not "
                "fall back to a default or random voice."
            )

        self._format = audio_format
        self._client = _httpx.AsyncClient(timeout=120.0)

        logger.info(
            "fish_tts_adapter_initialized base_url=%s voice_id=%s format=%s api_key_set=%s",
            self._base_url,
            _mask_id(self._voice_id),
            self._format,
            bool(self._api_key),
        )

    def _wav_to_pcm16_mono_16k(self, wav_bytes: bytes) -> bytes:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if channels == 2:
            frames = audioop.tomono(frames, sample_width, 0.5, 0.5)
            channels = 1
        elif channels > 2:
            frames = audioop.tomono(frames, sample_width, 0.5, 0.5)
            channels = 1

        if sample_width != 2:
            frames = audioop.lin2lin(frames, sample_width, 2)
            sample_width = 2

        if sample_rate != 16000:
            frames, _state = audioop.ratecv(
                frames,
                2,
                1,
                sample_rate,
                16000,
                None,
            )

        return frames

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        chunks: list[str] = []
        async for chunk in text_stream:
            if chunk:
                chunks.append(chunk)

        text = "".join(chunks).strip()
        if not text:
            logger.info("fish_tts_empty_text")
            return

        request_body: dict = {
            "text": text,
            "chunk_length": 200,
            "format": self._format,
            "normalize": True,
            "streaming": False,
            "reference_id": self._voice_id,
        }

        hint = (emotional_hint or "").lower()
        speed = self._SPEED_MAP.get(hint)
        if speed is not None and speed != 1.0:
            request_body["speed"] = speed

        headers: dict = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        logger.info(
            "fish_tts_request_start text_len=%s voice_id=%s format=%s speed=%s",
            len(text),
            _mask_id(self._voice_id),
            self._format,
            request_body.get("speed", 1.0),
        )

        try:
            response = await self._client.post(
                f"{self._base_url}/v1/tts",
                json=request_body,
                headers=headers,
            )
            response.raise_for_status()
            wav_bytes = response.content
        except Exception as exc:
            logger.error("fish_tts_request_failed error=%s", exc)
            return

        logger.info("fish_tts_response_bytes bytes=%s", len(wav_bytes))

        if not wav_bytes:
            logger.warning("fish_tts_empty_response")
            return

        try:
            pcm_bytes = self._wav_to_pcm16_mono_16k(wav_bytes)
        except Exception as exc:
            logger.error("fish_tts_decode_failed error=%s", exc)
            return

        logger.info("fish_tts_pcm_bytes bytes=%s", len(pcm_bytes))

        if not pcm_bytes:
            logger.warning("fish_tts_empty_pcm")
            return

        chunk_size = 640
        chunk_count = 0
        for i in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[i:i + chunk_size]
            if chunk:
                chunk_count += 1
                yield chunk

        logger.info("fish_tts_chunks_yielded count=%s", chunk_count)

    async def close(self) -> None:
        await self._client.aclose()