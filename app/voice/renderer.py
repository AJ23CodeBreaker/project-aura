"""
Live Voice Renderer

The single canonical live voice rendering path for Project Aura v1.

ARCHITECTURE RULE (per ARCHITECTURE.md §10.3):
  Use ONE primary live voice rendering path. Do not add extra live
  transformation layers without explicit justification.
  Offline voice experimentation belongs outside this module.

The renderer wraps the TTS adapter and is the only place in the codebase
that converts dialogue text to audio. The orchestrator calls this.

Phase 12A: FishAudioTTSAdapter is injected by build_voice_pipeline().
  emotional_hint is propagated from SessionController.current_mood through
  TTSPipelineService → LiveVoiceRenderer.render() → TTSAdapter.synthesize_stream().
  Actress voice identity is preserved through the adapter's voice_id / reference_id.
"""
from typing import AsyncIterator, Optional

from app.adapters.tts import StubTTSAdapter, TTSAdapter


class LiveVoiceRenderer:
    """
    Canonical live voice renderer.

    Defaults to StubTTSAdapter when no real provider is injected.
    Inject FishAudioTTSAdapter (or any TTSAdapter) via the constructor.
    """

    def __init__(self, tts_adapter: Optional[TTSAdapter] = None) -> None:
        self._adapter: TTSAdapter = tts_adapter or StubTTSAdapter()

    async def render(
        self,
        text_stream: AsyncIterator[str],
        emotional_hint: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """
        Convert a streamed dialogue text into streamed companion audio.

        Args:
            text_stream:    Streaming text chunks from the dialogue engine.
            emotional_hint: Optional tone hint passed to the TTS provider.
                            e.g. "warm", "playful", "soft", "intimate"

        Yields:
            Audio bytes for streaming to the WebRTC client.
        """
        async for chunk in self._adapter.synthesize_stream(text_stream, emotional_hint):
            yield chunk

    async def close(self) -> None:
        await self._adapter.close()
