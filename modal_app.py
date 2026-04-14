"""
Project Aura — Modal deployment.

Serves the FastAPI session bootstrap API as a Modal ASGI web endpoint.

Volumes:
  aura-data   — mounted at /data; memory JSON files survive restarts and redeploys.

Secrets:
  aura-secrets — Modal Secret containing at minimum ANTHROPIC_API_KEY.
                 Optionally add CORS_ORIGINS to include your Netlify URL.

Data path:
  DATA_DIR is set to /data/memory inside the container so the memory store
  writes to the Modal Volume rather than the (ephemeral) container filesystem.

Local dev workflow (unchanged):
  uvicorn app.api.session:app --reload

Modal workflow:
  # One-time setup (run once per environment):
  modal secret create aura-secrets ANTHROPIC_API_KEY=<your-key>

  # Dev tunnel — live reload, temporary public URL:
  modal serve modal_app.py

  # Permanent deploy:
  modal deploy modal_app.py

After deploying, copy the printed web endpoint URL into frontend/config.js.
"""

import modal

app = modal.App("project-aura")

# Persistent volume — memory JSON files survive container restarts and redeploys.
data_volume = modal.Volume.from_name("aura-data", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_python_source("app")
)

@app.function(
    image=image,
    volumes={"/data": data_volume},
    secrets=[modal.Secret.from_name("aura-secrets")],
    # Modal 1.x: keep_warm was renamed to min_containers
    min_containers=1,
)
@modal.asgi_app()
def serve() -> object:
    """
    Return the FastAPI app after pointing DATA_DIR at the mounted Volume.

    DATA_DIR must be set before app.api.session is imported so the settings
    singleton picks up the correct path at startup.
    """
    import os

    os.environ.setdefault("DATA_DIR", "/data/memory")

    # Imported here (not at module level) so DATA_DIR is set first.
    from app.api.session import app as fastapi_app  # noqa: PLC0415

    return fastapi_app