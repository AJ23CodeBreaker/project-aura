/**
 * Project Aura — Frontend Configuration
 *
 * apiBaseUrl is selected at runtime based on hostname:
 *   localhost / 127.0.0.1  →  local uvicorn dev server
 *   any other host         →  deployed Modal endpoint
 *
 * This file contains NO secrets. Never add provider API keys here.
 */
const _isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

window.AURA_CONFIG = {
  apiBaseUrl: _isLocal
    ? "http://localhost:8000"
    : "https://airjacky--project-aura-serve.modal.run",
  // TEST ONLY: set to a fixed string (e.g. "demo-user-001") to persist memory
  // and relationship state across sessions. Leave null for anonymous sessions.
  testUserId: null,
};
