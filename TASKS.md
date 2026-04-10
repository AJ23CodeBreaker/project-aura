# Project Aura — Build Tasks and Delivery Plan

## 1. Purpose

This document translates the product and architecture documents into a practical execution plan for Claude Code.

The purpose of this file is to:

- define the implementation phases
- sequence work in a buildable order
- prevent architecture drift
- ensure the prototype is developed toward believability, continuity, and real-time usability
- keep the first version focused

This is a prototype plan, not a public production rollout plan.

---

## 2. Execution Rules

Claude Code must follow these rules during implementation:

1. Work phase by phase.
2. Do not skip ahead unless explicitly instructed.
3. Do not mark unfinished integrations as complete.
4. Stub unknown or uncertain provider integrations clearly.
5. Prefer a working skeleton over fake completeness.
6. Keep the live voice path simple.
7. Keep the frontend and backend separated.
8. Implement memory in structured, selective form.
9. Do not use full raw transcript retention as the primary memory strategy.
10. Treat intimacy and NSFW logic as relationship-state-driven behavior.

---

## 3. High-Level Build Roadmap

Project Aura will be built in 6 major phases:

- Phase 1 — Repository skeleton and configuration foundation
- Phase 2 — Frontend and backend baseline wiring
- Phase 3 — Real-time voice pipeline skeleton
- Phase 4 — Memory and relationship-state implementation
- Phase 5 — Companion behavior and intimacy progression
- Phase 6 — Testing, tuning, and prototype hardening

Each phase should produce a reviewable milestone.

---

## 4. Phase 1 — Repository Skeleton and Configuration Foundation

## 4.1 Goals

Create a clean project structure and prepare the repo for phased implementation.

## 4.2 Deliverables

- initialize core folder structure
- create backend service modules
- create frontend app skeleton placeholder
- create environment/config templates
- create basic README guidance
- establish interfaces for:
  - frontend
  - orchestration
  - memory
  - relationship state
  - voice
- create placeholder files for future implementation

## 4.3 Required Tasks

### Backend structure
Create initial backend-oriented directories such as:
- `app/`
- `services/`
- `scripts/`
- `docs/`

Suggested substructure:
- `app/api/`
- `app/core/`
- `app/models/`
- `app/adapters/`
- `app/state/`
- `app/memory/`
- `app/voice/`
- `app/session/`
- `app/config/`

### Frontend placeholder
Create a simple frontend placeholder structure for the future Netlify UI.
If frontend framework choice is not finalized, create a minimal placeholder and note assumptions.

### Environment and config
Create:
- `.env.example`
- config loader stubs
- settings template
- safe separation of frontend/public config vs backend/secret config

### Documentation
Update `README.md` with:
- project purpose
- repo overview
- setup notes
- phase status section

## 4.4 Acceptance Criteria

Phase 1 is complete when:
- the repo is clearly structured
- placeholder modules exist
- no fake provider completion is claimed
- config boundaries are documented
- the project is ready for actual implementation work

---

## 5. Phase 2 — Frontend and Backend Baseline Wiring

## 5.1 Goals

Establish the first browser-to-backend connection structure for the Netlify-hosted UI and the Modal-hosted backend.

## 5.2 Deliverables

- basic frontend shell
- session start UI
- session status UI
- backend bootstrap endpoint
- initial session creation flow
- temporary session state initialization

## 5.3 Required Tasks

### Frontend
Implement a minimal browser UI that can:
- display prototype status
- start a test session
- end a session
- show connection state
- show listening / speaking / idle state placeholders

### Backend
Implement an initial bootstrap/session endpoint that can:
- create a session ID
- initialize temporary session state
- return safe session metadata to the frontend
- support future real-time transport integration

### Session State
Store minimal runtime session state in Redis or a stub abstraction if Redis wiring is not yet ready.
If Redis is not yet integrated, use a clearly labeled in-memory session store stub.

Session state should include:
- session ID
- created timestamp
- current status
- relationship-state placeholder
- recent activity placeholder

## 5.4 Acceptance Criteria

Phase 2 is complete when:
- frontend can contact backend successfully
- a session can be created
- session state is initialized
- there is a visible end-to-end browser-to-backend flow

---

## 6. Phase 3 — Real-Time Voice Pipeline Skeleton

## 6.1 Goals

Create the first real-time voice pipeline structure without overcomplicating the live path.

## 6.2 Deliverables

- Pipecat-oriented orchestration skeleton
- audio input/output pathway design
- STT adapter interface
- LLM dialogue adapter interface
- TTS/live voice adapter interface
- per-turn orchestration flow
- latency instrumentation placeholders

## 6.3 Required Tasks

### Transport and orchestration
Create the structure for:
- session transport
- user audio ingestion
- turn detection / end-of-turn handling
- backend response streaming

### STT adapter
Create an adapter interface for STT that supports:
- partial transcripts if available
- final transcript output
- interruption-aware behavior

### Dialogue adapter
Create an adapter interface for the conversational model that supports:
- system persona injection
- memory injection
- relationship-state injection
- spoken-style response generation

### Voice adapter
Create a canonical live voice interface for:
- speech rendering
- streaming output
- timing/pacing hooks
- optional emotional style controls

### Logging
Track:
- STT latency
- LLM latency
- TTS latency
- first-audio latency

## 6.4 Acceptance Criteria

Phase 3 is complete when:
- the live pipeline skeleton exists
- interfaces are defined cleanly
- provider implementations are either real or clearly stubbed
- the system is ready for real provider integration

---

## 7. Phase 4 — Memory and Relationship-State Implementation

## 7.1 Goals

Implement selective memory and relationship continuity.

## 7.2 Deliverables

- session memory store
- semantic user memory model
- relationship memory model
- episodic memory model
- memory retrieval pipeline
- selective memory writing logic
- relationship-state engine

## 7.3 Required Tasks

### Memory schema
Create structured memory models for:
- session memory
- user semantic memory
- relationship memory
- episodic memory

### Memory retrieval
Implement a retrieval step before response generation that can gather:
- user preferences
- relationship closeness
- unresolved threads
- notable past moments
- recent emotional context

### Memory writing
Implement selective write logic that stores only meaningful information, such as:
- preferences
- relationship milestones
- emotionally important moments
- recurring topics
- promises or callbacks

Do not write every turn by default.

### Relationship-state engine
Implement a relationship-state service that:
- tracks closeness
- tracks emotional warmth
- supports progression and regression
- influences tone and intimacy gating
- does not behave like a simple one-way unlock ladder

## 7.4 Acceptance Criteria

Phase 4 is complete when:
- memory retrieval works
- memory writes are selective
- relationship state persists across sessions
- the companion can reference prior history in a structured way

---

## 8. Phase 5 — Companion Behavior and Intimacy Progression

## 8.1 Goals

Make the companion feel less robotic and more relationally believable.

## 8.2 Deliverables

- spoken-style dialogue behavior rules
- emotional warmth tuning hooks
- flirtation gating
- intimacy progression model
- NSFW eligibility logic for adult-enabled testing
- safer configuration switches for adult-enabled vs adult-disabled sessions

## 8.3 Required Tasks

### Dialogue behavior shaping
Implement response shaping to favor:
- spoken naturalness
- shorter and varied replies
- callbacks
- playful tone when appropriate
- non-essay response style
- emotional responsiveness

### Relationship-driven intimacy
Implement state-aware logic so that:
- flirtation emerges gradually
- affection varies by closeness and context
- NSFW is not default
- explicit content requires relationship and situational support

### Session controls
Create configurable flags for:
- adult-enabled test sessions
- adult-disabled sessions
- adjustable intimacy thresholds
- adjustable tone profile

### Repetition controls
Reduce robotic feel by avoiding:
- repeated pet names
- repeated affection templates
- repetitive explicit phrasing
- overuse of scripted reassurance

## 8.4 Acceptance Criteria

Phase 5 is complete when:
- the companion feels more personalized
- tone changes reflect relationship state
- flirtation and adult escalation are not mechanical
- the experience is meaningfully less robotic than a generic assistant

---

## 9. Phase 6 — Testing, Tuning, and Prototype Hardening

## 9.1 Goals

Evaluate the prototype and improve realism, continuity, and stability.

## 9.2 Deliverables

- internal test checklist
- latency review
- memory quality review
- realism evaluation notes
- voice quality review
- defect tracking notes
- prioritized improvement list

## 9.3 Required Tasks

### Functional testing
Test:
- session start/end
- audio path behavior
- memory persistence
- relationship-state carryover
- interrupt handling
- reconnect behavior

### Realism testing
Evaluate:
- emotional warmth
- memory usefulness
- repetition level
- flirtation timing
- intimacy pacing
- voice attractiveness
- robotic-feeling reduction

### Performance testing
Review:
- first-audio latency
- transcription speed
- response speed
- transport stability
- backend reliability

### Improvement logging
Document:
- what feels fake
- what breaks immersion
- where memory helps
- where intimacy progression fails
- where voice realism is insufficient

## 9.4 Acceptance Criteria

Phase 6 is complete when:
- the prototype is stable enough for repeated private demos/tests
- major realism failures are documented
- next-iteration priorities are clear

---

## 10. Stretch Work (Optional After Core Prototype)

These tasks are optional and should not block the core prototype:

- richer emotional voice asset expansion
- advanced relationship-state tuning
- more sophisticated voice style controls
- improved memory ranking/retrieval
- graph-based relationship memory
- multiple companion personas
- long-session summarization improvements
- advanced UI polish
- analytics dashboards

---

## 11. Explicit Non-Tasks for Early Phases

The following should not distract early implementation:

- public launch preparation
- payments or subscription logic
- mobile packaging
- community features
- large-scale scaling work
- over-engineered graph architecture
- unnecessary multi-provider complexity in the live path
- trying to perfect every emotional mode before the basic system works

---

## 12. Claude Code Working Style

When implementing, Claude Code must:

1. Read `PRD.md`, `ARCHITECTURE.md`, `TASKS.md`, and `CLAUDE.md` first.
2. Work only on the current requested phase.
3. State assumptions clearly.
4. Create replaceable adapter interfaces.
5. Prefer working scaffolds over fake completion.
6. Keep code modular and easy to review.
7. Summarize completed work after each phase.
8. List remaining stubs explicitly.
9. Avoid architecture changes unless clearly justified.
10. Preserve the principle that believability matters more than complexity.

---

## 13. Suggested First Claude Prompt

After all project docs are completed, the first build prompt should be:

Read `PRD.md`, `ARCHITECTURE.md`, `TASKS.md`, and `CLAUDE.md` first.

Work only on Phase 1 from `TASKS.md`.

Your goals:
1. initialize the repository structure
2. create backend module placeholders
3. create a frontend placeholder for the future Netlify UI
4. add configuration and environment templates
5. update `README.md`
6. do not implement advanced provider logic yet
7. clearly mark all stubs and assumptions

At the end, summarize:
- what was created
- what remains stubbed
- what should be done next

---

## 14. Summary

This task plan exists to keep Project Aura buildable.

It ensures that development proceeds from:
- structure
- to connectivity
- to real-time pipeline
- to memory
- to relationship realism
- to intimacy behavior
- to tuning and evaluation

The prototype should be built deliberately, with each phase reviewable before moving forward.