/**
 * Project Aura — Frontend Entry Point (placeholder)
 *
 * Responsibilities:
 *   - manage session lifecycle (start / end)
 *   - display connection and conversation state
 *   - handle browser microphone permissions
 *   - call the backend bootstrap endpoint to create sessions
 *   - connect to real-time transport (Pipecat / WebRTC) — STUB
 *
 * RULES:
 *   - This file must NEVER contain provider API secrets.
 *   - Core memory logic and orchestration must stay in the backend.
 *   - Only safe session metadata is exchanged with the frontend.
 *
 * STUB NOTE: Real-time transport (WebRTC) is not yet wired.
 *   Session creation calls the backend bootstrap API.
 *   Audio capture and streaming are placeholder functions (Phase 3).
 */

// ---------------------------------------------------------------------------
// Config — set in frontend/config.js, not here
// ---------------------------------------------------------------------------

const API_BASE_URL =
  (window.AURA_CONFIG && window.AURA_CONFIG.apiBaseUrl) ||
  "http://localhost:8000";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let currentSessionId = null;

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function setConnectionStatus(text) {
  document.getElementById("connection-status").textContent = text;
}

function setStateLabel(text) {
  document.getElementById("state-label").textContent = text;
}

function setSessionId(id) {
  const el = document.getElementById("session-id");
  el.textContent = id ? `session: ${id}` : "";
}

function setDebug(data) {
  const panel = document.getElementById("debug-panel");
  const output = document.getElementById("debug-output");
  panel.style.display = "block";
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

// ---------------------------------------------------------------------------
// Chat helpers
// ---------------------------------------------------------------------------

function appendMessage(role, text) {
  const log = document.getElementById("chat-log");
  const el = document.createElement("div");
  el.className = `msg msg-${role}`;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

function clearChat() {
  document.getElementById("chat-log").innerHTML = "";
}

function setComposerEnabled(enabled) {
  document.getElementById("btn-send").disabled = !enabled;
  document.getElementById("message-input").disabled = !enabled;
}

// ---------------------------------------------------------------------------
// Turn
// ---------------------------------------------------------------------------

function handleComposerSubmit(event) {
  event.preventDefault();
  sendTurn();
}

async function sendTurn() {
  const input = document.getElementById("message-input");
  const userText = input.value.trim();
  if (!userText || !currentSessionId) return;

  input.value = "";
  appendMessage("user", userText);
  setComposerEnabled(false);
  setStateLabel("thinking");

  try {
    const response = await fetch(
      `${API_BASE_URL}/session/${currentSessionId}/turn`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_text: userText }),
      }
    );

    if (!response.ok) {
      throw new Error(`Turn failed: ${response.status}`);
    }

    const data = await response.json();
    appendMessage("assistant", data.assistant_text);
    setStateLabel("idle");
  } catch (err) {
    appendMessage("assistant", "[Error: could not get a reply]");
    setStateLabel("idle");
    console.error("Turn error:", err);
  } finally {
    setComposerEnabled(true);
    input.focus();
  }
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

async function startSession() {
  setConnectionStatus("Connecting…");
  setStateLabel("starting");
  document.getElementById("btn-start").disabled = true;

  try {
    const response = await fetch(`${API_BASE_URL}/session/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: null }), // STUB: no auth yet
    });

    if (!response.ok) {
      throw new Error(`Session create failed: ${response.status}`);
    }

    const data = await response.json();
    currentSessionId = data.session_id;

    setConnectionStatus("Connected");
    setStateLabel("idle");
    setSessionId(data.session_id);
    clearChat();
    setComposerEnabled(true);
    document.getElementById("message-input").focus();
    document.getElementById("btn-end").disabled = false;

    // STUB: initialise real-time transport here in Phase 3
    setDebug(data);

  } catch (err) {
    setConnectionStatus("Error");
    setStateLabel("failed");
    setSessionId(null);
    document.getElementById("btn-start").disabled = false;
    console.error("Session start error:", err);
    setDebug(`Error: ${err.message}`);
  }
}

async function endSession() {
  if (!currentSessionId) return;

  setConnectionStatus("Ending…");
  setStateLabel("ending");
  document.getElementById("btn-end").disabled = true;
  setComposerEnabled(false);

  try {
    await fetch(`${API_BASE_URL}/session/${currentSessionId}/end`, {
      method: "POST",
    });
  } catch (err) {
    console.error("Session end error:", err);
  }

  currentSessionId = null;
  setConnectionStatus("Disconnected");
  setStateLabel("idle");
  setSessionId(null);
  document.getElementById("btn-start").disabled = false;
}

// ---------------------------------------------------------------------------
// STUB: microphone capture placeholder (Phase 3)
// ---------------------------------------------------------------------------

async function requestMicrophoneAccess() {
  // TODO Phase 3: implement real microphone capture and WebRTC stream setup
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return stream;
  } catch (err) {
    console.error("Microphone access denied:", err);
    return null;
  }
}
