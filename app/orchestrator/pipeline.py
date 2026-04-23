"""
Pipecat pipeline — STT → Dialogue → TTS (Live transport compatible)

Defines the real-time voice processing chain using Pipecat's Pipeline
and FrameProcessor model.

Key fixes:
- STTPipelineService no longer depends only on UserStoppedSpeakingFrame.
- It now also detects sustained PCM silence inside a continuous audio stream,
  so buffered audio is sent to STT even when the transport keeps delivering
  silence frames and does not emit VAD stop frames reliably.
- TTSPipelineService now emits TTSAudioRawFrame instead of generic
  AudioRawFrame so Pipecat output transports can route synthesized audio
  correctly.
"""

import asyncio
import audioop
import logging
from typing import AsyncIterator, List, Optional, TYPE_CHECKING

from pipecat.frames.frames import (
    AudioRawFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameProcessor

try:
    from pipecat.frames.frames import (
        UserStartedSpeakingFrame,
        UserStoppedSpeakingFrame,
    )
    _HAS_VAD_FRAMES = True
except ImportError:
    UserStartedSpeakingFrame = None  # type: ignore[assignment,misc]
    UserStoppedSpeakingFrame = None  # type: ignore[assignment,misc]
    _HAS_VAD_FRAMES = False

if TYPE_CHECKING:
    from app.orchestrator.transport import LiveKitTransport, TransportBase

from app.adapters.factory import get_llm_adapter
from app.adapters.llm import DialogueAdapter, StubDialogueAdapter
from app.adapters.stt import STTAdapter, StubSTTAdapter
from app.core.logging import LatencyTimer
from app.dialogue.signals import classify_turn
from app.memory.engine import MemoryEngine
from app.memory.writer import MemoryWriter
from app.models.session import SessionModel
from app.orchestrator.context import HISTORY_MAX_TURNS, build_dialogue_context
from app.relationship.engine import RelationshipEngine
from app.voice.renderer import LiveVoiceRenderer

logger = logging.getLogger(__name__)


class STTPipelineService(FrameProcessor):
    """
    Audio buffering + STT transcription service.

    Behavior:
      - Buffers AudioRawFrame bytes from the user.
      - Flushes immediately on UserStoppedSpeakingFrame when available.
      - Also detects sustained PCM silence inside a continuous audio stream.
      - Keeps an idle flush timer as a fallback when frames stop arriving.
    """

    def __init__(
        self,
        adapter: Optional[STTAdapter] = None,
        flush_silence_seconds: float = 0.7,
        silence_rms_threshold: int = 140,
    ) -> None:
        super().__init__()
        self._adapter: STTAdapter = adapter or StubSTTAdapter()
        self._audio_buffer: List[bytes] = []
        self._flush_silence_seconds = flush_silence_seconds
        self._silence_rms_threshold = silence_rms_threshold

        self._flush_task: Optional[asyncio.Task] = None
        self._flush_lock = asyncio.Lock()

        self._speech_started = False
        self._silence_run_seconds = 0.0

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, AudioRawFrame):
            if not frame.audio:
                return

            is_silent = self._is_silent_frame(frame)

            if is_silent and not self._speech_started:
                return

            self._audio_buffer.append(frame.audio)

            if is_silent:
                self._silence_run_seconds += self._frame_duration_seconds(frame)
            else:
                self._speech_started = True
                self._silence_run_seconds = 0.0

            self._schedule_idle_flush()

            if self._speech_started and self._silence_run_seconds >= self._flush_silence_seconds:
                self._cancel_idle_flush()
                logger.info(
                    "stt_silence_flush silence_run_s=%.3f buffered_chunks=%d",
                    self._silence_run_seconds,
                    len(self._audio_buffer),
                )
                await self._transcribe_buffer()
            return

        if _HAS_VAD_FRAMES and UserStartedSpeakingFrame and isinstance(frame, UserStartedSpeakingFrame):
            self._cancel_idle_flush()
            self._speech_started = True
            self._silence_run_seconds = 0.0
            await self.push_frame(frame)
            return

        if _HAS_VAD_FRAMES and UserStoppedSpeakingFrame and isinstance(frame, UserStoppedSpeakingFrame):
            self._cancel_idle_flush()
            logger.info("stt_vad_flush buffered_chunks=%d", len(self._audio_buffer))
            await self._transcribe_buffer()
            return

        await self.push_frame(frame)

    def _frame_duration_seconds(self, frame: AudioRawFrame) -> float:
        sample_rate = getattr(frame, "sample_rate", 16000) or 16000
        num_channels = getattr(frame, "num_channels", 1) or 1
        bytes_per_sample = 2
        denom = sample_rate * num_channels * bytes_per_sample
        if denom <= 0:
            return 0.0
        return len(frame.audio) / denom

    def _is_silent_frame(self, frame: AudioRawFrame) -> bool:
        try:
            rms = audioop.rms(frame.audio, 2)
            return rms <= self._silence_rms_threshold
        except Exception:
            return False

    def _schedule_idle_flush(self) -> None:
        self._cancel_idle_flush()
        self._flush_task = asyncio.create_task(self._flush_after_timeout())

    def _cancel_idle_flush(self) -> None:
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        self._flush_task = None

    async def _flush_after_timeout(self) -> None:
        try:
            await asyncio.sleep(self._flush_silence_seconds)
            logger.info("stt_idle_flush buffered_chunks=%d", len(self._audio_buffer))
            await self._transcribe_buffer()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("stt_idle_flush_failed error=%s", exc)

    async def _transcribe_buffer(self) -> None:
        async with self._flush_lock:
            if not self._audio_buffer:
                self._speech_started = False
                self._silence_run_seconds = 0.0
                return

            accumulated = b"".join(self._audio_buffer)
            self._audio_buffer = []
            self._speech_started = False
            self._silence_run_seconds = 0.0

            async def _stream() -> AsyncIterator[bytes]:
                yield accumulated

            with LatencyTimer("stt"):
                emitted = False
                async for event in self._adapter.transcribe_stream(_stream()):
                    if event.get("type") == "final" and event.get("text"):
                        text = event["text"].strip()
                        logger.info("stt_final_transcript text=%s", text[:200])
                        emitted = True
                        await self.push_frame(
                            TranscriptionFrame(
                                text=text,
                                user_id="",
                                timestamp="",
                            )
                        )
                if not emitted:
                    logger.info("stt_no_final_transcript")

    async def cleanup(self) -> None:
        self._cancel_idle_flush()
        try:
            await self._adapter.close()
        except Exception:
            pass


class DialoguePipelineService(FrameProcessor):
    """
    Consumes TranscriptionFrame, emits TextFrame chunks (streaming).
    """

    def __init__(
        self,
        adapter: Optional[DialogueAdapter] = None,
        session: Optional[SessionModel] = None,
        engine: Optional[MemoryEngine] = None,
    ) -> None:
        super().__init__()
        self._adapter: DialogueAdapter = adapter or StubDialogueAdapter()
        self._session: SessionModel = session or SessionModel()
        self._engine: MemoryEngine = engine or MemoryEngine()
        self._writer = MemoryWriter(self._engine)
        self._relationship_engine = RelationshipEngine(self._engine)
        self._history: List[dict] = []

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            user_text = frame.text

            context = await build_dialogue_context(self._session, self._engine)
            system_prompt = context.to_system_prompt()

            assistant_chunks: List[str] = []
            with LatencyTimer("llm"):
                async for chunk in self._adapter.generate(
                    system_prompt=system_prompt,
                    conversation_history=self._history,
                    user_message=user_text,
                ):
                    assistant_chunks.append(chunk)
                    await self.push_frame(TextFrame(text=chunk))

            assistant_text = "".join(assistant_chunks)

            self._history.append({"role": "user", "text": user_text})
            self._history.append({"role": "assistant", "text": assistant_text})
            if len(self._history) > HISTORY_MAX_TURNS:
                self._history = self._history[-HISTORY_MAX_TURNS:]

            user_id = self._session.user_id
            await self._writer.process_turn(
                session_id=self._session.session_id,
                user_id=user_id,
                user_text=user_text,
                assistant_text=assistant_text,
            )

            if user_id and user_id != "anonymous":
                signal = classify_turn(user_text)
                if signal.conflict or signal.positive:
                    await self._relationship_engine.apply_turn_signal(
                        user_id=user_id,
                        positive=signal.positive,
                        conflict=signal.conflict,
                    )
            return

        await self.push_frame(frame)


class TTSPipelineService(FrameProcessor):
    """
    Consumes TextFrame chunks, emits TTSAudioRawFrame.

    Delegates to LiveVoiceRenderer.

    Barge-in:
      When UserStartedSpeakingFrame arrives while the assistant is playing,
      the current TTS render is interrupted immediately.
    """

    def __init__(self, renderer: Optional[LiveVoiceRenderer] = None) -> None:
        super().__init__()
        self._renderer: LiveVoiceRenderer = renderer or LiveVoiceRenderer()
        self._barge_in: asyncio.Event = asyncio.Event()
        self._emotional_hint: Optional[str] = None

    def set_emotional_hint(self, hint: Optional[str]) -> None:
        self._emotional_hint = hint

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)

        if _HAS_VAD_FRAMES and UserStartedSpeakingFrame and isinstance(frame, UserStartedSpeakingFrame):
            self._barge_in.set()
            await self.push_frame(frame)
            return

        if isinstance(frame, TextFrame):
            self._barge_in.clear()

            async def _text_stream() -> AsyncIterator[str]:
                yield frame.text

            with LatencyTimer("tts"):
                async for audio_bytes in self._renderer.render(
                    _text_stream(), emotional_hint=self._emotional_hint
                ):
                    if self._barge_in.is_set():
                        break
                    if audio_bytes:
                        frame_out = TTSAudioRawFrame(
                            audio=audio_bytes,
                            sample_rate=16000,
                            num_channels=1,
                            context_id=self._session_context_id(),
                        )
                        logger.info("tts_output_frame_type type=%s", type(frame_out).__name__)
                        await self.push_frame(frame_out)
            return

        await self.push_frame(frame)

    def _session_context_id(self) -> str:
        # Stable non-empty context id for Pipecat TTS observers/transports
        return "aura-live-tts"


def build_pipeline(
    stt_adapter: Optional[STTAdapter] = None,
    llm_adapter: Optional[DialogueAdapter] = None,
    session: Optional[SessionModel] = None,
    engine: Optional[MemoryEngine] = None,
) -> Pipeline:
    stt = STTPipelineService(adapter=stt_adapter)
    dialogue = DialoguePipelineService(
        adapter=llm_adapter or get_llm_adapter(),
        session=session,
        engine=engine,
    )
    tts = TTSPipelineService()
    return Pipeline([stt, dialogue, tts])


def build_voice_pipeline(
    transport,
    stt_adapter: Optional[STTAdapter] = None,
    llm_adapter: Optional[DialogueAdapter] = None,
    renderer: Optional[LiveVoiceRenderer] = None,
    session: Optional[SessionModel] = None,
    engine: Optional[MemoryEngine] = None,
) -> Pipeline:
    stt = STTPipelineService(adapter=stt_adapter)
    dialogue = DialoguePipelineService(
        adapter=llm_adapter or get_llm_adapter(),
        session=session,
        engine=engine,
    )
    tts = TTSPipelineService(renderer=renderer)

    return Pipeline([
        transport.input(),
        stt,
        dialogue,
        tts,
        transport.output(),
    ])