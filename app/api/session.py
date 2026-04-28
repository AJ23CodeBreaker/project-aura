"""
Session Bootstrap API

Called by the frontend to start and end companion sessions.

RULES:
  - This endpoint must NEVER return provider secrets to the frontend.
  - Only safe session metadata is returned.
  - The demo_token field is consumed server-side and NEVER echoed, logged,
    or included in any response body.
  - adult_mode reflects server-side config only; the frontend cannot force it.

LiveKit migration:
  - Demo sessions with LiveKit configured return:
      transport_url        = LIVEKIT_URL
      transport_token      = user join token
      transport_room_name  = room name
      transport_provider   = "livekit"
  - The server bot joins the same room in the background using a bot token.
  - Standard sessions remain text-only.

Typed-text playback:
  - POST /session/{session_id}/tts converts assistant text into browser-playable
    WAV audio so the frontend Play Voice button can speak typed-mode replies.
"""

import asyncio
import concurrent.futures
import datetime
import hmac
import io
import logging
import secrets
import threading
import wave
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.adapters.factory import get_demo_llm_adapter, get_llm_adapter
from app.config.settings import settings
from app.memory.engine import MemoryEngine
from app.orchestrator.dialogue_runner import (
    clear_session_history,
    run_text_turn,
    stream_text_turn,
)
from app.models.session import SessionStatus
from app.session.manager import SessionManager

logger = logging.getLogger(__name__)

app = FastAPI(title="Project Aura — Session Bootstrap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_engine = MemoryEngine()
_session_manager = SessionManager(memory_engine=_engine)
_llm_adapter = get_llm_adapter()
_demo_llm_adapter = get_demo_llm_adapter()

# Voice pipeline futures keyed by session_id. These are scheduled onto a
# dedicated background asyncio loop thread so they are not tied to the
# request-scoped ASGI loop.
_voice_tasks: dict[str, concurrent.futures.Future] = {}
_livekit_rooms: dict[str, str] = {}

_voice_loop: Optional[asyncio.AbstractEventLoop] = None
_voice_loop_thread: Optional[threading.Thread] = None
_voice_loop_ready = threading.Event()


# --------------------------------------------------------------------------- #
# Request / response schemas
# --------------------------------------------------------------------------- #

class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = None
    demo_token: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    adult_mode: bool
    transport_url: Optional[str] = None
    transport_token: Optional[str] = None
    transport_room_name: Optional[str] = None
    transport_provider: Optional[str] = None


class TurnRequest(BaseModel):
    user_text: str


class TurnResponse(BaseModel):
    session_id: str
    assistant_text: str


class TTSRequest(BaseModel):
    text: str


# --------------------------------------------------------------------------- #
# Internal helpers — background voice loop
# --------------------------------------------------------------------------- #

def _voice_loop_worker() -> None:
    """
    Dedicated background asyncio loop for long-lived voice tasks.

    This keeps the LiveKit / Pipecat voice pipeline off the request-scoped
    ASGI loop, which makes it much less likely to be cancelled when the
    session bootstrap request finishes.
    """
    global _voice_loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _voice_loop = loop
    _voice_loop_ready.set()

    logger.info("voice_loop_started")
    loop.run_forever()


def _ensure_voice_loop() -> asyncio.AbstractEventLoop:
    """
    Lazily create a dedicated background event loop thread for voice tasks.
    """
    global _voice_loop_thread, _voice_loop

    if _voice_loop is not None and _voice_loop_thread and _voice_loop_thread.is_alive():
        return _voice_loop

    _voice_loop_ready.clear()
    _voice_loop_thread = threading.Thread(
        target=_voice_loop_worker,
        name="aura-voice-loop",
        daemon=True,
    )
    _voice_loop_thread.start()

    if not _voice_loop_ready.wait(timeout=5.0) or _voice_loop is None:
        raise RuntimeError("Failed to start background voice loop.")

    return _voice_loop


def _on_voice_future_done(session_id: str, fut: concurrent.futures.Future) -> None:
    """
    Cleanup + logging callback when a voice pipeline future completes.
    """
    current = _voice_tasks.get(session_id)
    if current is fut:
        _voice_tasks.pop(session_id, None)

    try:
        fut.result()
        logger.info("voice_pipeline_finished session=%s", session_id)
    except concurrent.futures.CancelledError:
        logger.info("voice_pipeline_future_cancelled session=%s", session_id)
    except Exception as exc:
        logger.error("voice_pipeline_future_error session=%s error=%s", session_id, exc)


# --------------------------------------------------------------------------- #
# Internal helpers — demo token
# --------------------------------------------------------------------------- #

def _validate_demo_token(provided: Optional[str]) -> bool:
    if not provided or not settings.demo_token:
        return False
    return hmac.compare_digest(
        provided.encode("utf-8"),
        settings.demo_token.encode("utf-8"),
    )


def _pick_adapter(session_adult_mode: bool):
    return _demo_llm_adapter if session_adult_mode else _llm_adapter


# --------------------------------------------------------------------------- #
# Internal helpers — LiveKit
# --------------------------------------------------------------------------- #

def _make_livekit_room_name(session_id: str) -> str:
    return f"aura-demo-{session_id[:8]}"


def _make_livekit_tokens(room_name: str) -> tuple[str, str]:
    """
    Return (user_token, bot_token) for the same LiveKit room.

    Uses LIVEKIT_API_KEY / LIVEKIT_API_SECRET from environment via settings.
    """
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise RuntimeError("LiveKit credentials are not configured.")

    try:
        from livekit.api import AccessToken, VideoGrants
    except ImportError as exc:
        raise RuntimeError(
            "livekit-api package is not installed."
        ) from exc

    user_token = (
        AccessToken()
        .with_identity(f"user-{secrets.token_hex(3)}")
        .with_name("Aura User")
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
            )
        )
        .with_ttl(datetime.timedelta(hours=1))
        .to_jwt()
    )

    bot_token = (
        AccessToken()
        .with_identity(f"bot-{secrets.token_hex(3)}")
        .with_name("Aura")
        .with_kind("agent")
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
            )
        )
        .with_ttl(datetime.timedelta(hours=1))
        .to_jwt()
    )

    return user_token, bot_token


# --------------------------------------------------------------------------- #
# Internal helpers — typed text TTS playback
# --------------------------------------------------------------------------- #

async def _single_text_stream(text: str) -> AsyncIterator[str]:
    """
    Adapts one text string into the async text-stream interface expected by
    FishAudioTTSAdapter.
    """
    yield text


def _pcm16_mono_16k_to_wav(pcm_bytes: bytes) -> bytes:
    """
    Wrap 16 kHz mono signed 16-bit PCM bytes in a WAV container so browser
    Audio() can play the result.
    """
    if not pcm_bytes:
        return b""

    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm_bytes)

    return out.getvalue()


async def _synthesize_text_to_wav(text: str) -> bytes:
    """
    Generate browser-playable WAV audio for a typed-mode assistant reply.

    Internally reuses FishAudioTTSAdapter, which calls either:
      - hosted Fish API if FISH_AUDIO_URL=https://api.fish.audio, or
      - self-hosted Modal aura-fish if FISH_AUDIO_URL points there.

    FishAudioTTSAdapter yields 16 kHz mono PCM chunks, so this helper wraps
    those chunks into a WAV container for the browser.
    """
    from app.adapters.tts import FishAudioTTSAdapter

    adapter = None

    try:
        adapter = FishAudioTTSAdapter(
            base_url=settings.fish_audio_url,
            api_key=settings.fish_audio_api_key,
            voice_id=settings.fish_audio_voice_id or "",
        )

        pcm_parts: list[bytes] = []
        async for chunk in adapter.synthesize_stream(_single_text_stream(text)):
            if chunk:
                pcm_parts.append(chunk)

        pcm_bytes = b"".join(pcm_parts)

        if not pcm_bytes:
            raise RuntimeError("Fish TTS returned no PCM audio.")

        wav_bytes = _pcm16_mono_16k_to_wav(pcm_bytes)

        if not wav_bytes:
            raise RuntimeError("Could not wrap PCM audio as WAV.")

        return wav_bytes

    finally:
        if adapter is not None:
            try:
                await adapter.close()
            except Exception as exc:
                logger.warning("tts_adapter_close_failed error=%s", exc)


# --------------------------------------------------------------------------- #
# Internal helpers — voice pipeline background coroutine
# --------------------------------------------------------------------------- #

async def _run_voice_pipeline(session_id: str, room_name: str, bot_token: str) -> None:
    """
    Background coroutine: runs the Deepgram → vLLM → Fish Audio voice pipeline
    connected to a LiveKit room.
    """
    try:
        logger.info(
            "voice_pipeline_starting session=%s room_name=%s",
            session_id,
            room_name,
        )

        session = await _session_manager.get_session(session_id)
        if not session:
            logger.warning("voice_pipeline_missing_session session=%s", session_id)
            return

        from app.adapters.stt import DeepgramSTTAdapter
        from app.adapters.tts import FishAudioTTSAdapter
        from app.orchestrator.pipeline import build_voice_pipeline
        from app.orchestrator.transport import LiveKitTransport
        from app.voice.renderer import LiveVoiceRenderer

        stt_adapter = None
        if settings.stt_api_key:
            try:
                stt_adapter = DeepgramSTTAdapter(api_key=settings.stt_api_key)
            except Exception as exc:
                logger.warning("deepgram_init_failed error=%s", exc)

        tts_adapter = None
        if settings.fish_audio_url:
            try:
                tts_adapter = FishAudioTTSAdapter(
                    base_url=settings.fish_audio_url,
                    api_key=settings.fish_audio_api_key,
                    voice_id=settings.fish_audio_voice_id or "",
                )
            except Exception as exc:
                logger.warning("fish_audio_init_failed error=%s", exc)

        renderer = LiveVoiceRenderer(tts_adapter=tts_adapter)
        transport = LiveKitTransport(
            room_name=room_name,
            token=bot_token,
        )

        pipeline = build_voice_pipeline(
            transport=transport,
            stt_adapter=stt_adapter,
            llm_adapter=_demo_llm_adapter,
            renderer=renderer,
            session=session,
            engine=_engine,
        )

        try:
            from pipecat.pipeline.runner import PipelineRunner
            from pipecat.pipeline.task import PipelineTask

            task = PipelineTask(
                pipeline,
                idle_timeout_secs=None,
                cancel_on_idle_timeout=False,
            )

            @task.event_handler("on_pipeline_error")
            async def _on_pipeline_error(task, frame):
                logger.error(
                    "voice_pipeline_error session=%s error=%s",
                    session_id,
                    frame.error,
                )

            runner = PipelineRunner(handle_sigint=False)
            await runner.run(task)

            logger.info("voice_pipeline_runner_returned session=%s", session_id)

        except Exception as exc:
            logger.error("voice_pipeline_error session=%s error=%s", session_id, exc)

    except asyncio.CancelledError:
        logger.info("voice_pipeline_cancelled session=%s", session_id)
        raise
    except Exception as exc:
        logger.error("voice_pipeline_error session=%s error=%s", session_id, exc)


async def _cancel_voice_task(session_id: str) -> None:
    fut = _voice_tasks.pop(session_id, None)
    if not fut:
        return

    if not fut.done():
        fut.cancel()

    try:
        await asyncio.wait_for(asyncio.wrap_future(fut), timeout=3.0)
    except (asyncio.CancelledError, concurrent.futures.CancelledError, asyncio.TimeoutError):
        pass
    except Exception as exc:
        logger.warning("voice_pipeline_cancel_wait_failed session=%s error=%s", session_id, exc)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@app.post("/session/create", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest) -> SessionCreateResponse:
    is_demo = False
    if request.demo_token is not None:
        if not _validate_demo_token(request.demo_token):
            raise HTTPException(status_code=403, detail="Demo access denied.")
        is_demo = True

    session = await _session_manager.create_session(user_id=request.user_id)

    if is_demo:
        session.adult_mode = True
        session.relationship_level = settings.demo_starting_closeness

    transport_url: Optional[str] = None
    transport_token: Optional[str] = None
    transport_room_name: Optional[str] = None
    transport_provider: Optional[str] = None

    # LiveKit demo path
    if is_demo and settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret:
        try:
            room_name = _make_livekit_room_name(session.session_id)
            user_token, bot_token = _make_livekit_tokens(room_name)

            transport_url = settings.livekit_url
            transport_token = user_token
            transport_room_name = room_name
            transport_provider = "livekit"

            _livekit_rooms[session.session_id] = room_name

            voice_loop = _ensure_voice_loop()
            fut = asyncio.run_coroutine_threadsafe(
                _run_voice_pipeline(
                    session_id=session.session_id,
                    room_name=room_name,
                    bot_token=bot_token,
                ),
                voice_loop,
            )
            _voice_tasks[session.session_id] = fut
            fut.add_done_callback(
                lambda done_fut, sid=session.session_id: _on_voice_future_done(sid, done_fut)
            )

            logger.info(
                "livekit_room_prepared session=%s room_name=%s voice_task_mode=background_loop",
                session.session_id,
                room_name,
            )

        except Exception as exc:
            logger.error(
                "livekit_prepare_failed session=%s error=%s — falling back to text mode",
                session.session_id,
                exc,
            )

    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status.value,
        adult_mode=session.adult_mode,
        transport_url=transport_url,
        transport_token=transport_token,
        transport_room_name=transport_room_name,
        transport_provider=transport_provider,
    )


@app.post("/session/{session_id}/turn", response_model=TurnResponse)
async def turn(session_id: str, request: TurnRequest) -> TurnResponse:
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status == SessionStatus.ENDED:
        raise HTTPException(status_code=404, detail="Session has ended.")

    assistant_text = await run_text_turn(
        session=session,
        user_text=request.user_text,
        engine=_engine,
        adapter=_pick_adapter(session.adult_mode),
    )
    return TurnResponse(session_id=session_id, assistant_text=assistant_text)


@app.post("/session/{session_id}/turn/stream")
async def turn_stream(session_id: str, request: TurnRequest) -> StreamingResponse:
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status == SessionStatus.ENDED:
        raise HTTPException(status_code=404, detail="Session has ended.")

    adapter = _pick_adapter(session.adult_mode)

    async def event_generator():
        async for chunk in stream_text_turn(
            session=session,
            user_text=request.user_text,
            engine=_engine,
            adapter=adapter,
        ):
            safe = chunk.replace("\r", " ").replace("\n", " ")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/session/{session_id}/tts")
async def text_to_speech(session_id: str, request: TTSRequest) -> Response:
    """
    Generate browser-playable WAV audio for a typed-mode assistant reply.

    This endpoint is intentionally separate from /turn and /turn/stream:
      - /turn/stream handles dialogue + memory + relationship state
      - /tts only speaks the assistant text that was already generated

    Frontend usage:
      POST /session/{session_id}/tts
      body: { "text": "assistant text" }
      response: audio/wav
    """
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status == SessionStatus.ENDED:
        raise HTTPException(status_code=404, detail="Session has ended.")

    text = (request.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    if not settings.fish_audio_url:
        raise HTTPException(status_code=500, detail="FISH_AUDIO_URL is not configured.")

    try:
        logger.info(
            "typed_tts_start session=%s text_len=%s voice_id_set=%s",
            session_id,
            len(text),
            bool(settings.fish_audio_voice_id),
        )

        wav_bytes = await _synthesize_text_to_wav(text)

        logger.info(
            "typed_tts_success session=%s wav_bytes=%s",
            session_id,
            len(wav_bytes),
        )

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'inline; filename="aura-reply.wav"',
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("typed_tts_failed session=%s error=%s", session_id, exc)
        raise HTTPException(status_code=500, detail="TTS generation failed.")


@app.post("/session/{session_id}/end")
async def end_session(session_id: str) -> dict:
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    await _cancel_voice_task(session_id)
    _livekit_rooms.pop(session_id, None)

    await _session_manager.end_session(session_id)
    clear_session_history(session_id)
    return {"status": "ended", "session_id": session_id}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "project-aura-bootstrap"}