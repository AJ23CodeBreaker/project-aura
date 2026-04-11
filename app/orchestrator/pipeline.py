"""
Pipecat pipeline skeleton — STT → Dialogue → TTS

Defines the real-time voice processing chain using Pipecat's Pipeline
and FrameProcessor model.

--- Architecture rule ---
One canonical live voice path. TTSPipelineService delegates exclusively to
LiveVoiceRenderer, which wraps the single TTSAdapter. Do not add extra
TTS layers here.

--- Provider injection ---
All adapters default to stubs. To use a real provider, pass its adapter
to build_pipeline(). No changes to pipeline structure needed.

--- Pipecat API assumptions ---
Written against pipecat-ai's FrameProcessor protocol. Key assumptions:
  - FrameProcessor.process_frame(frame, direction) is async
  - FrameProcessor.push_frame(frame) is async; direction defaults to DOWNSTREAM
  - Frame types: AudioRawFrame, TextFrame, TranscriptionFrame live in
    pipecat.frames.frames
  - FrameDirection lives in pipecat.processors.frame_processor
  - Pipeline([processor, ...]) chains processors in order
  - AudioRawFrame(audio: bytes, sample_rate: int, num_channels: int)
  - TextFrame(text: str)
  - TranscriptionFrame(text: str, user_id: str, timestamp: str)

If the installed pipecat-ai version has different import paths or
constructor signatures, adjust the imports at the top of this file.
The processor logic itself (process_frame bodies) will not need changes.
"""
from typing import AsyncIterator, List, Optional

from pipecat.frames.frames import (
    AudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.adapters.llm import DialogueAdapter, StubDialogueAdapter
from app.adapters.stt import STTAdapter, StubSTTAdapter
from app.core.logging import LatencyTimer
from app.memory.engine import MemoryEngine
from app.memory.writer import MemoryWriter
from app.models.session import SessionModel
from app.orchestrator.context import HISTORY_MAX_TURNS, build_dialogue_context
from app.relationship.engine import RelationshipEngine
from app.voice.renderer import LiveVoiceRenderer


class STTPipelineService(FrameProcessor):
    """
    Consumes AudioRawFrame, emits TranscriptionFrame on final transcript.
    Delegates to STTAdapter; defaults to StubSTTAdapter.
    """

    def __init__(self, adapter: Optional[STTAdapter] = None) -> None:
        super().__init__()
        self._adapter: STTAdapter = adapter or StubSTTAdapter()

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, AudioRawFrame):
            audio_bytes = frame.audio

            async def _byte_stream() -> AsyncIterator[bytes]:
                yield audio_bytes

            with LatencyTimer("stt"):
                async for event in self._adapter.transcribe_stream(_byte_stream()):
                    if event.get("type") == "final" and event.get("text"):
                        await self.push_frame(
                            TranscriptionFrame(
                                text=event["text"],
                                user_id="",
                                timestamp="",
                            )
                        )


class DialoguePipelineService(FrameProcessor):
    """
    Consumes TranscriptionFrame, emits TextFrame chunks (streaming).

    Calls build_dialogue_context() once per turn to assemble the three-layer
    system prompt, then makes ONE call to DialogueAdapter.generate().

    Maintains a minimal in-session history buffer (HISTORY_MAX_TURNS entries).
    History format: [{"role": "user"|"assistant", "text": str}, ...]
    History is in-memory and session-scoped — it is not persisted.
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
        # Minimal rolling history buffer — not a full transcript system
        self._history: List[dict] = []

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            user_text = frame.text

            # Assemble three-layer context → one system prompt string
            context = await build_dialogue_context(self._session, self._engine)
            system_prompt = context.to_system_prompt()

            # ONE LLM call per turn — stream text chunks downstream immediately
            assistant_chunks: List[str] = []
            with LatencyTimer("llm"):
                async for chunk in self._adapter.generate(
                    system_prompt=system_prompt,
                    conversation_history=self._history,
                    user_message=user_text,
                ):
                    assistant_chunks.append(chunk)
                    await self.push_frame(TextFrame(text=chunk))

            # Update rolling history; trim to cap
            self._history.append({"role": "user", "text": user_text})
            self._history.append({"role": "assistant", "text": "".join(assistant_chunks)})
            if len(self._history) > HISTORY_MAX_TURNS:
                self._history = self._history[-HISTORY_MAX_TURNS:]

            # Memory write and relationship signal — after response is fully generated.
            # Non-blocking relative to already-pushed TTS frames; awaited here for
            # correctness (writes must complete before session end triggers clean-up).
            user_id = self._session.user_id
            await self._writer.process_turn(
                session_id=self._session.session_id,
                user_id=user_id,
                user_text=user_text,
                assistant_text="".join(assistant_chunks),
            )
            if user_id and user_id != "anonymous":
                await self._relationship_engine.apply_turn_signal(
                    user_id=user_id,
                    positive=True,  # Phase 4: every completed turn counts as positive
                    conflict=False, # Phase 5 will detect conflict from dialogue signals
                )


class TTSPipelineService(FrameProcessor):
    """
    Consumes TextFrame chunks, emits AudioRawFrame.

    Delegates to LiveVoiceRenderer — preserving the one canonical live
    voice path rule. Each TextFrame is rendered individually as it arrives
    (streaming-friendly; batching is a Phase 4+ optimisation).
    """

    def __init__(self, renderer: Optional[LiveVoiceRenderer] = None) -> None:
        super().__init__()
        self._renderer: LiveVoiceRenderer = renderer or LiveVoiceRenderer()

    async def process_frame(self, frame, direction) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TextFrame):
            async def _text_stream() -> AsyncIterator[str]:
                yield frame.text

            with LatencyTimer("tts"):
                async for audio_bytes in self._renderer.render(_text_stream()):
                    if audio_bytes:
                        await self.push_frame(
                            AudioRawFrame(
                                audio=audio_bytes,
                                sample_rate=16000,
                                num_channels=1,
                            )
                        )


def build_pipeline(
    stt_adapter: Optional[STTAdapter] = None,
    llm_adapter: Optional[DialogueAdapter] = None,
    session: Optional[SessionModel] = None,
    engine: Optional[MemoryEngine] = None,
) -> Pipeline:
    """
    Construct the STT → Dialogue → TTS Pipecat pipeline.

    All parameters are optional; stub adapters are used by default.
    Inject real provider adapters here when they are wired in later phases.

    In production, DailyTransport input/output processors would wrap this
    pipeline. For local testing, frames are pushed directly to
    pipeline.processors[0] (see app/orchestrator/runner.py).
    """
    stt = STTPipelineService(adapter=stt_adapter)
    dialogue = DialoguePipelineService(
        adapter=llm_adapter,
        session=session,
        engine=engine,
    )
    tts = TTSPipelineService()
    return Pipeline([stt, dialogue, tts])
