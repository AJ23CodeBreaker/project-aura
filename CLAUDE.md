# CLAUDE.md — Project Aura Working Rules

## 1. Purpose

This file defines the working rules for Claude Code inside the Project Aura repository.

Project Aura is a private-test, voice-first, relationship-based adult AI companion prototype.

The objective is not to build a generic chatbot.
The objective is to build a prototype that feels emotionally believable, remembers prior history, and supports gradual intimacy progression over time.

Claude Code must treat this repository as a focused prototype build, not as a place for uncontrolled experimentation.

---

## 2. Required Reading Before Major Work

Before making major code changes, always read:

- `PRD.md`
- `ARCHITECTURE.md`
- `TASKS.md`
- `CLAUDE.md`

Do not proceed with large implementation work unless these files have been reviewed in the current session.

---

## 3. Core Product Principle

The most important principle in this project is:

**Believability is more important than technical complexity.**

When tradeoffs occur, prefer:

- consistency over cleverness
- emotional continuity over feature count
- stable voice behavior over experimental layering
- selective memory over full transcript storage
- gradual intimacy over instant explicitness
- clean architecture over rushed integration

---

## 4. Scope Discipline

This repository is for a prototype.

Do not expand scope casually.

Do not introduce major new systems unless they are clearly necessary for one of these goals:

- real-time voice conversation
- companion realism
- selective memory
- relationship continuity
- actress-based voice identity
- gradual intimacy progression
- private-test usability

Avoid product drift.

---

## 5. Phase-Based Work Rule

Always work phase by phase according to `TASKS.md`.

Rules:
1. Do not skip ahead unless explicitly instructed.
2. Do not mix unfinished future-phase work into the current phase without clear need.
3. Complete the current scaffold cleanly before adding extra complexity.
4. After each phase, summarize:
   - what was created
   - what remains stubbed
   - what should be done next

---

## 6. Architecture Discipline

Follow `ARCHITECTURE.md`.

### 6.1 Frontend / Backend Separation
- Netlify hosts the frontend UI.
- Sensitive logic belongs in backend services.
- Do not put provider secrets in frontend code.
- Do not let browser code directly own sensitive orchestration logic.

### 6.2 Canonical Live Voice Path
- Keep one primary live voice path in v1.
- Do not stack multiple live voice-transformation systems unless explicitly requested and justified.
- Offline voice experiments belong outside the real-time path.

### 6.3 Memory Discipline
- Treat memory as selective structured data.
- Do not rely on full raw transcript dumping as the main memory strategy.
- Distinguish between session memory, semantic user memory, relationship memory, and episodic memory.

### 6.4 Relationship Discipline
- Intimacy must be state-driven.
- NSFW is not a default mode.
- Relationship progression must feel gradual and contextual.
- Avoid abrupt, mechanical, or repetitive escalation.

---

## 7. Coding Rules

### 7.1 General
- Write modular, readable, reviewable code.
- Prefer small interfaces and clear boundaries.
- Use replaceable adapters for external providers.
- Keep naming consistent and explicit.
- Avoid hidden magic behavior.

### 7.2 Honesty Rule
- Do not pretend integrations are complete when they are not.
- Do not invent APIs.
- Do not fabricate provider behavior.
- If a component is uncertain, stub it clearly and document assumptions.

### 7.3 Simplicity Rule
- Start with the simplest implementation that respects the architecture.
- Only add complexity when it solves a real problem.
- Avoid premature optimization.
- Avoid infrastructure sprawl.

### 7.4 Reviewability Rule
- Keep files organized and easy to inspect.
- Add comments only where they help understanding.
- Do not bury key assumptions inside code without explaining them.

---

## 8. Real-Time Conversation Rules

The product is voice-first and conversation-first.

Therefore:

- favor spoken-style responses over essay-like text
- design for short, natural turns
- support interruption and turn-taking
- reduce robotic pacing
- preserve emotional continuity across turns
- avoid overly formal or overly verbose responses

The system should feel like a person in conversation, not a support bot.

---

## 9. Memory Rules

Memory should improve attachment and continuity.

### Store selectively
Prefer storing:
- user preferences
- important facts the user shared
- meaningful shared moments
- relationship milestones
- unresolved threads
- emotional patterns
- promises and callbacks

### Avoid over-saving
Do not automatically save:
- every user sentence
- every assistant sentence
- trivial filler turns
- repetitive low-value details

### Retrieval goal
Memory retrieval should help the companion:
- remember who the user is
- remember what matters
- feel consistent across sessions
- bring back emotionally meaningful prior moments naturally

---

## 10. Relationship and Intimacy Rules

Project Aura is a relationship-based adult prototype.

This means:

- affection should emerge through continuity
- flirtation should be contextual
- intimacy should reflect relationship state
- NSFW behavior should only appear when session configuration and relationship state support it
- escalation must not feel instant, cheap, or disconnected

Avoid:
- repetitive pet names
- copy-paste affection loops
- mechanical explicit phrasing
- abrupt jumps from neutral to sexual
- behavior that makes the companion feel fake or scripted

---

## 11. Voice Rules

Voice quality is central to immersion.

Rules:
- preserve one stable live voice architecture in v1
- do not add extra live voice layers casually
- prefer consistency and low artifact risk
- separate offline voice experimentation from the main runtime path
- design for future asset enrichment if needed

The system does not succeed just because the voice is attractive.
The voice must also feel stable, natural, and emotionally aligned with the dialogue.

---

## 12. Frontend Rules

The frontend should remain clean and lightweight.

It should:
- manage session start/end
- show connection and interaction state
- handle browser-side audio controls
- call backend/bootstrap endpoints safely

It should not:
- contain secret provider keys
- own core memory logic
- own core orchestration logic
- become overloaded with backend behavior

---

## 13. Backend Rules

The backend is the authoritative runtime layer.

It should:
- manage orchestration
- manage memory retrieval and writes
- manage relationship-state logic
- manage provider adapters
- manage session flow
- keep observability hooks for debugging realism and latency

Backend components should be clearly separated by responsibility.

---

## 14. Documentation Rules

When making meaningful structural changes:

- keep `README.md` updated
- keep assumptions visible
- keep placeholders clearly labeled
- do not leave confusing unfinished structure without explanation

If architecture changes materially, update the relevant documentation.
If project documents and implementation assumptions conflict, stop and explain the conflict before making a major architecture change.

---

## 15. What Not to Do

Do not:

- build the whole product in one jump
- overcomplicate the live voice path
- introduce unnecessary providers
- store raw transcripts as the primary memory model
- claim realism without implementing continuity
- treat NSFW as a keyword-triggered mode
- optimize for theoretical perfection before the prototype works
- silently change architecture without explanation

---

## 16. Expected Working Output Format

After a meaningful implementation task, provide:

### Completed
- files created or updated
- key modules added
- working scaffolds or implemented behavior

### Stubbed / Pending
- provider integrations not finished
- placeholder logic
- known missing pieces

### Assumptions
- anything inferred during implementation
- any unresolved technical choice
- any recommended next decision

### Next Step
- the most logical next build action based on `TASKS.md`

---

## 17. First Build Priority

The first priority is not advanced realism tuning.

The first priority is to establish:

- a clean repository structure
- safe config boundaries
- frontend/backend separation
- replaceable adapters
- a buildable real-time pipeline skeleton
- a clean memory foundation

Only after that should deeper realism and intimacy behavior be added.

---

## 18. Final Instruction

Build Project Aura like a disciplined prototype.

Do not chase maximum complexity.
Do not improvise around the core product goal.

Always preserve the central aim:

**Create a voice-first companion that feels emotionally real, remembers shared history, and supports gradual intimacy progression in a believable way.**