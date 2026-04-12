"""
Project Aura — Prototype Evaluation Harness

Runs through the Phase 5 verification matrix, Phase 4 memory persistence
checks, and (if ANTHROPIC_API_KEY is set) one real LLM dialogue turn.

Usage:
    python scripts/evaluate.py

Output: structured pass/fail report. No external dependencies beyond
what is already installed; Anthropic section skipped if key not present.
"""
import asyncio
import os
import sys

# Allow running from the project root without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dialogue.signals import classify_turn
from app.memory.engine import MemoryEngine
from app.memory.store import InMemorySessionMemoryStore, JsonFileMemoryStore
from app.models.relationship import ClosenessLevel
from app.models.session import SessionModel
from app.orchestrator.context import build_dialogue_context
from app.orchestrator.scene import EscalationPace, SessionController


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

_pass = 0
_fail = 0


def _check(label: str, condition: bool, detail: str = "") -> bool:
    global _pass, _fail
    status = "PASS" if condition else "FAIL"
    suffix = f"  ({detail})" if detail and not condition else ""
    print(f"  [{status}] {label}{suffix}")
    if condition:
        _pass += 1
    else:
        _fail += 1
    return condition


def _section(title: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# Section 1: Signal detection
# ---------------------------------------------------------------------------

def evaluate_signals() -> None:
    _section("Signal Detection (Phase 5)")

    conflict_cases = [
        "leave me alone",
        "stop it",
        "please stop",
        "go away",
        "don't do that",
        "that's not okay",
    ]
    for phrase in conflict_cases:
        s = classify_turn(phrase)
        _check(f'conflict: "{phrase}"', s.conflict and not s.positive)

    positive_cases = [
        "thank you so much",
        "I enjoy talking with you",
        "I love chatting with you",
    ]
    for phrase in positive_cases:
        s = classify_turn(phrase)
        _check(f'positive: "{phrase}"', s.positive and not s.conflict)

    neutral_cases = ["how was your day", "I went to the store"]
    for phrase in neutral_cases:
        s = classify_turn(phrase)
        _check(f'neutral: "{phrase}"', not s.positive and not s.conflict)

    s = classify_turn("I love you but please stop")
    _check("conflict beats positive in same message", s.conflict and not s.positive)


# ---------------------------------------------------------------------------
# Section 2: NSFW gate and scene rendering
# ---------------------------------------------------------------------------

def _make_scene(level: int, adult: bool, mood: str = "neutral") -> SessionController:
    from app.orchestrator.scene import EscalationPace
    nsfw_eligible = level >= int(ClosenessLevel.INTIMATE)
    return SessionController(
        closeness=ClosenessLevel(level),
        adult_enabled=adult,
        nsfw_eligible=nsfw_eligible,
        current_mood=mood,
        escalation_pace=EscalationPace.HOLD,
        current_topic=None,
    )


def evaluate_scene() -> None:
    _section("Scene Rendering and NSFW Gate (Phase 5)")

    cases = [
        (1, False, "neutral", "NEW + adult false → gate fails"),
        (2, False, "neutral", "FAMILIAR + adult false → gate fails"),
        (3, False, "heavy",  "CLOSE + heavy mood → gate fails + mood line"),
        (4, False, "neutral", "INTIMATE + adult false → gate fails"),
        (4, True,  "neutral", "INTIMATE + adult true → gate PASSES"),
    ]

    for level, adult, mood, label in cases:
        scene = _make_scene(level, adult, mood)
        rendered = scene.render()

        if level == 4 and adult:
            # Gate should PASS
            _check(label, "Adult content: enabled" in rendered, rendered[:80])
            _check(f"  > 'unprompted' guard present", "unprompted" in rendered)
        else:
            # Gate should FAIL
            _check(label, "not permitted" in rendered, rendered[:80])

        if mood == "heavy":
            _check("  > heavy mood renders grounding instruction", "grounding" in rendered.lower())


# ---------------------------------------------------------------------------
# Section 3: Context assembly (mood flow, escalation pace)
# ---------------------------------------------------------------------------

async def evaluate_context() -> None:
    _section("Context Assembly (Phase 5)")

    engine = MemoryEngine(
        session_store=InMemorySessionMemoryStore(),
        persistent_store=JsonFileMemoryStore(),
    )

    from app.models.memory import SessionMemory

    session = SessionModel(user_id="eval-user")
    await engine.write_session_memory(
        SessionMemory(session_id=session.session_id, emotional_tone="playful")
    )
    ctx = await build_dialogue_context(session, engine)
    _check("Mood flows from session memory into scene", ctx.scene.current_mood == "playful")

    session_i = SessionModel(relationship_level=4, adult_mode=True)
    ctx_i = await build_dialogue_context(session_i, engine)
    _check("Escalation INCREASE at INTIMATE + adult", ctx_i.scene.escalation_pace == EscalationPace.INCREASE)

    session_n = SessionModel(relationship_level=1, adult_mode=True)
    ctx_n = await build_dialogue_context(session_n, engine)
    _check("Escalation HOLD at NEW (even with adult=True)", ctx_n.scene.escalation_pace == EscalationPace.HOLD)

    prompt = ctx_i.to_system_prompt()
    _check("System prompt is non-empty", len(prompt) > 200)
    _check("System prompt contains identity (Aura)", "Aura" in prompt)
    _check("System prompt contains NSFW gate text", "not permitted" in prompt or "enabled" in prompt)


# ---------------------------------------------------------------------------
# Section 4: Memory persistence (Phase 4)
# ---------------------------------------------------------------------------

async def evaluate_memory() -> None:
    _section("Memory Persistence (Phase 4)")

    engine = MemoryEngine(
        session_store=InMemorySessionMemoryStore(),
        persistent_store=JsonFileMemoryStore(),
    )

    from app.memory.writer import MemoryWriter
    from app.relationship.engine import RelationshipEngine

    import uuid
    user_id = f"eval-memory-{uuid.uuid4().hex[:8]}"
    writer = MemoryWriter(engine)
    rel_engine = RelationshipEngine(engine)

    ctx_before = await build_dialogue_context(SessionModel(user_id=user_id), engine)
    _check("New user: no prior facts", ctx_before.memory.user_facts == {})
    _check('New user: relationship says "First session"', "First session" in ctx_before.memory.relationship_summary)

    await writer.process_turn(
        session_id="eval-sess",
        user_id=user_id,
        user_text="My name is Sam. I really enjoy talking with you.",
        assistant_text="Great to meet you, Sam.",
    )
    await rel_engine.apply_turn_signal(user_id=user_id, positive=True)

    ctx_after = await build_dialogue_context(SessionModel(user_id=user_id), engine)
    _check("After turn: personal fact stored (name=Sam)", ctx_after.memory.user_facts.get("name") == "Sam")
    _check("After turn: relationship summary updated", "First session" not in ctx_after.memory.relationship_summary)


# ---------------------------------------------------------------------------
# Section 5: Optional real LLM dialogue turn (Anthropic)
# ---------------------------------------------------------------------------

async def evaluate_real_llm() -> None:
    _section("Real LLM Dialogue (Anthropic — optional)")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [SKIP] ANTHROPIC_API_KEY not set — skipping real LLM test.")
        print("         Set it in .env and re-run to test actual dialogue quality.")
        return

    try:
        from app.adapters.anthropic_llm import AnthropicDialogueAdapter
    except ImportError as exc:
        print(f"  [SKIP] anthropic package not installed: {exc}")
        print("         Run: pip install anthropic")
        return

    try:
        adapter = AnthropicDialogueAdapter(api_key=api_key)
    except ImportError as exc:
        print(f"  [SKIP] anthropic package not installed: {exc}")
        print("         Run: pip install anthropic")
        return

    try:
        engine = MemoryEngine(
            session_store=InMemorySessionMemoryStore(),
            persistent_store=JsonFileMemoryStore(),
        )
        session = SessionModel(relationship_level=2, adult_mode=False)
        ctx = await build_dialogue_context(session, engine)
        system_prompt = ctx.to_system_prompt()

        chunks = []
        async for chunk in adapter.generate(
            system_prompt=system_prompt,
            conversation_history=[],
            user_message="Hey, how are you today?",
        ):
            chunks.append(chunk)
        await adapter.close()

        response = "".join(chunks).strip()
        _check("Real LLM: response is non-empty", len(response) > 0)
        _check("Real LLM: response under 400 chars (spoken length)", len(response) < 400, f"len={len(response)}")
        print(f"\n  Response: {response!r}\n")

    except Exception as exc:
        print(f"  [FAIL] Real LLM test raised: {exc}")
        global _fail
        _fail += 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    print("\n" + "=" * 60)
    print("  Project Aura — Prototype Evaluation Report")
    print("=" * 60)

    evaluate_signals()
    evaluate_scene()
    await evaluate_context()
    await evaluate_memory()
    await evaluate_real_llm()

    print(f"\n{'=' * 60}")
    total = _pass + _fail
    print(f"  Results: {_pass}/{total} passed  |  {_fail} failed")
    print("=" * 60 + "\n")
    sys.exit(0 if _fail == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
