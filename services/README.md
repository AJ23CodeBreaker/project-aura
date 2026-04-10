# Services

Configuration, wrappers, or bootstrap files for external services used by Project Aura.

## Planned integrations

| Service | Purpose | Status |
|---|---|---|
| Modal | Backend Python runtime and deployment | Stub — not yet deployed |
| Redis | Session state store (TTL-based) | Stub — not yet connected |
| STT provider (TBD) | Speech-to-text, streaming | Stub — provider not selected |
| LLM provider (TBD) | Companion dialogue brain | Stub — provider not selected |
| TTS / voice provider (TBD) | Live voice rendering | Stub — provider not selected |
| Persistent memory store (TBD) | Long-term memory (user, relationship, episodic) | Stub — provider not selected |

## Notes

- Provider credentials must never appear in frontend code.
- All service credentials live in `.env` (not committed) or Modal secret stores.
- See `ARCHITECTURE.md` for canonical service boundary definitions.
- See `docs/decisions.md` for open provider selection decisions.
