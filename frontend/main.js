/**
 * Project Aura — Frontend Entry Point
 *
 * Two-mode UI:
 *   1. Text Mode:
 *      User types text → backend returns assistant text → user can press
 *      "Play voice" to synthesize and play the assistant reply.
 *
 *   2. Voice Mode:
 *      User speaks through microphone → LiveKit voice transport → Aura replies
 *      in real time.
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const API_BASE_URL =
  (window.AURA_CONFIG && window.AURA_CONFIG.apiBaseUrl) ||
  "http://localhost:8000";

const TTS_ENDPOINT_TEMPLATE =
  (window.AURA_CONFIG && window.AURA_CONFIG.ttsEndpointTemplate) ||
  "/session/{sessionId}/tts";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentSessionId = null;
let currentMode = null; // "text" | "voice" | null

let lastAssistantText = "";
let currentPlaybackAudio = null;

// LiveKit room object while a voice session is active.
let _livekitRoom = null;
let _voiceActive = false;

// Track attached remote audio elements by track SID.
const _remoteAudioEls = new Map();

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function setConnectionStatus(text, state) {
  const el = document.getElementById("connection-status");
  if (!el) return;
  el.textContent = text;
  el.className = state ? `status--${state}` : "";
}

function setStateLabel(text) {
  const el = document.getElementById("state-label");
  if (!el) return;
  el.textContent = text;
}

function setSessionId(id) {
  const el = document.getElementById("session-id");
  if (!el) return;
  el.textContent = id ? `session: ${id}` : "";
}

function setDebug(data) {
  const panel = document.getElementById("debug-panel");
  const output = document.getElementById("debug-output");
  if (!panel || !output) return;

  panel.style.display = "block";
  output.textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function hideDebug() {
  const panel = document.getElementById("debug-panel");
  if (panel) panel.style.display = "none";
}

function setTextControlsEnabled(enabled) {
  const input = document.getElementById("message-input");
  const send = document.getElementById("btn-send");

  if (input) input.disabled = !enabled;
  if (send) send.disabled = !enabled;
}

function setPlayEnabled(enabled) {
  const btn = document.getElementById("btn-play");
  if (btn) btn.disabled = !enabled;
}

function setSessionButtonsForMode(mode, active) {
  const textStart = document.getElementById("btn-text-start");
  const textEnd = document.getElementById("btn-text-end");
  const voiceStart = document.getElementById("btn-voice-start");
  const voiceEnd = document.getElementById("btn-voice-end");

  if (!active) {
    if (textStart) textStart.disabled = false;
    if (voiceStart) voiceStart.disabled = false;
    if (textEnd) textEnd.disabled = true;
    if (voiceEnd) voiceEnd.disabled = true;
    return;
  }

  if (textStart) textStart.disabled = true;
  if (voiceStart) voiceStart.disabled = true;

  if (textEnd) textEnd.disabled = mode !== "text";
  if (voiceEnd) voiceEnd.disabled = mode !== "voice";
}

function resetUiForDisconnected() {
  currentSessionId = null;
  currentMode = null;
  lastAssistantText = "";

  setConnectionStatus("Disconnected");
  setStateLabel("idle");
  setSessionId(null);
  setTextControlsEnabled(false);
  setPlayEnabled(false);
  setSessionButtonsForMode(null, false);
  hideDebug();
}

function setBusyState(message) {
  setConnectionStatus(message || "Working…", "busy");
}

// ---------------------------------------------------------------------------
// Chat helpers
// ---------------------------------------------------------------------------

function appendMessage(role, text) {
  const log = document.getElementById("chat-log");
  if (!log) return;

  const el = document.createElement("div");
  el.className = `msg msg-${role}`;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

function createMessageBubble(role) {
  const log = document.getElementById("chat-log");
  if (!log) return null;

  const el = document.createElement("div");
  el.className = `msg msg-${role}`;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function clearChat() {
  const log = document.getElementById("chat-log");
  if (log) log.innerHTML = "";
}

function showTypingIndicator() {
  const log = document.getElementById("chat-log");
  if (!log) return;

  removeTypingIndicator();

  const el = document.createElement("div");
  el.id = "typing-indicator";
  el.className = "msg msg-typing";
  el.innerHTML = "<span>•</span><span>•</span><span>•</span>";
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function focusInput() {
  const input = document.getElementById("message-input");
  if (input && !input.disabled) input.focus();
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

async function createSession() {
  const response = await fetch(`${API_BASE_URL}/session/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: (window.AURA_CONFIG && window.AURA_CONFIG.testUserId) || null,
      demo_token: (window.AURA_CONFIG && window.AURA_CONFIG.demoToken) || null,
    }),
  });

  if (!response.ok) {
    throw new Error(`Session create failed: ${response.status}`);
  }

  return await response.json();
}

async function startTextSession() {
  if (currentSessionId) return;

  currentMode = "text";
  setBusyState("Starting text session…");
  setStateLabel("starting");
  setSessionButtonsForMode("text", true);
  clearChat();
  setTextControlsEnabled(false);
  setPlayEnabled(false);

  try {
    const data = await createSession();
    currentSessionId = data.session_id;

    // Keep repeated demo starts working while removing any URL token.
    if (window.AURA_CONFIG && window.AURA_CONFIG.demoToken) {
      history.replaceState(null, "", window.location.pathname);
    }

    setSessionId(data.session_id);
    setConnectionStatus("Text session connected", "connected");
    setStateLabel("ready");
    setTextControlsEnabled(true);
    setPlayEnabled(false);
    setDebug(data);
    focusInput();
  } catch (err) {
    console.error("Text session start error:", err);
    appendMessage("error", "[Could not start text session]");
    resetUiForDisconnected();
    setDebug(`Error: ${err.message}`);
  }
}

async function startVoiceSession() {
  if (currentSessionId) return;

  currentMode = "voice";
  setBusyState("Starting voice session…");
  setStateLabel("starting");
  setSessionButtonsForMode("voice", true);
  setTextControlsEnabled(false);
  setPlayEnabled(false);

  try {
    const data = await createSession();
    currentSessionId = data.session_id;

    if (window.AURA_CONFIG && window.AURA_CONFIG.demoToken) {
      history.replaceState(null, "", window.location.pathname);
    }

    setSessionId(data.session_id);
    setDebug(data);

    if (
      data.transport_provider === "livekit" &&
      data.transport_url &&
      data.transport_token &&
      data.transport_room_name
    ) {
      try {
        await _initVoiceTransport(
          data.transport_url,
          data.transport_token,
          data.transport_room_name
        );
      } catch (voiceErr) {
        console.error("Voice transport init failed:", voiceErr);
        setConnectionStatus("Connected, but voice failed", "error");
        setStateLabel("voice failed");
        appendMessage(
          "error",
          "[Voice transport failed — check LiveKit/backend logs]"
        );
      }
    } else {
      setConnectionStatus("Connected, but no voice transport", "error");
      setStateLabel("no voice transport");
      appendMessage(
        "error",
        "[No LiveKit voice transport returned by backend]"
      );
    }
  } catch (err) {
    console.error("Voice session start error:", err);
    appendMessage("error", "[Could not start voice session]");
    resetUiForDisconnected();
    setDebug(`Error: ${err.message}`);
  }
}

async function endCurrentSession() {
  if (!currentSessionId) return;

  const sessionIdToEnd = currentSessionId;

  setBusyState("Ending…");
  setStateLabel("ending");
  setTextControlsEnabled(false);
  setPlayEnabled(false);
  setSessionButtonsForMode(currentMode, true);

  await _stopCurrentPlayback();
  await _destroyVoiceTransport();

  try {
    await fetch(`${API_BASE_URL}/session/${sessionIdToEnd}/end`, {
      method: "POST",
    });
  } catch (err) {
    console.error("Session end error:", err);
  }

  resetUiForDisconnected();
}

// ---------------------------------------------------------------------------
// Text turn
// ---------------------------------------------------------------------------

function handleComposerSubmit(event) {
  event.preventDefault();
  sendTextTurn();
}

async function sendTextTurn() {
  const input = document.getElementById("message-input");
  if (!input) return;

  const userText = input.value.trim();

  if (!userText || !currentSessionId || currentMode !== "text") return;

  input.value = "";
  appendMessage("user", userText);
  showTypingIndicator();
  setTextControlsEnabled(false);
  setPlayEnabled(false);
  setStateLabel("thinking");

  let assistantBubble = null;
  let assistantText = "";

  try {
    const response = await fetch(
      `${API_BASE_URL}/session/${currentSessionId}/turn/stream`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_text: userText }),
      }
    );

    if (!response.ok) {
      const err = new Error(`Turn failed: ${response.status}`);
      err.status = response.status;
      throw err;
    }

    if (!response.body) {
      throw new Error("No streaming response body returned.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    outer: while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;

        const data = line.slice(6);
        if (data === "[DONE]") break outer;

        if (!assistantBubble) {
          removeTypingIndicator();
          assistantBubble = createMessageBubble("assistant");
        }

        assistantText += data;
        assistantBubble.textContent += data;

        const log = document.getElementById("chat-log");
        if (log) log.scrollTop = log.scrollHeight;
      }
    }

    lastAssistantText = assistantText.trim();

    if (lastAssistantText) {
      setPlayEnabled(true);
      setStateLabel("reply ready");
    } else {
      setStateLabel("ready");
    }
  } catch (err) {
    let message;

    if (err.status === 404) {
      message = "[Session expired — please start a new session]";
    } else if (err.status >= 500) {
      message = "[Server error — try sending again]";
    } else {
      message = "[Could not reach the server — is the backend running?]";
    }

    removeTypingIndicator();
    appendMessage("error", message);
    setStateLabel("ready");
    console.error("Turn error:", err);
  } finally {
    removeTypingIndicator();
    if (currentSessionId && currentMode === "text") {
      setTextControlsEnabled(true);
      focusInput();
    }
  }
}

// ---------------------------------------------------------------------------
// Text reply playback
// ---------------------------------------------------------------------------

async function playLastAssistantReply() {
  if (!lastAssistantText || !currentSessionId) return;
  await speakAssistantText(lastAssistantText);
}

function resolveTtsEndpoint(sessionId) {
  return TTS_ENDPOINT_TEMPLATE.replace("{sessionId}", encodeURIComponent(sessionId));
}

async function speakAssistantText(text) {
  if (!text || !currentSessionId) return;

  await _stopCurrentPlayback();

  setPlayEnabled(false);
  setStateLabel("generating voice");

  try {
    const response = await fetch(`${API_BASE_URL}${resolveTtsEndpoint(currentSessionId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const err = new Error(`TTS failed: ${response.status}`);
      err.status = response.status;
      throw err;
    }

    const audioBlob = await response.blob();

    if (!audioBlob || audioBlob.size === 0) {
      throw new Error("TTS returned empty audio.");
    }

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    currentPlaybackAudio = audio;

    audio.onplay = () => {
      setStateLabel("speaking");
    };

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      currentPlaybackAudio = null;
      setStateLabel("ready");
      setPlayEnabled(Boolean(lastAssistantText));
      focusInput();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      currentPlaybackAudio = null;
      setStateLabel("ready");
      setPlayEnabled(Boolean(lastAssistantText));
      appendMessage("error", "[Could not play generated voice]");
      focusInput();
    };

    await audio.play();
  } catch (err) {
    console.error("TTS playback error:", err);

    if (err.status === 404) {
      appendMessage(
        "error",
        "[Voice playback endpoint not found — backend /tts endpoint is not ready yet]"
      );
    } else if (err.status >= 500) {
      appendMessage("error", "[Voice generation server error]");
    } else {
      appendMessage("error", "[Could not generate voice playback]");
    }

    setStateLabel("ready");
    setPlayEnabled(Boolean(lastAssistantText));
    focusInput();
  }
}

async function _stopCurrentPlayback() {
  if (!currentPlaybackAudio) return;

  try {
    currentPlaybackAudio.pause();
    currentPlaybackAudio.currentTime = 0;
  } catch (_) {}

  currentPlaybackAudio = null;
}

// ---------------------------------------------------------------------------
// LiveKit voice transport
// ---------------------------------------------------------------------------

async function _initVoiceTransport(livekitUrl, token, roomName) {
  if (!window.LivekitClient) {
    throw new Error("LiveKit SDK not loaded.");
  }

  const { Room, RoomEvent, Track } = window.LivekitClient;

  _livekitRoom = new Room({
    adaptiveStream: true,
    dynacast: true,
  });

  _livekitRoom
    .on(RoomEvent.Connected, async () => {
      _voiceActive = true;
      setConnectionStatus("Voice connected", "connected");
      setStateLabel("listening");

      try {
        if (typeof _livekitRoom.startAudio === "function") {
          await _livekitRoom.startAudio();
        }
      } catch (err) {
        console.warn("LiveKit startAudio warning:", err);
      }

      try {
        await _livekitRoom.localParticipant.setMicrophoneEnabled(true);
      } catch (err) {
        console.error("Could not enable microphone:", err);
        setConnectionStatus("Mic permission error", "error");
      }
    })
    .on(RoomEvent.Disconnected, () => {
      _voiceActive = false;
      if (currentMode === "voice") {
        setConnectionStatus("Voice disconnected", "");
        setStateLabel("idle");
      }
    })
    .on(RoomEvent.ParticipantConnected, (participant) => {
      console.log("Remote participant connected:", participant.identity);
    })
    .on(RoomEvent.ParticipantDisconnected, (participant) => {
      console.log("Remote participant disconnected:", participant.identity);
      if (_voiceActive) {
        setStateLabel("listening");
      }
    })
    .on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio && !participant.isLocal) {
        const el = track.attach();
        el.autoplay = true;
        el.playsInline = true;
        el.style.display = "none";
        document.body.appendChild(el);
        _remoteAudioEls.set(publication.trackSid || publication.sid, el);
        setStateLabel("speaking");
      }
    })
    .on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio && !participant.isLocal) {
        const key = publication.trackSid || publication.sid;
        const el = _remoteAudioEls.get(key);

        if (el) {
          track.detach(el);
          el.remove();
          _remoteAudioEls.delete(key);
        }

        if (_voiceActive) {
          setStateLabel("listening");
        }
      }
    })
    .on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const localIdentity = _livekitRoom.localParticipant?.identity;
      const localSpeaking = speakers.some((p) => p.identity === localIdentity);

      if (
        localSpeaking &&
        document.getElementById("state-label").textContent === "speaking"
      ) {
        setStateLabel("listening");
      }
    })
    .on(RoomEvent.ConnectionStateChanged, (state) => {
      console.log("LiveKit state:", state, "room:", roomName);
    })
    .on(RoomEvent.MediaDevicesError, (err) => {
      console.error("Media devices error:", err);
      setConnectionStatus("Mic permission error", "error");
    });

  await _livekitRoom.connect(livekitUrl, token);
}

async function _destroyVoiceTransport() {
  if (!_livekitRoom) return;

  _voiceActive = false;

  for (const el of _remoteAudioEls.values()) {
    try {
      el.remove();
    } catch (_) {}
  }

  _remoteAudioEls.clear();

  try {
    await _livekitRoom.localParticipant.setMicrophoneEnabled(false);
  } catch (_) {}

  try {
    await _livekitRoom.disconnect();
  } catch (_) {}

  _livekitRoom = null;
}

async function requestMicrophoneAccess() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return stream;
  } catch (err) {
    console.error("Microphone access denied:", err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Expose handlers for inline HTML onclick/onsubmit
// ---------------------------------------------------------------------------

window.startTextSession = startTextSession;
window.startVoiceSession = startVoiceSession;
window.endCurrentSession = endCurrentSession;
window.handleComposerSubmit = handleComposerSubmit;
window.playLastAssistantReply = playLastAssistantReply;