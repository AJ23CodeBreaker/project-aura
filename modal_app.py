"""
Project Aura — Modal deployment.

Fresh-debug deployment of the FastAPI session bootstrap API as a Modal ASGI web
endpoint.

Purpose of this file version:
- Force a completely fresh Modal app name so we can rule out stale containers
  or stale code in the previous `project-aura` deployment.
- Keep the same volumes/secrets/runtime settings.
"""

import modal

# Fresh app name to guarantee a new deployment target.
app = modal.App("project-aura-fresh")

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
    min_containers=1,
    nonpreemptible=True,
)
@modal.asgi_app()
def serve() -> object:
    import os

    os.environ.setdefault("DATA_DIR", "/data/memory")

    print("AURA_BUILD_MARKER=voice-fix-fresh-2026-04-23-01")

    from app.api.session import app as fastapi_app  # noqa: PLC0415

    return fastapi_app