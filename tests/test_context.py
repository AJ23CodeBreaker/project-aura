"""
Tests for app.orchestrator.context — three-layer dialogue context assembly.

Verifies that build_dialogue_context() correctly assembles identity, memory,
and scene layers, and that Phase 5 wiring (mood flow, escalation pace) works.
"""
import pytest

from app.models.memory import SessionMemory
from app.models.session import SessionModel
from app.orchestrator.context import build_dialogue_context
from app.orchestrator.scene import EscalationPace


async def test_returns_all_three_layers(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    assert ctx.identity is not None
    assert ctx.memory is not None
    assert ctx.scene is not None


async def test_identity_name_is_aura(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    assert ctx.identity.name == "Aura"


async def test_system_prompt_is_non_empty_string(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    prompt = ctx.to_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 200


async def test_system_prompt_contains_identity_text(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    prompt = ctx.to_system_prompt()
    assert "Aura" in prompt


async def test_system_prompt_contains_nsfw_gate_text(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    prompt = ctx.to_system_prompt()
    # Gate text always present — one of two outcomes
    assert "not permitted" in prompt or "Adult content: enabled" in prompt


async def test_mood_flows_from_session_memory(engine):
    session = SessionModel(user_id="test-user")
    await engine.write_session_memory(
        SessionMemory(session_id=session.session_id, emotional_tone="heavy")
    )
    ctx = await build_dialogue_context(session, engine)
    assert ctx.scene.current_mood == "heavy"


async def test_neutral_mood_when_no_session_memory(engine):
    session = SessionModel()
    ctx = await build_dialogue_context(session, engine)
    assert ctx.scene.current_mood == "neutral"


async def test_escalation_increase_at_intimate_adult(engine):
    session = SessionModel(relationship_level=4, adult_mode=True)
    ctx = await build_dialogue_context(session, engine)
    assert ctx.scene.escalation_pace == EscalationPace.INCREASE


async def test_escalation_hold_when_not_intimate(engine):
    # adult_mode=True but only NEW level — nsfw_eligible=False → HOLD
    session = SessionModel(relationship_level=1, adult_mode=True)
    ctx = await build_dialogue_context(session, engine)
    assert ctx.scene.escalation_pace == EscalationPace.HOLD


async def test_escalation_hold_when_intimate_but_adult_disabled(engine):
    session = SessionModel(relationship_level=4, adult_mode=False)
    ctx = await build_dialogue_context(session, engine)
    assert ctx.scene.escalation_pace == EscalationPace.HOLD
