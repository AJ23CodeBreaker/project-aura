"""
Dialogue context assembly — three-layer system prompt builder

Assembles Layer 1 (Identity), Layer 2 (Memory), and Layer 3 (Scene)
into a single DialogueContext per turn.

DialogueContext.to_system_prompt() produces one string passed to the
dialogue adapter. There is ONE LLM call per user turn — not one per layer.

--- Conversation history definition (Phase 3) ---

History is a minimal in-session rolling buffer. It is:
  - Format:  List[dict] with keys "role" ("user" | "assistant") and "text" (str)
  - Scope:   current session only — starts empty, not persisted across sessions
  - Size:    capped at HISTORY_MAX_TURNS (6 entries = 3 user + 3 assistant turns)
  - Owner:   DialoguePipelineService maintains it in memory during the session
  - Phase 4: real retrieved episodes may be surfaced via Layer 2 (memory block),
             but the history format and size cap remain unchanged here

This is NOT a full transcript system. It is a short coherence window.

--- Layer 2 source ---

Layer 2 is served by app.memory.retrieval.build_context(), which already
returns an empty MemoryContext stub. Phase 4 replaces build_context()'s
body without changing any interface here.
"""
from dataclasses import dataclass
from typing import List

from app.memory.engine import MemoryEngine
from app.memory.retrieval import MemoryContext, build_context
from app.models.session import SessionModel
from app.orchestrator.identity import CompanionIdentity, DEFAULT_IDENTITY
from app.orchestrator.scene import SessionController

# Maximum entries in the in-session history buffer.
# 6 = 3 user turns + 3 assistant turns. Keeps context lean for low latency.
HISTORY_MAX_TURNS = 6


@dataclass
class DialogueContext:
    """
    The complete per-turn context package.

    Passed to DialogueContext.to_system_prompt() to produce the single
    string given to DialogueAdapter.generate().
    """
    identity: CompanionIdentity   # Layer 1 — static companion persona
    memory: MemoryContext         # Layer 2 — relationship/memory retrieval (stub)
    scene: SessionController      # Layer 3 — runtime session control block

    def to_system_prompt(self) -> str:
        """
        Assemble all three layers into one system prompt string.

        Layer ordering: Identity → Memory context → Scene controller.

        Memory block is omitted when empty (Phase 3 default) to keep the
        prompt compact. Scene block is always included.
        """
        parts: List[str] = []

        # Layer 1: identity (always present)
        parts.append(self.identity.render())

        # Layer 2: memory context — only emit non-empty, non-stub fields
        memory_lines: List[str] = []
        if self.memory.user_facts:
            facts = "; ".join(f"{k}: {v}" for k, v in self.memory.user_facts.items())
            memory_lines.append(f"What you know about them: {facts}")
        if (
            self.memory.relationship_summary
            and not self.memory.relationship_summary.startswith("[no ")
        ):
            memory_lines.append(f"Relationship context: {self.memory.relationship_summary}")
        if self.memory.notable_episodes:
            memory_lines.append(
                "Shared moments: " + "; ".join(self.memory.notable_episodes)
            )
        if self.memory.emotional_context and self.memory.emotional_context != "neutral":
            memory_lines.append(f"Emotional context: {self.memory.emotional_context}")
        if memory_lines:
            parts.append("\n".join(memory_lines))

        # Layer 3: scene controller (always present, always compact)
        parts.append(self.scene.render())

        return "\n\n".join(parts)


async def build_dialogue_context(
    session: SessionModel,
    engine: MemoryEngine,
) -> DialogueContext:
    """
    Assemble the full dialogue context for one turn.

    Called once per turn, before the single LLM call.

    Layer 1: DEFAULT_IDENTITY — static, same for every session.
    Layer 2: build_context() — currently returns empty stubs; Phase 4 wires real retrieval.
    Layer 3: SessionController.from_session() — built from live session state.
    """
    # Layer 2: memory retrieval (stub in Phase 3 — returns empty MemoryContext)
    user_id = session.user_id or "anonymous"
    memory = await build_context(engine, user_id, session.session_id)

    # Layer 3: session / scene controller
    scene = SessionController.from_session(session)

    return DialogueContext(
        identity=DEFAULT_IDENTITY,
        memory=memory,
        scene=scene,
    )
