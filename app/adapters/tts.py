"""
TTS / Live Voice Adapter Interface — STUB

Defines the contract for the canonical live voice renderer.
The live provider is not yet selected or integrated.

ARCHITECTURE RULE: There must be exactly ONE canonical live voice path in v1.
Do not stack multiple live TTS layers. Offline voice experiments and asset
generation belong in app/voice/offline (Phase 4+), not here.

Assumptions:
- Provider must support streaming audio output to minimize first-audio latency.
- Voice identity is actress-based; voice_id / model maps to the actress recording.
- Optional emotional style hints may be passed but are not required in v1.
- Post-processing (pitch shifting, timbre conversion) is disabled in the live path.

Next step (Phase 3): implement a concrete adapter (e.g. ElevenLabsTTSAdapter
or CartesiaTTSAdapter) that satisfies this interface and wire it into the renderer.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class TTSAdapter(ABC):

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """
        Convert a streaming text input into streaming audio bytes.

        Args:
            text_stream:     Streaming text chunks from the dialogue adapter.
            emotional_hint:  Optional tone hint ("warm", "playful", "soft").
                             May be ignored by providers that don't support it.

        Yields:
            Raw audio bytes suitable for streaming back to the client.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class StubTTSAdapter(TTSAdapter):
    """
    STUB — consumes text and yields empty audio bytes for local testing only.
    Replace with a real provider adapter before any voice testing.
    """

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        async for _ in text_stream:
            pass
        yield b""  # empty audio — stub only

    async def close(self) -> None:
        pass
