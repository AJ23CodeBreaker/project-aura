/**
 * Project Aura — Frontend Configuration
 *
 * Set apiBaseUrl to point to your running backend.
 *
 *   Local development:  "http://localhost:8000"  (default)
 *   Modal deployment:   replace with your Modal web endpoint URL
 *
 * This file contains NO secrets. Never add provider API keys here.
 */
window.AURA_CONFIG = {
  apiBaseUrl: "http://localhost:8000",
  // TEST ONLY: set to a fixed string (e.g. "demo-user-001") to persist memory
  // and relationship state across sessions. Leave null for anonymous sessions.
  testUserId: null,
};
