"""
STT (Speech-to-Text) Adapter Interface

Defines the contract any STT provider must satisfy.

Env var convention:
  STT_API_KEY is the canonical name for the Deepgram API key.
  DEEPGRAM_API_KEY is accepted as a backward-compat alias (checked second).
  Set exactly one of these in .env / Modal Secret aura-secrets.
"""

import inspect
import io
import logging
import os
import wave
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class STTAdapter(ABC):

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[dict]:
        """
        Consume a raw audio byte stream and yield transcript events.

        Each yielded dict:
          "type":           "partial" | "final"
          "text":           str
          "is_end_of_turn": bool
          "confidence":     Optional[float]
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any open connections to the STT provider."""
        ...


class StubSTTAdapter(STTAdapter):
    """
    STUB — returns a fake transcript for local testing only.
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


class DeepgramSTTAdapter(STTAdapter):
    """
    Deepgram speech-to-text adapter.

    Buffers all audio chunks from the pipeline and submits them to Deepgram's
    pre-recorded endpoint in a single call.

    Requirements:
      pip install 'deepgram-sdk>=3.2.0'
      STT_API_KEY set to your Deepgram API key.

    Input audio format from the pipeline:
      linear16 PCM, 16 kHz, mono

    Implementation detail:
      We wrap raw PCM into an in-memory WAV file before sending it to Deepgram.
      That avoids needing raw-audio query params and matches the SDK's normal
      pre-recorded file flow.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "nova-2",
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        try:
            from deepgram import DeepgramClient
        except ImportError as exc:
            raise ImportError(
                "deepgram-sdk is not installed. Run: pip install 'deepgram-sdk>=3.2.0'"
            ) from exc

        key = api_key or os.getenv("STT_API_KEY") or os.getenv("DEEPGRAM_API_KEY")
        if not key:
            raise ValueError(
                "Deepgram API key not set. Add STT_API_KEY to .env or pass api_key= directly."
            )

        self._client = DeepgramClient(api_key=key)
        self._model = model
        self._sample_rate = sample_rate
        self._channels = channels

    async def _maybe_await(self, value):
        if inspect.isawaitable(value):
            return await value
        return value

    def _pcm_to_wav_bytes(self, pcm_bytes: bytes) -> bytes:
        """
        Wrap headerless linear16 PCM into a WAV container in memory.
        """
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self._channels)
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(pcm_bytes)
        return buffer.getvalue()

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[dict]:
        """
        Buffer all audio chunks then submit to Deepgram's pre-recorded endpoint.

        Yields at most one "final" event per call, containing the full
        transcript for the buffered utterance.
        """
        chunks = []
        async for chunk in audio_stream:
            if chunk:
                chunks.append(chunk)

        if not chunks:
            logger.info("deepgram_no_audio_chunks")
            return

        pcm_bytes = b"".join(chunks)
        wav_bytes = self._pcm_to_wav_bytes(pcm_bytes)

        logger.info(
            "deepgram_transcribe_start pcm_bytes=%s wav_bytes=%s model=%s sample_rate=%s channels=%s",
            len(pcm_bytes),
            len(wav_bytes),
            self._model,
            self._sample_rate,
            self._channels,
        )

        response = None

        # Deepgram Python SDK documented shape:
        # client.listen.v1.media.transcribe_file(request=<file bytes>, model="nova-3")
        try:
            call = self._client.listen.v1.media.transcribe_file(
                request=wav_bytes,
                model=self._model,
                smart_format=True,
            )
            response = await self._maybe_await(call)
        except Exception as exc:
            logger.warning("deepgram_request_wav_bytes_failed error=%s", exc)

        # Fallback: file-like bytes wrapper if this SDK build prefers it.
        if response is None:
            try:
                call = self._client.listen.v1.media.transcribe_file(
                    request=io.BytesIO(wav_bytes),
                    model=self._model,
                    smart_format=True,
                )
                response = await self._maybe_await(call)
            except Exception as exc:
                logger.warning("deepgram_request_wav_filelike_failed error=%s", exc)

        if response is None:
            logger.error("deepgram_transcribe_failed_no_response")
            return

        transcript = ""
        confidence = None

        # Typed response path
        try:
            transcript = response.results.channels[0].alternatives[0].transcript or ""
            confidence = response.results.channels[0].alternatives[0].confidence
        except Exception:
            pass

        # Dict-style fallback
        if not transcript:
            try:
                channels = response.get("results", {}).get("channels", [])
                alt = channels[0].get("alternatives", [{}])[0] if channels else {}
                transcript = (alt.get("transcript") or "").strip()
                confidence = alt.get("confidence")
            except Exception:
                pass

        if transcript and transcript.strip():
            final_text = transcript.strip()
            logger.info("deepgram_final_transcript text=%s", final_text[:200])
            yield {
                "type": "final",
                "text": final_text,
                "is_end_of_turn": True,
                "confidence": confidence,
            }
            return

        logger.warning("deepgram_empty_transcript response_type=%s", type(response).__name__)

    async def close(self) -> None:
        pass