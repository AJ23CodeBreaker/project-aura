"""
Dialogue Runner — text-in / text-out turn execution.

Factored out of DialoguePipelineService so the HTTP /turn endpoint can call
one LLM turn directly, without going through the Pipecat audio pipeline.

This module provides:
  run_text_turn()       — execute one turn, return assistant text as a string
  clear_session_history() — remove history for a session (call on session end)

History is kept in a module-level dict keyed by session_id. It is in-memory
only and session-scoped — not persisted across process restarts. This matches
the rolling-buffer behaviour inside DialoguePipelineService.
"""
from typing import Dict, List, Optional

from app.adapters.llm import DialogueAdapter, StubDialogueAdapter
from app.dialogue.signals import classify_turn
from app.memory.engine import MemoryEngine
from app.memory.writer import MemoryWriter
from app.models.session import SessionModel
from app.orchestrator.context import HISTORY_MAX_TURNS, build_dialogue_context
from app.relationship.engine import RelationshipEngine

# Rolling in-memory history per session.
# Each entry: {"role": "user" | "assistant", "text": str}
_session_histories: Dict[str, List[dict]] = {}


async def run_text_turn(
    session: SessionModel,
    user_text: str,
    engine: MemoryEngine,
    adapter: Optional[DialogueAdapter] = None,
) -> str:
    """
    Execute one text dialogue turn for the given session.

    Builds the three-layer system prompt, calls adapter.generate(), updates
    the in-memory rolling history, runs selective memory writes, and applies
    the relationship signal for the turn.

    Returns the full assistant response as a single string.
    """
    _adapter = adapter or StubDialogueAdapter()
    session_id = session.session_id

    # Build three-layer context (identity + memory + scene)
    history = list(_session_histories.get(session_id, []))
    context = await build_dialogue_context(session, engine)
    system_prompt = context.to_system_prompt()

    # Single LLM call — collect streamed chunks
    chunks: List[str] = []
    async for chunk in _adapter.generate(
        system_prompt=system_prompt,
        conversation_history=history,
        user_message=user_text,
    ):
        chunks.append(chunk)

    assistant_text = "".join(chunks)

    # Update rolling history, capped at HISTORY_MAX_TURNS total entries
    history.append({"role": "user", "text": user_text})
    history.append({"role": "assistant", "text": assistant_text})
    if len(history) > HISTORY_MAX_TURNS:
        history = history[-HISTORY_MAX_TURNS:]
    _session_histories[session_id] = history

    # Selective memory write (MemoryWriter skips anonymous/None user_id internally)
    writer = MemoryWriter(engine)
    await writer.process_turn(
        session_id=session_id,
        user_id=session.user_id,
        user_text=user_text,
        assistant_text=assistant_text,
    )

    # Relationship signal — only for identified, non-anonymous users
    user_id = session.user_id
    if user_id and user_id != "anonymous":
        signal = classify_turn(user_text)
        if signal.conflict or signal.positive:
            rel_engine = RelationshipEngine(engine)
            await rel_engine.apply_turn_signal(
                user_id=user_id,
                positive=signal.positive,
                conflict=signal.conflict,
            )

    return assistant_text


def clear_session_history(session_id: str) -> None:
    """
    Remove the in-memory turn history for a session.

    Called from the /session/{id}/end endpoint so memory is not held
    indefinitely. Safe to call for a session that has no history.
    """
    _session_histories.pop(session_id, None)
