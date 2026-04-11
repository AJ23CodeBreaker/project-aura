"""
modal_app.py — Modal deployment stub

STUB: wraps the FastAPI session bootstrap API as a Modal ASGI web endpoint.

This file is NOT yet deployed or tested against a live Modal account.
Review against current Modal documentation before running `modal deploy`.

Prerequisites (run once per machine):
    pip install modal
    modal token new

Add backend secrets to Modal before deploying:
    modal secret create project-aura-secrets \
        SESSION_SECRET_KEY=<your-value> \
        ADULT_MODE_ENABLED=false

    # Add provider keys once selected (Phase 3+):
    # STT_API_KEY, LLM_API_KEY, TTS_API_KEY, REDIS_URL, etc.

Deploy:
    modal deploy modal_app.py

See scripts/deploy_modal.ps1 (Windows) or scripts/deploy_modal.sh (bash)
for the full step-by-step commands.
"""
import modal

from app.api.session import app as fastapi_app

# STUB: image definition.
# Pin additional system packages here if any provider SDKs require them.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
)

modal_app = modal.App("project-aura-bootstrap")


@modal_app.function(
    image=image,
    # STUB: mount Modal secrets here before deploying, e.g.:
    # secrets=[modal.Secret.from_name("project-aura-secrets")],
)
@modal.asgi_app()
def web():
    """Serve the FastAPI session bootstrap API on Modal."""
    return fastapi_app


@modal_app.function(
    image=image,
    # STUB: configure timeout and concurrency limits when wiring live sessions
    # timeout=600,
    # secrets=[modal.Secret.from_name("project-aura-secrets")],
)
async def run_orchestrator(session_id: str) -> dict:
    """
    STUB: Modal entry point for the companion session orchestrator.

    Will call app.orchestrator.runner.run_session(session_id) once
    DailyTransport and the pipeline are fully wired (Phase 3+).
    Not yet deployed or tested.
    """
    # TODO Phase 3+:
    # from app.orchestrator.runner import run_session
    # return await run_session(session_id)
    raise NotImplementedError(
        "Orchestrator not yet wired. "
        "Implement run_session() in app/orchestrator/runner.py (Phase 3+)."
    )
