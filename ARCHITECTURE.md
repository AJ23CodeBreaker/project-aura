# Project Aura — System Architecture

## 1. Purpose

This document defines the implementation architecture for Project Aura, a private-test, voice-first AI companion prototype.

The architecture must support:

- real-time voice-to-voice interaction
- believable companion behavior
- persistent selective memory
- relationship-state progression
- actress-based voice identity
- gradual intimacy progression
- adult-only private testing

This document is intentionally implementation-oriented. It defines system boundaries, service roles, data flow, memory strategy, and deployment structure.

---

## 2. Architecture Principles

Project Aura must follow these principles:

### 2.1 Believability over complexity
If a design choice improves realism, consistency, or emotional continuity, it should be preferred over technically flashy but unstable solutions.

### 2.2 One canonical live voice path
The real-time production path must remain as simple and stable as possible.
Offline voice experiments and asset generation are allowed, but the live pipeline should not stack unnecessary voice-transformation layers.

### 2.3 Selective memory, not transcript hoarding
The system should store meaningful memories, relationship state, and important user facts rather than relying on full raw conversation logs as the main source of continuity.

### 2.4 State-driven intimacy
Flirtation and NSFW capability must be governed by relationship state, context, and session dynamics rather than simple keyword triggers.

### 2.5 Frontend and backend separation
The Netlify frontend must not contain sensitive model-provider secrets or backend orchestration logic.
All sensitive processing must happen in backend services.

---

## 3. Deployment Overview

Project Aura is split into four major layers:

### 3.1 Frontend Layer
Hosted on Netlify.

Responsibilities:
- browser UI
- microphone permission handling
- audio device selection
- conversation controls
- session start / end UI
- status display
- lightweight chat/state display
- safe calls to backend endpoints

The frontend does not:
- store provider API secrets
- run core AI orchestration
- perform sensitive memory writes directly

### 3.2 Real-Time Orchestration Layer
Hosted on Modal.

Responsibilities:
- session orchestration
- real-time voice pipeline control
- STT -> LLM -> TTS pipeline coordination
- relationship-state injection
- memory retrieval and write-back
- tool / adapter routing
- transport/session management

### 3.3 Data and Memory Layer
Hosted in external data services.

Responsibilities:
- session state
- user profile memory
- relationship memory
- episodic memory
- optional transcript summaries
- voice/session metadata

### 3.4 Voice Asset and Offline Processing Layer
Hosted on Modal and external voice services.

Responsibilities:
- actress voice asset management
- voice quality testing
- offline asset generation
- possible future enrichment of emotional voice samples
- non-live experimentation

---

## 4. Canonical v1 Technology Choices

## 4.1 Frontend
- Netlify-hosted web frontend
- browser-based microphone/audio UI
- secure API calls to backend services
- no sensitive inference logic in browser

## 4.2 Real-Time Pipeline
- Pipecat for orchestration
- WebRTC-based real-time transport
- Python service runtime
- Modal for backend execution

## 4.3 STT
- low-latency speech-to-text engine
- must support streaming or near-streaming behavior
- partial transcription preferred

## 4.4 LLM
- primary conversational brain for:
  - companion dialogue
  - contextual response shaping
  - emotional tone
  - memory-aware generation
  - relationship-state behavior

## 4.5 TTS / Live Voice
- one primary live TTS / voice engine only
- actress-like identity must be implemented in the chosen live voice path
- optional post-processing layers are disabled by default in v1 real-time operation

## 4.6 Memory
- Redis for session and short-term runtime state
- persistent store for long-term memory
- graph-style relational memory may be added later if it provides clear value, but it must not block v1

For v1, long-term memory may use a simple persistent store; a graph database is explicitly deferred unless later testing clearly requires it.

## 4.7 Offline Voice Work
- offline voice asset generation is allowed
- benchmarking multiple voice methods is allowed
- experiments such as asset expansion, whisper variants, or emotional sample generation belong outside the live path

---

## 5. Core System Components

## 5.1 Netlify Frontend App

Responsibilities:
- render conversation UI
- manage connection lifecycle
- initiate session creation
- request temporary session/bootstrap data from backend
- stream or transmit audio to the real-time backend transport
- display companion state, listening state, speaking state, and connection state

Key rules:
- never expose backend provider keys in frontend code
- never place memory logic directly in browser
- never place direct vendor credentials in client-side environment variables

---

## 5.2 Session Bootstrap Service

This service creates a new conversation session.

Responsibilities:
- create session ID
- authenticate tester/user
- confirm adult-test access permissions
- return transport/bootstrap information needed by the frontend
- initialize runtime session state in Redis

This service may be hosted:
- on Modal, or
- as a very thin proxy layer if needed

Preferred rule:
- keep bootstrap thin
- keep core orchestration on Modal

---

## 5.3 Real-Time Orchestrator

This is the core backend service.

Responsibilities:
- receive user audio
- coordinate STT
- retrieve session context and relevant memories
- calculate relationship-state context
- inject dialogue instructions into the LLM
- route LLM output to TTS
- stream companion audio back to the client
- persist selective memory after each turn or session milestone

The orchestrator is the authoritative runtime brain of the system.

---

## 5.4 STT Adapter

Responsibilities:
- convert incoming user speech to text
- provide partial/final transcripts
- mark silence/end-of-turn events if available
- support interruption and turn-taking logic

The STT layer must optimize for:
- low latency
- stable transcription
- natural conversational timing

---

## 5.5 Dialogue Engine

Responsibilities:
- generate companion text responses
- incorporate:
  - system persona
  - session context
  - memory results
  - relationship-state data
  - intimacy policy/state
- output dialogue suitable for natural spoken delivery

Important rule:
The dialogue engine should generate spoken-style responses, not essay-style chatbot answers.

Responses should support:
- short turns
- playful short reactions
- follow-up questions
- unfinished-sounding natural speech when appropriate
- contextual warmth

---

## 5.6 Relationship State Engine

Responsibilities:
- maintain closeness/intimacy state
- update emotional openness
- determine flirtation allowance
- determine NSFW eligibility
- influence recall style and dialogue tone

This engine must not be a simple keyword gate.
It must consider:
- conversation history
- prior relationship milestones
- user behavior patterns
- recent emotional tone
- continuity from prior sessions

---

## 5.7 Memory Engine

Responsibilities:
- fetch relevant user and relationship memories before generation
- write new memories selectively after significant moments
- avoid over-saving trivial content
- support summaries, facts, emotional patterns, and shared moments

Memory retrieval should provide:
- stable user facts
- relationship status
- recent unresolved threads
- notable prior moments
- recent emotional context

---

## 5.8 Live Voice Renderer

Responsibilities:
- convert dialogue output to companion voice audio
- preserve voice identity
- preserve natural pacing
- support soft tone / warmth / intimacy shifts where possible
- stream audio back with low delay

Critical rule:
There must be one canonical live voice renderer for v1.
Do not stack multiple live voice transformation methods unless testing proves it necessary.

---

## 5.9 Offline Voice Asset Pipeline

Responsibilities:
- manage actress source recordings
- create additional voice assets if needed
- benchmark voice methods
- test whisper, playful, soft, intimate, and low-energy variants
- support future enrichment of the voice library

This pipeline is not part of the primary real-time path.

---

## 6. Real-Time Data Flow

## 6.1 Session Start

1. User opens Netlify UI
2. User starts a conversation
3. Frontend requests a new session from the backend
4. Backend creates a session and stores runtime state in Redis
5. Backend returns session/bootstrap data
6. Frontend connects to the real-time transport
7. Conversation begins

## 6.2 Per-Turn Flow

1. User speaks
2. Audio enters the real-time pipeline
3. STT generates transcript/partials
4. Orchestrator gathers:
   - session state
   - recent turn context
   - memory retrieval results
   - relationship-state values
5. Dialogue engine generates the response
6. Response is converted to speech by the live voice renderer
7. Audio is streamed back to the user
8. Session state is updated
9. Selective memory writes happen only if the turn is meaningful

## 6.3 Session End

1. User ends the conversation
2. Session summary is generated
3. Important memory candidates are written
4. Redis runtime session is closed or expired
5. Persistent relationship and memory stores remain available for next session

---

## 7. Memory Model

Project Aura uses selective memory with four layers.

## 7.1 Session Memory
Stored in Redis.

Contains:
- current session ID
- recent transcript window
- speaking/listening state
- recent emotional tone
- active conversation topic
- transport/session metadata
- current relationship-state snapshot

TTL-based and temporary.

## 7.2 Semantic User Memory
Persistent.

Contains:
- user preferences
- recurring interests
- important personal facts voluntarily shared by the user
- likes/dislikes relevant to interaction
- recurring style preferences

Should be concise and normalized.

## 7.3 Relationship Memory
Persistent.

Contains:
- closeness level
- affectionate tone history
- intimacy milestones
- tension or conflict notes
- comfort patterns
- preferred forms of emotional engagement
- prior shared moments with relational meaning

This is the backbone of continuity.

## 7.4 Episodic Memory
Persistent.

Contains:
- notable conversations
- memorable jokes or playful moments
- emotionally important exchanges
- promises
- callbacks
- unresolved threads worth revisiting later

Only high-value moments should become episodic memories.

---

## 8. Relationship State Model

The relationship model governs emotional and intimate progression.

## 8.1 Suggested State Layers

### Level 1 — New / Distant
Tone:
- warm but reserved
- no strong flirtation
- no sexual escalation

### Level 2 — Familiar / Comfortable
Tone:
- playful
- more personal references
- mild affection
- light teasing or gentle flirtation possible

### Level 3 — Close / Affectionate
Tone:
- emotionally warmer
- stronger attachment cues
- more softness and intimacy
- deeper emotional memory callbacks
- flirtation more natural and sustained

### Level 4 — Intimate / Adult
Tone:
- emotionally and romantically close
- NSFW conversation may be allowed when context supports it
- still must remain situational, gradual, and believable

## 8.2 State Inputs

State updates may consider:
- cumulative positive interactions
- emotional trust
- memory continuity
- user warmth
- consistency of sessions
- recent conflict or discomfort
- explicit user preferences or boundaries

## 8.3 State Constraints

The system must avoid:
- abrupt jumps from distant to explicit
- repetitive scripted affection
- permanent monotonic escalation
- contextless NSFW output

Relationship state must be dynamic, not a one-way unlock ladder.

---

## 9. NSFW Capability Design

NSFW support is part of the adult prototype, but it must be relationship-driven.

Rules:
- NSFW is not the default mode
- NSFW must depend on current relationship state and current context
- transitions should feel gradual and emotionally coherent
- the system should preserve companion believability even in adult mode
- adult testing access must be restricted to appropriate testers/accounts

The architecture must support separate policy controls for:
- adult-enabled sessions
- adult-disabled sessions
- relationship threshold gating
- configurable escalation behavior

---

## 10. Voice Architecture

## 10.1 Source Voice Asset
The actress’s studio recording is the foundation voice asset.

## 10.2 Voice Design Goal
The companion voice should feel:
- attractive
- stable
- soft when appropriate
- emotionally alive
- consistent across sessions

## 10.3 Live Path Rule
Use one primary live voice rendering path in v1.

Avoid:
- excessive post-processing in the live path
- unnecessary multi-stage timbre conversion
- experimental voice layering that harms latency or consistency

## 10.4 Offline Enrichment
If the initial 20-minute recording is not enough for expressive coverage, future voice asset enrichment should happen offline rather than by overcomplicating the live system.

---

## 11. Latency Targets

These are practical prototype targets, not unrealistic promises.

## 11.1 Response Targets

### Preferred
- first audible response after end-of-turn: <= 1.2 seconds
- interruption reaction: <= 300 ms
- session startup delay: as low as reasonably possible

### Stretch Goal
- first audible response: <= 900 ms

## 11.2 Priority Order
When tradeoffs occur, prioritize:
1. stable conversational rhythm
2. believable voice quality
3. emotional consistency
4. lower latency
5. secondary experimental enhancements

The system should not damage realism in pursuit of theoretical speed.

---

## 12. Security and Secret Handling

## 12.1 Frontend Rules
The Netlify frontend must never expose:
- LLM provider secrets
- TTS provider secrets
- backend admin keys
- memory database credentials

## 12.2 Backend Rules
Secrets must live in backend configuration or secure service environments only.

## 12.3 User Data Rules
The prototype should store only the data necessary to maintain continuity, improve testing quality, and evaluate product realism.

Raw full-session retention should not be the default memory strategy.

---

## 13. Observability and Evaluation

The system must log enough information to debug and improve realism without turning the product into a transcript archive.

Track:
- session duration
- connection failures
- STT latency
- LLM latency
- TTS latency
- first-audio latency
- interruption behavior
- memory retrieval counts
- memory write counts
- relationship-state changes

Human evaluation should focus on:
- realism
- warmth
- consistency
- recall quality
- intimacy timing
- voice attractiveness
- robotic-feeling reduction

---

## 14. Non-Goals for v1

The following are explicitly not required in v1:

- public production hardening
- large-scale scaling architecture
- multi-character support
- marketplace / payments
- app-store packaging
- social/community features
- complicated long-form world simulation
- overly complex graph architecture that blocks prototype progress

---

## 15. Implementation Guidance for Claude Code

Claude Code must follow these architecture rules:

1. Build clean module boundaries first.
2. Keep the live voice path simple.
3. Do not invent APIs or pretend integrations are finished.
4. Stub uncertain providers clearly.
5. Separate frontend, orchestration, memory, and voice layers cleanly.
6. Treat memory as selective structured data, not raw transcript dumping.
7. Keep adult/intimacy logic state-driven.
8. Prefer clear interfaces and replaceable adapters.
9. Do not introduce extra infrastructure unless it solves a real problem.
10. Optimize for a believable prototype, not theoretical perfection.

---

## 16. Summary

Project Aura will use:

- Netlify for the web UI
- Modal for the Python backend and orchestration
- Pipecat for real-time voice pipeline orchestration
- Redis for short-term session state
- persistent structured memory for user, relationship, and episodic continuity
- one canonical live voice path
- offline voice enrichment outside the real-time path

This architecture is designed to maximize believability, continuity, and emotional realism while keeping the first prototype buildable.