"""
Orchestrator runner

Two entry points:

  run_context_test()  — pure Python, no Pipecat required.
                        Tests the three-layer context assembly and stub
                        dialogue adapter end-to-end. Run this first.

  run_fake_turn()     — requires pipecat-ai to be installed.
                        Pushes one silent audio frame through the full
                        Pipecat pipeline using LocalTransport and all
                        stub adapters. Proves instantiation and frame
                        routing work correctly.

  run_session()       — Modal entry point stub.
                        Not yet implemented; wired in Phase 3+.
"""
import asyncio
from typing import Optional

from app.adapters.llm import StubDialogueAdapter
from app.memory.engine import MemoryEngine
from app.models.session import SessionModel
from app.orchestrator.context import build_dialogue_context
from app.orchestrator.transport import LocalTransport


# ---------------------------------------------------------------------------
# Pure Python context test — no Pipecat dependency
# ---------------------------------------------------------------------------

async def run_context_test() -> dict:
    """
    Test three-layer context assembly using all stubs.

    Verifies:
    - Layer 1 (identity) renders correctly
    - Layer 2 (memory) returns stub MemoryContext without error
    - Layer 3 (scene) builds from a default SessionModel
    - to_system_prompt() assembles all three into one string
    - StubDialogueAdapter.generate() produces a response from that prompt

    No Pipecat, no network, no credentials required.
    """
    session = SessionModel()
    engine = MemoryEngine()

    context = await build_dialogue_context(session, engine)
    system_prompt = context.to_system_prompt()

    response_chunks = []
    async for chunk in StubDialogueAdapter().generate(
        system_prompt=system_prompt,
        conversation_history=[],
        user_message="Hello, are you there?",
    ):
        response_chunks.append(chunk)

    return {
        "status": "ok",
        "system_prompt_length": len(system_prompt),
        "response": "".join(response_chunks),
        "layers": {
            "identity_name": context.identity.name,
            "closeness": context.scene.closeness.name,
            "adult_enabled": context.scene.adult_enabled,
            "memory_user_facts": context.memory.user_facts,
        },
    }


# ---------------------------------------------------------------------------
# Full pipeline fake-turn test — requires pipecat-ai
# ---------------------------------------------------------------------------

async def run_fake_turn() -> dict:
    """
    Run one fake turn through the complete Pipecat pipeline.

    Uses LocalTransport (one silent audio frame, no real I/O),
    all stub adapters, and a default SessionModel.

    Proves:
    - Pipeline instantiation succeeds
    - A frame can be pushed through STT → Dialogue → TTS without error
    - Latency timers fire without crashing

    Requires pipecat-ai to be installed:
        pip install -r requirements.txt
    """
    from pipecat.frames.frames import AudioRawFrame, StartFrame
    from pipecat.processors.frame_processor import FrameDirection

    from app.orchestrator.pipeline import build_pipeline

    session = SessionModel()
    transport = LocalTransport()
    pipeline = build_pipeline(session=session)

    # Initialize the pipeline before any data frames
    await pipeline.processors[0].process_frame(StartFrame(), FrameDirection.DOWNSTREAM)

    # Get the single silent frame from LocalTransport
    async for audio_bytes in transport.audio_input_stream():
        frame = AudioRawFrame(audio=audio_bytes, sample_rate=16000, num_channels=1)
        # Push directly into the first processor; Pipecat routes it downstream
        await pipeline.processors[0].process_frame(frame, FrameDirection.DOWNSTREAM)
        break  # LocalTransport yields only one frame

    return {
        "status": "ok",
        "session_id": session.session_id,
        "message": "fake turn completed through full pipeline",
    }


# ---------------------------------------------------------------------------
# Modal entry point — STUB
# ---------------------------------------------------------------------------

async def run_session(session_id: str) -> dict:
    """
    Orchestrator entry point for a live companion session.

    STUB: not yet implemented.
    Phase 3+: load session, wire DailyTransport, run pipeline until session ends.
    """
    # TODO Phase 3+:
    #   session = await session_manager.get_session(session_id)
    #   transport = DailyTransport(room_url=..., token=...)
    #   pipeline = build_pipeline(session=session)
    #   runner = PipelineRunner()
    #   task = PipelineTask(pipeline, PipelineParams(...))
    #   await runner.run(task)
    raise NotImplementedError(
        "run_session() is not yet implemented. "
        "Wire DailyTransport and PipelineRunner here in Phase 3+."
    )


# ---------------------------------------------------------------------------
# Local convenience runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    print("--- Context test (pure Python) ---")
    result = asyncio.run(run_context_test())
    print(json.dumps(result, indent=2))

    print("\n--- Fake turn test (requires pipecat-ai) ---")
    try:
        result = asyncio.run(run_fake_turn())
        print(json.dumps(result, indent=2))
    except ImportError as exc:
        print(f"Skipped: pipecat-ai not installed ({exc})")
    except Exception as exc:
        print(f"Error: {exc}")
