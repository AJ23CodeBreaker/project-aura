"""
STT (Speech-to-Text) Adapter Interface — STUB

Defines the contract any STT provider must satisfy.
The live provider is not yet selected or integrated.

Assumptions:
- Provider must support streaming/partial transcripts for low-latency behavior.
- Turn-end detection (VAD or silence) is signalled via `is_end_of_turn`.
- Interruption signals fire during active TTS playback.

Next step (Phase 3): implement a concrete adapter (e.g. DeepgramSTTAdapter)
that satisfies this interface and wire it into the Pipecat orchestrator.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class STTAdapter(ABC):

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[dict]:
        """
        Consume a raw audio byte stream and yield transcript events.

        Each yielded dict:
          "type":          "partial" | "final"
          "text":          str
          "is_end_of_turn": bool
          "confidence":    Optional[float]
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any open connections to the STT provider."""
        ...


class StubSTTAdapter(STTAdapter):
    """
    STUB — returns a fake transcript for local testing only.
    Replace with a real provider adapter before any voice testing.
    """

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[dict]:
        async for _ in audio_stream:
            pass
        yield {
            "type": "final",
            "text": "[stub transcript]",
            "is_end_of_turn": True,
            "confidence": None,
        }

    async def close(self) -> None:
        pass
