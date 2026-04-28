# Phase 12A Demo Validation Guide

**Scope:** Investor demo voice lane — Deepgram STT + Dolphin-Mistral-24B vLLM + Fish Audio S2 Pro TTS over Daily WebRTC.

**Date authored:** 2026-04-15

---

## 1. Prerequisites

### Environment variables (`.env`)

All of the following must be set before running the voice path:

| Variable | Purpose | Where to get it |
|---|---|---|
| `DAILY_API_KEY` | Creates and deletes Daily rooms server-side | https://dashboard.daily.co → Developers → API keys |
| `DEEPGRAM_API_KEY` | Streaming STT transcription | https://console.deepgram.com |
| `VLLM_BASE_URL` | OpenAI-compatible endpoint for Dolphin-Mistral-24B | Output of `modal deploy modal_vllm.py` |
| `VLLM_MODEL` | Model name served by vLLM | `cognitivecomputations/Dolphin3.0-Mistral-24B` |
| `FISH_AUDIO_URL` | Self-hosted Fish Audio S2 Pro endpoint | Output of `modal deploy modal_fish.py` |
| `DEMO_TOKEN` | Gate token for demo session creation | Any strong random string |
| `DEMO_STARTING_CLOSENESS` | Relationship level for demo sessions (1–5) | Set to `3` or `4` for investor demo |

Optional:
| Variable | Purpose |
|---|---|
| `FISH_AUDIO_VOICE_ID` | Reference ID for voice cloning (actress voice) |
| `FISH_AUDIO_API_KEY` | Auth header for Fish Audio endpoint (if proxy added) |
| `VLLM_API_KEY` | Auth for vLLM endpoint (if middleware added) |
| `DAILY_ROOM_EXPIRY_SECONDS` | Room TTL in seconds (default 3600) |

### Modal services

Both Modal services must be deployed and warm before the demo:

```bash
# 1. Download model weights (one-time, ~15 min each)
modal run modal_vllm.py::download_model
modal run modal_fish.py::download_model

# 2. Deploy services (keeps one container warm via min_containers=1)
modal deploy modal_vllm.py
modal deploy modal_fish.py
```

Copy the printed endpoint URLs to `.env`:
```
VLLM_BASE_URL=https://your-org--aura-vllm-serve.modal.run/v1
FISH_AUDIO_URL=https://your-org--aura-fish-serve.modal.run
```

---

## 2. Running the Backend

```bash
cd /c/project-aura
source .venv/Scripts/activate    # Windows
# source .venv/bin/activate      # Linux/macOS

uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Confirm the backend is healthy:
```bash
curl http://localhost:8000/health
# → {"status": "ok", "service": "aura"}
```

---

## 3. Validation Checklist

### 3.1 Unit tests (fully offline)

Run before any live testing to confirm core logic is sound:

```bash
pytest tests/test_voice_stack.py -v
pytest tests/test_api.py -v
```

Expected: all tests pass with no network calls.

Key test groups:
- `TestOpenAICompatibleDialogueAdapter` — vLLM adapter yields tokens, injects system prompt
- `TestDeepgramSTTAdapter` — STT buffers audio, handles blank/failure gracefully
- `TestFishAudioTTSAdapter` — TTS streams audio chunks, respects emotional hint speed map
- `TestLiveVoiceRendererEmotionalHint` — hint forwarded from session scene to TTS adapter
- `TestTextSSEPathRegression` — text/SSE path unaffected by Phase 12A changes
- `TestTransportUrl` — standard sessions get null, demo sessions get Daily room URL

### 3.2 Standard (text-only) session smoke test

Verify Phase 12A did not break the existing text/SSE path:

```bash
# Create session (no demo token)
curl -s -X POST http://localhost:8000/session/create -H "Content-Type: application/json" -d '{}'
# → {"session_id": "...", "status": "initializing", "adult_mode": false, "transport_url": null}

# Send a turn
SESSION_ID=<from above>
curl -s -X POST http://localhost:8000/session/$SESSION_ID/turn \
  -H "Content-Type: application/json" \
  -d '{"user_text": "Hello"}'
# → {"session_id": "...", "assistant_text": "...", "turn_count": 1}

# End session
curl -s -X POST http://localhost:8000/session/$SESSION_ID/end
# → {"status": "ended", "session_id": "..."}
```

### 3.3 Demo token gating

```bash
# Missing token → no adult mode
curl -s -X POST http://localhost:8000/session/create -H "Content-Type: application/json" \
  -d '{}' | jq .adult_mode
# → false

# Wrong token → 403
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/session/create \
  -H "Content-Type: application/json" -d '{"demo_token": "wrong"}'
# → 403

# Correct token → adult mode, transport_url populated (if DAILY_API_KEY set)
curl -s -X POST http://localhost:8000/session/create -H "Content-Type: application/json" \
  -d '{"demo_token": "'$DEMO_TOKEN'"}' | jq '{adult_mode, transport_url}'
# → {"adult_mode": true, "transport_url": "https://...daily.co/..."}
```

### 3.4 Voice pipeline — adapter connectivity

Test each adapter independently before a full voice session:

**Deepgram STT**
```bash
python - <<'EOF'
import asyncio, os
from app.adapters.stt import DeepgramSTTAdapter

async def test():
    adapter = DeepgramSTTAdapter()
    silence = bytes(16000 * 2)  # 1 second of silent int16 PCM
    async for event in adapter.transcribe_stream(iter([silence])):
        print("STT event:", event)
    print("STT adapter OK (blank audio → no transcript expected)")

asyncio.run(test())
EOF
```

**Fish Audio TTS**
```bash
python - <<'EOF'
import asyncio
from app.adapters.tts import FishAudioTTSAdapter

async def test():
    async def text_gen():
        yield "Hello, this is a voice check."

    adapter = FishAudioTTSAdapter()
    total_bytes = 0
    async for chunk in adapter.synthesize_stream(text_gen()):
        total_bytes += len(chunk)
    print(f"TTS adapter OK — received {total_bytes} audio bytes")
    await adapter.close()

asyncio.run(test())
EOF
```

**vLLM adapter**
```bash
python - <<'EOF'
import asyncio, os
from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter

async def test():
    adapter = OpenAICompatibleDialogueAdapter(
        base_url=os.getenv("VLLM_BASE_URL"),
        api_key=os.getenv("VLLM_API_KEY", "no-key-required"),
        model=os.getenv("VLLM_MODEL", "cognitivecomputations/Dolphin3.0-Mistral-24B"),
        max_tokens=50,
    )
    tokens = []
    async for token in adapter.generate("You are a helpful assistant.", [], "Say hi."):
        tokens.append(token)
    print("vLLM adapter OK:", "".join(tokens))

asyncio.run(test())
EOF
```

### 3.5 Full voice session end-to-end (browser)

1. Open `frontend/index.html` in Chrome (or the Netlify preview URL).
2. Check console — Daily JS SDK must be loaded: `window.Daily !== undefined`.
3. Add the demo token to `frontend/config.js`:
   ```js
   window.AURA_CONFIG = {
     apiBaseUrl: "http://localhost:8000",
     demoToken: "your-demo-token",
   };
   ```
4. Click **Start Session**.
5. Observe:
   - `transport_url` is non-null in the debug panel.
   - Status transitions to **"Voice connected"**.
   - State label shows **"listening"**.
6. Grant microphone permission when prompted.
7. Speak a sentence. Observe:
   - State transitions to *(brief)* **"listening"** → **"speaking"** (bot audio plays).
8. Verify barge-in: begin speaking before the bot finishes. Observe:
   - State transitions back to **"listening"** immediately.
9. Click **End Session**. Observe:
   - Status shows **"Disconnected"**.
   - Backend logs show room deleted.

### 3.6 Graceful degradation (no Daily key)

Remove `DAILY_API_KEY` from `.env` and restart the backend.

```bash
curl -s -X POST http://localhost:8000/session/create -H "Content-Type: application/json" \
  -d '{"demo_token": "'$DEMO_TOKEN'"}' | jq '{adult_mode, transport_url}'
# → {"adult_mode": true, "transport_url": null}
```

The demo session should work as a text-only session — adult mode is active, voice is unavailable, SSE streaming continues to work normally.

---

## 4. Latency Budget

For a smooth real-time demo, target these per-turn latencies:

| Component | Target | Notes |
|---|---|---|
| Deepgram STT | < 400 ms | After `UserStoppedSpeakingFrame` |
| vLLM first token | < 800 ms | Dolphin-Mistral-24B on A100, warm container |
| Fish Audio first audio chunk | < 500 ms | After first LLM token accumulated |
| Daily round-trip | < 100 ms | WebRTC; depends on network |
| **Total TTFA** | **< 1.5 s** | Time-to-first-audio from end of user speech |

If latency is unacceptable:
- Increase `VLLM_MAX_TOKENS` ceiling and accept truncation for speed.
- Reduce `DEMO_STARTING_CLOSENESS` to avoid a heavy system prompt on first turn.
- Check Modal container warm status: `modal app list` → container count for `aura-vllm` and `aura-fish` should show ≥ 1 running.

---

## 5. Known Limitations (Phase 12A)

| Item | Status | Notes |
|---|---|---|
| STT streaming (utterance-level) | **Working** | Buffers full utterance, single Deepgram call per turn |
| STT real-time streaming | **Deferred** | Deepgram live websocket streaming not wired; requires pipecat DeepgramSTTService |
| Fish Audio voice cloning | **Optional** | Set `FISH_AUDIO_VOICE_ID` to a reference_id for actress voice |
| Bot participant visible | **Expected** | Daily server bot appears as a participant in the room; cosmetic |
| Redis session persistence | **Deferred** | In-memory session store only; sessions lost on backend restart |
| Multiple concurrent demo sessions | **Untested** | One session per tab; concurrent load not benchmarked |
| Daily room token auth | **Not implemented** | Room is open to anyone with the URL; acceptable for private single-user demo |
| pipecat version lock | **Assumed** | Pipecat API subject to change; pin to tested version |
| Barge-in on text turns | **N/A** | Barge-in is voice-only; text SSE turns are unaffected |

---

## 6. Rollback

If the Phase 12A voice path causes problems during the demo, set:

```
DAILY_API_KEY=   # unset or blank
```

All demo sessions will fall back to text-only mode automatically. No code changes required.

---

## 7. Appendix — Daily Room Config

Rooms are created with these parameters (see `app/api/session.py → _create_daily_room()`):

```json
{
  "properties": {
    "exp": "<unix_timestamp + DAILY_ROOM_EXPIRY_SECONDS>",
    "enable_chat": false,
    "start_video_off": true,
    "start_audio_off": false,
    "enable_screenshare": false,
    "lang": "en"
  }
}
```

Rooms are deleted immediately on session end. If a backend crash prevents cleanup, rooms expire automatically at `exp`.
