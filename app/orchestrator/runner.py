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

  run_memory_test()   — pure Python, no Pipecat required.
                        Verifies memory persistence across two simulated
                        turns using a fixed test user ID ("test-user-001").
                        Run this to confirm Phase 4 memory and relationship
                        state are working end-to-end.

  run_session()       — Modal entry point stub.
                        Not yet implemented; wired in Phase 3+.
"""
import asyncio
from typing import Optional

from app.adapters.llm import StubDialogueAdapter
from app.dialogue.signals import classify_turn
from app.memory.engine import MemoryEngine
from app.memory.writer import MemoryWriter
from app.models.session import SessionModel
from app.orchestrator.context import build_dialogue_context
from app.orchestrator.transport import LocalTransport
from app.relationship.engine import RelationshipEngine


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
# Memory persistence test — no Pipecat dependency
# ---------------------------------------------------------------------------

async def run_memory_test(user_id: str = "test-user-001") -> dict:
    """
    Verify Phase 4 memory and relationship state end-to-end.

    Uses a fixed user_id so results persist across runs in data/memory/.
    Run twice to confirm data survives between invocations:
      - First run:  shows "First session" relationship, no user facts.
      - Second run: shows stored closeness level and any written facts.

    No Pipecat, no network, no credentials required.
    """
    engine = MemoryEngine()
    writer = MemoryWriter(engine)
    rel_engine = RelationshipEngine(engine)

    session = SessionModel(user_id=user_id)

    # --- Before: read context as-is from persistent store ---
    context_before = await build_dialogue_context(session, engine)
    prompt_before = context_before.to_system_prompt()

    # Simulate two dialogue turns with warmth and a personal fact
    await writer.process_turn(
        session_id=session.session_id,
        user_id=user_id,
        user_text="My name is Alex. I really enjoy talking with you.",
        assistant_text="It's wonderful to meet you, Alex.",
    )
    await rel_engine.apply_turn_signal(user_id=user_id, positive=True)

    await writer.process_turn(
        session_id=session.session_id,
        user_id=user_id,
        user_text="I like jazz music and I'm a software engineer.",
        assistant_text="Jazz and code — I love that combination.",
    )
    await rel_engine.apply_turn_signal(user_id=user_id, positive=True)

    # --- After: rebuild context to reflect writes ---
    context_after = await build_dialogue_context(session, engine)
    prompt_after = context_after.to_system_prompt()

    # Load final relationship state
    rel_state = await rel_engine.load_state(user_id)

    return {
        "status": "ok",
        "user_id": user_id,
        "before": {
            "relationship_summary": context_before.memory.relationship_summary,
            "user_facts": context_before.memory.user_facts,
        },
        "after": {
            "relationship_summary": context_after.memory.relationship_summary,
            "user_facts": context_after.memory.user_facts,
            "emotional_context": context_after.memory.emotional_context,
        },
        "relationship_state": {
            "closeness": rel_state.closeness.name,
            "emotional_warmth": rel_state.emotional_warmth,
            "flirtation_allowance": rel_state.flirtation_allowance,
            "nsfw_eligible": rel_state.nsfw_eligible,
        },
        "prompt_before_length": len(prompt_before),
        "prompt_after_length": len(prompt_after),
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
# Behavior and gating test — no Pipecat dependency
# ---------------------------------------------------------------------------

async def run_behavior_test() -> dict:
    """
    Verify Phase 5: behavioral instructions, NSFW gating, mood flow,
    conflict detection, and anti-repetition rules.

    Exercises the verification matrix cases directly without a real LLM.
    No Pipecat, no network, no credentials required.
    """
    from app.models.session import SessionStatus

    def _make_session(relationship_level: int, adult_mode: bool) -> SessionModel:
        return SessionModel(
            user_id=None,
            relationship_level=relationship_level,
            adult_mode=adult_mode,
            status=SessionStatus.INITIALIZING,
        )

    engine = MemoryEngine()

    # Helper: get the scene render for a given session + mood
    async def _scene_render(relationship_level: int, adult_mode: bool, mood: str = "neutral") -> str:
        session = _make_session(relationship_level, adult_mode)
        ctx = await build_dialogue_context(session, engine)
        ctx.scene.current_mood = mood
        return ctx.scene.render()

    results = {}

    # Case 1: NEW + adult false
    results["NEW_adult_false"] = await _scene_render(1, False)

    # Case 2: FAMILIAR + adult false (positive signal handled separately)
    results["FAMILIAR_adult_false"] = await _scene_render(2, False)

    # Case 3: CLOSE + heavy mood
    results["CLOSE_heavy_mood"] = await _scene_render(3, False, mood="heavy")

    # Case 4: INTIMATE + adult false
    results["INTIMATE_adult_false"] = await _scene_render(4, False)

    # Case 5: INTIMATE + adult true + nsfw_eligible true
    results["INTIMATE_adult_true"] = await _scene_render(4, True)

    # Signal detection cases
    signal_cases = {
        "leave me alone": classify_turn("leave me alone"),
        "stop it": classify_turn("stop it"),
        "please stop": classify_turn("please stop"),
        "don't do that": classify_turn("don't do that"),
        "go away": classify_turn("go away"),
        "that's not okay": classify_turn("that's not okay"),
        "thank you so much": classify_turn("thank you so much"),
        "I enjoy talking with you": classify_turn("I enjoy talking with you"),
        "how was your day": classify_turn("how was your day"),  # neutral
    }
    signal_results = {
        text: {"positive": sig.positive, "conflict": sig.conflict}
        for text, sig in signal_cases.items()
    }

    return {
        "status": "ok",
        "scene_renders": results,
        "signal_detection": signal_results,
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

    print("\n--- Memory persistence test (pure Python) ---")
    result = asyncio.run(run_memory_test())
    print(json.dumps(result, indent=2))

    print("\n--- Behavior and gating test (pure Python) ---")
    result = asyncio.run(run_behavior_test())
    print(json.dumps(result, indent=2))

    print("\n--- Fake turn test (requires pipecat-ai) ---")
    try:
        result = asyncio.run(run_fake_turn())
        print(json.dumps(result, indent=2))
    except ImportError as exc:
        print(f"Skipped: pipecat-ai not installed ({exc})")
    except Exception as exc:
        print(f"Error: {exc}")
