# Scripts

Utility scripts for development, deployment, offline voice work, and testing.

## Planned scripts

| Script | Purpose | Status |
|---|---|---|
| `deploy_modal.sh` | Deploy backend services to Modal | Stub — not yet created |
| `test_voice.py` | Test a TTS adapter locally against the actress voice | Stub — not yet created |
| `benchmark_stt.py` | Compare STT provider latency and accuracy | Stub — not yet created |
| `seed_memory.py` | Seed test user / relationship memory for dev sessions | Stub — not yet created |
| `check_latency.py` | Run an end-to-end latency benchmark | Stub — not yet created |

## Notes

- Offline voice experiments and provider benchmarking belong here,
  not in the live `app/voice/` path.
- Scripts that generate additional voice assets from the actress recording
  should also live here.
- See `TASKS.md §11` for what should NOT be done in early phases.
