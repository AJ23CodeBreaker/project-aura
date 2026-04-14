# Project Aura

A private-test, voice-first, relationship-based adult AI companion prototype.

The objective is not to build a generic chatbot.
The objective is to build a prototype that feels emotionally believable,
remembers shared history, and supports gradual intimacy progression over time.

> **Status: Phase 9 complete — Modal deployment wired; text chat prototype fully working locally and deployable.**

---

## What this is

Project Aura is a real-time voice-to-voice companion system. A user talks to
the companion by voice. The companion listens, understands, remembers, and
responds with a believable voice identity rooted in a hired actress's studio
recording. Intimacy and closeness build gradually across sessions.

This is a private prototype for internal testing — not a public product.

---

## Repository structure

```
project-aura/
│
├── app/                        Backend application (Python)
│   ├── api/                    Session bootstrap API (FastAPI)
│   │   └── session.py          /session/create and /session/{id}/end endpoints
│   ├── core/                   Shared utilities
│   │   └── logging.py          Structured logging and latency hooks
│   ├── models/                 Data models
│   │   ├── session.py          Session model and status enum
│   │   ├── memory.py           Four-layer memory model
│   │   └── relationship.py     Relationship state model (ClosenessLevel)
│   ├── adapters/               Replaceable provider interfaces
│   │   ├── stt.py              STT adapter (interface + stub)
│   │   ├── llm.py              LLM dialogue adapter (interface + stub)
│   │   └── tts.py              TTS / voice adapter (interface + stub)
│   ├── state/                  Runtime session state
│   │   └── session_store.py    InMemorySessionStore + RedisSessionStore stub
│   ├── memory/                 Selective memory engine
│   │   ├── engine.py           MemoryEngine interface (stub)
│   │   └── retrieval.py        Pre-generation context assembly (stub)
│   ├── voice/                  Live voice rendering
│   │   └── renderer.py         LiveVoiceRenderer — single canonical live path
│   ├── session/                Session lifecycle
│   │   └── manager.py          SessionManager
│   └── config/
│       └── settings.py         Environment-based config loader
│
├── frontend/                   Netlify-hosted web UI (placeholder)
│   ├── index.html              Single-page shell
│   ├── main.js                 Session lifecycle + stub transport
│   ├── style.css               Base styles
│   └── netlify.toml            Netlify deployment config
│
├── services/                   External service notes and wrappers
├── scripts/                    Dev, deployment, and offline voice scripts
├── docs/
│   └── decisions.md            Architecture decision log
│
├── .env.example                Environment variables template (copy → .env)
├── requirements.txt            Python dependencies
├── PRD.md                      Product requirements document
├── ARCHITECTURE.md             System architecture
├── TASKS.md                    Phased build plan
└── CLAUDE.md                   Working rules for Claude Code
```

---

## Architecture overview

| Layer | Host | Role |
|---|---|---|
| Frontend | Netlify | Browser UI, audio controls, session start/end |
| Orchestration | Modal (Python / Pipecat) | STT → LLM → TTS pipeline, memory, relationship state |
| Session state | Redis | Short-term runtime state (TTL-based) |
| Long-term memory | TBD persistent store | User facts, relationship history, episodic moments |
| Voice / offline | Modal + voice service | Actress asset management, offline enrichment |

**Key rules:**
- Provider secrets never appear in frontend code.
- One canonical live voice path — no extra transformation layers.
- Memory is selective structured data, not raw transcript storage.
- NSFW is state-driven (relationship level + session config), not keyword-triggered.

---

## Local setup

```bash
# Copy and fill in environment variables
cp .env.example .env

# Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the session bootstrap API locally
uvicorn app.api.session:app --reload
```

The frontend can be served directly from the `frontend/` directory
(any static file server, or Netlify CLI).

## Modal deployment

```bash
# One-time: create the Modal Secret with your Anthropic key
modal secret create aura-secrets ANTHROPIC_API_KEY=<your-key>

# Dev tunnel (live reload, temporary URL printed to terminal)
modal serve modal_app.py

# Permanent deploy (stable URL printed to terminal)
modal deploy modal_app.py
```

After deploying, update `frontend/config.js`:
```js
window.AURA_CONFIG = {
  apiBaseUrl: "https://<your-modal-endpoint>.modal.run",
  testUserId: null,
};
```

Add your Netlify URL to `CORS_ORIGINS` in the Modal Secret if the frontend
is hosted on Netlify (e.g. `CORS_ORIGINS=https://your-app.netlify.app`).

---

## Phase status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Repository skeleton and configuration foundation | **Complete** |
| Phase 2 | Frontend and backend baseline wiring | **Complete** |
| Phase 3 | Real-time voice pipeline skeleton (Pipecat + WebRTC) | **Complete** |
| Phase 4 | Memory and relationship-state implementation | **Complete** |
| Phase 5 | Companion behaviour and intimacy progression | **Complete** |
| Phase 6 | Testing, tuning, and prototype hardening | **Complete** |
| Phase 7A | AnthropicDialogueAdapter + text turn API | **Complete** |
| Phase 7B / Phase 8 | Frontend chat UX + conversation quality | **Complete** |
| Phase 9 | Modal deployment | **Complete** |

---

## What is stubbed

Everything below is scaffolded but not yet implemented:

- **STT provider** — interface defined; no real provider wired
- **LLM provider** — interface defined; no real provider wired
- **TTS / voice provider** — interface defined; no real provider wired
- **Redis session store** — `InMemorySessionStore` used locally; `RedisSessionStore` is a stub
- **Memory engine** — all four layers modelled; no storage backend connected
- **Relationship engine** — state model defined; logic not yet computed dynamically
- **Pipecat orchestration** — not yet wired; per-turn flow is the target for Phase 3
- **WebRTC transport** — frontend transport functions are placeholder stubs
- **Authentication** — session create endpoint accepts any request for now

---

## Core product principle

> **Believability is more important than technical complexity.**

When tradeoffs occur, prefer consistency over cleverness, emotional continuity
over feature count, and stable voice quality over experimental layering.
