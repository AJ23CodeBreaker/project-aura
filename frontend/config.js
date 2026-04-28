/**
 * Project Aura — Frontend Configuration
 *
 * Local browser on localhost:5500 talks directly to the deployed Modal backend.
 *
 * This file contains NO provider secrets. Never add Fish, Deepgram, Modal,
 * LiveKit, or LLM API keys here.
 */
window.AURA_CONFIG = {
  apiBaseUrl: "https://airjacky--project-aura-fresh-serve.modal.run",
  testUserId: null,
  demoToken: "aura-demo-7Kp9xQ2mL8vR4nT6yB1cW5zH3uJ0DT",

  /**
   * Typed-text playback endpoint.
   *
   * The frontend will replace {sessionId} with the active session id.
   * Expected backend behavior:
   *   POST /session/{session_id}/tts
   *   body: { "text": "assistant reply text" }
   *   response: audio/wav or another browser-playable audio format
   */
  ttsEndpointTemplate: "/session/{sessionId}/tts"
};