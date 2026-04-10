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
// Config
// ---------------------------------------------------------------------------

// STUB: set VITE_API_BASE_URL (or window.ENV_API_BASE_URL) in your deployment
// environment. Never put secret keys here.
const API_BASE_URL =
  (typeof window !== "undefined" && window.ENV_API_BASE_URL) ||
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

function setDebug(data) {
  const panel = document.getElementById("debug-panel");
  const output = document.getElementById("debug-output");
  panel.style.display = "block";
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

// ---------------------------------------------------------------------------
// Session lifecycle
// ---------------------------------------------------------------------------

async function startSession() {
  setConnectionStatus("Connecting…");
  setStateLabel("starting");

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
    document.getElementById("btn-start").disabled = true;
    document.getElementById("btn-end").disabled = false;

    // STUB: initialise real-time transport here in Phase 3
    setDebug(data);

  } catch (err) {
    setConnectionStatus("Error");
    setStateLabel("failed");
    console.error("Session start error:", err);
    setDebug(`Error: ${err.message}`);
  }
}

async function endSession() {
  if (!currentSessionId) return;

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
  document.getElementById("btn-start").disabled = false;
  document.getElementById("btn-end").disabled = true;
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
