# Architecture Decision Log

Running log of non-obvious technical decisions made during Project Aura development.
Add an entry whenever a meaningful choice is made that is not obvious from the code.

---

## Phase 1 — 2026-04-10

### In-memory session store as Phase 1/2 default

**Decision:** `InMemorySessionStore` is the default `SessionStore` during Phase 1–2 development.

**Why:** Redis wiring is a Phase 2/3 concern and should not block repository
structure work. The `SessionStore` interface is designed so Redis can be swapped
in transparently without changing callers.

**Constraint:** `InMemorySessionStore` does not persist across process restarts
and does not work in multi-process deployments. Switch to `RedisSessionStore`
before any Modal deployment or multi-instance testing.

---

### Pipecat chosen for real-time orchestration

**Decision:** Target Pipecat as the primary real-time voice pipeline orchestration library.

**Why:** Defined in `ARCHITECTURE.md`. Pipecat provides a Python-native streaming
pipeline model compatible with Modal deployment and STT→LLM→TTS chaining.

**Status:** Pipecat integration is stubbed — not yet implemented. Wire in Phase 3.

---

### Frontend framework deferred

**Decision:** Frontend is plain HTML/CSS/JS for Phase 1. No build framework selected yet.

**Why:** Framework choice (Vite + React, etc.) is not critical for Phase 1 scaffolding.
The placeholder works as-is and can be upgraded when real-time audio streaming
requirements (Phase 3) make a framework necessary.

**Constraint:** If WebRTC library size or state complexity grows significantly,
migrate to a proper framework before Phase 3 is complete.

---

### One canonical live voice path

**Decision:** `LiveVoiceRenderer` in `app/voice/renderer.py` is the single live voice
path. No additional TTS transformation layers may be added to the live path without
explicit justification.

**Why:** Per `ARCHITECTURE.md §10.3`. Extra layers risk latency regression,
consistency loss, and artifact introduction. Offline enrichment is always preferred
over live-path complexity.

---

## Open Decisions (not yet resolved)

| Decision | Options | Status |
|---|---|---|
| STT provider | Deepgram, Whisper variants | Not selected |
| LLM provider | Anthropic, OpenAI | Not selected |
| TTS / voice provider | ElevenLabs, Cartesia | Not selected |
| Persistent memory store | Supabase, Postgres, SQLite | Not selected |
| Frontend framework | Vite + React, plain JS | Deferred |
