"""
Project Aura — vLLM Modal Service (Phase 12A)

Serves Dolphin-Mistral-24B-Venice-Edition via vLLM's OpenAI-compatible API.
This is the LLM backend for the investor demo lane.

--- Deployment ---

One-time setup (run from the project root):

  # Create a secret for any future auth middleware key
  modal secret create aura-vllm-secrets VLLM_API_KEY=your-optional-key

  # Download model weights to a persistent Modal Volume
  modal run modal_vllm.py::download_model

  # Deploy the inference server
  modal deploy modal_vllm.py

After deploying, copy the printed web endpoint URL into your .env:
  VLLM_BASE_URL=https://your-org--aura-vllm-serve.modal.run/v1

--- Model ---

MODEL_NAME defaults to cognitivecomputations/Dolphin3.0-Mistral-24B.

"Dolphin-Mistral-24B-Venice-Edition" refers to Venice AI's deployment of
this model family. If Venice AI publishes a specific HuggingFace repo for
their Venice Edition weights, update MODEL_NAME to that repo slug.

--- GPU requirements ---

This file is configured for H100 on Modal.
Modal may automatically upgrade H100 requests to H200.

--- Token cap ---

VLLM_MAX_TOKENS in .env controls the per-turn token cap on the client side.
The server-side --max-model-len limits the maximum context window.
8192 tokens is sufficient for 6-turn companion conversations.
"""

import os
import pathlib
import subprocess
import sys

import modal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = os.environ.get(
    "VLLM_MODEL_NAME",
    "cognitivecomputations/Dolphin3.0-Mistral-24B",
)

MODEL_DIR = "/models"
MODEL_CACHE_DIR = f"{MODEL_DIR}/model"
VLLM_PORT = 8080
STARTUP_TIMEOUT_SECONDS = 1200

# ---------------------------------------------------------------------------
# Modal infrastructure
# ---------------------------------------------------------------------------

app = modal.App("aura-vllm")

model_volume = modal.Volume.from_name("aura-vllm-models", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.0-devel-ubuntu22.04",
        add_python="3.11",
    )
    .entrypoint([])
    .pip_install(
        "vllm==0.19.0",
        "huggingface-hub>=0.22",
        "transformers>=4.40,<6",
        "accelerate>=0.29",
        "bitsandbytes>=0.43",
    )
    .env(
        {
            "HF_HOME": MODEL_DIR,
            "HF_XET_HIGH_PERFORMANCE": "1",
        }
    )
)

# ---------------------------------------------------------------------------
# Model download function
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    gpu="H100",
    volumes={MODEL_DIR: model_volume},
    timeout=7200,
    secrets=[modal.Secret.from_name("aura-vllm-secrets")],
)
def download_model():
    """
    Pre-download model weights to the Modal Volume.

    Run once before the first deployment:
      modal run modal_vllm.py::download_model
    """
    from huggingface_hub import snapshot_download

    hf_token = os.environ.get("HF_TOKEN")

    target_dir = pathlib.Path(MODEL_CACHE_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=MODEL_NAME,
        local_dir=str(target_dir),
        token=hf_token,
        ignore_patterns=["*.gguf", "*.pt"],
    )

    print(f"Model {MODEL_NAME!r} downloaded to {target_dir}")


# ---------------------------------------------------------------------------
# vLLM serving function
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    gpu="H100",
    volumes={MODEL_DIR: model_volume},
    secrets=[modal.Secret.from_name("aura-vllm-secrets")],
    min_containers=1,
    timeout=7200,
    scaledown_window=300,
)
@modal.web_server(port=VLLM_PORT, startup_timeout=STARTUP_TIMEOUT_SECONDS)
def serve():
    """
    Start the vLLM OpenAI-compatible API server.

    Exposes /v1/chat/completions (and related OpenAI-compatible routes)
    on port 8080.

    After deploying, set in .env:
      VLLM_BASE_URL=https://<your-modal-url>/v1
      VLLM_MODEL=cognitivecomputations/Dolphin3.0-Mistral-24B
    """
    model_path = pathlib.Path(MODEL_CACHE_DIR)

    # Serve from the exact predownloaded directory on the volume if present.
    # Only fall back to the repo name if the local directory is missing/empty.
    if model_path.exists() and any(model_path.iterdir()):
        resolved_model = str(model_path)
    else:
        resolved_model = MODEL_NAME

    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        resolved_model,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
        "--download-dir",
        MODEL_DIR,
        "--max-model-len",
        "8192",
        "--dtype",
        "bfloat16",
        "--gpu-memory-utilization",
        "0.85",
        "--served-model-name",
        MODEL_NAME,
        "--trust-remote-code",
    ]

    print(f"Starting vLLM: {' '.join(cmd)}")
    subprocess.Popen(cmd)