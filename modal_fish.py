"""
Project Aura — Fish Audio S2 Pro Modal Service (Phase 12A)

Serves the Fish Audio S2 Pro text-to-speech model via fish-speech's HTTP API.
This is the TTS backend for the investor demo lane.

--- Deployment ---

One-time setup (run from the project root):

  # Optional auth key — pass it as FISH_AUDIO_API_KEY in .env
  modal secret create aura-fish-secrets FISH_AUDIO_API_KEY=your-optional-key

  # Download model checkpoints to a persistent Modal Volume
  modal run modal_fish.py::download_model

  # Deploy the TTS server
  modal deploy modal_fish.py

After deploying, copy the printed web endpoint URL into your .env:
  FISH_AUDIO_URL=https://your-org--aura-fish-serve.modal.run

--- Voice identity ---

FISH_AUDIO_VOICE_ID in .env points to a Fish Audio reference ID.
For an actress voice, upload a reference audio clip to Fish Audio's
voice cloning system to obtain a reference_id, then set that here.
Leave empty to use the default model voice.

--- GPU requirements ---

Fish Audio S2 Pro runs comfortably on an A10G (24 GB VRAM) for single-user
demo traffic. Upgrade to A100 if latency is unacceptable under load.

--- Audio format ---

The server responds with WAV audio by default. This is compatible with
Daily WebRTC's audio pipeline and our FishAudioTTSAdapter.
Change FISH_AUDIO_FORMAT in .env to "opus" for lower bandwidth at the cost
of an additional transcode step on the client side.
"""

import os
import pathlib
import subprocess
import sys

import modal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FISH_SPEECH_VERSION = "v1.4.2"
FISH_SPEECH_REPO = "https://github.com/fishaudio/fish-speech.git"
APP_DIR = "/app/fish-speech"
MODEL_DIR = "/models/fish-speech"
FISH_PORT = 8080

# Fish-Speech 1.4 decoder checkpoint filename
DECODER_FILENAME = "firefly-gan-vq-fsq-8x1024-21hz-generator.pth"
DECODER_CONFIG_NAME = "firefly_gan_vq"

app = modal.App("aura-fish")

model_volume = modal.Volume.from_name("aura-fish-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "git",
        "ffmpeg",
        "libsndfile1",
        "portaudio19-dev",
        "libportaudio2",
        "libportaudiocpp0",
        "libasound2-dev",
    )
    .run_commands(
        f"git clone --depth 1 --branch {FISH_SPEECH_VERSION} {FISH_SPEECH_REPO} {APP_DIR}",
        # Pin a known-good torch/torchaudio pair first for CUDA 12.8
        "pip install --no-cache-dir torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128",
        # Then install fish-speech itself on top of that environment
        f"cd {APP_DIR} && pip install -e '.[api]' --no-cache-dir",
        # Simple version sanity check
        "python -c \"import torch, torchaudio; print('torch=', torch.__version__); print('torchaudio=', torchaudio.__version__)\"",
    )
    .pip_install(
        "huggingface-hub>=0.22",
        "soundfile",
        "numpy",
    )
    .env({"HF_HOME": MODEL_DIR})
)


@app.function(
    image=image,
    gpu="A10",
    volumes={MODEL_DIR: model_volume},
    timeout=1800,
    secrets=[modal.Secret.from_name("aura-fish-secrets")],
)
def download_model():
    """
    Pre-download Fish Audio S2 Pro checkpoint to the Modal Volume.

    Run once before the first deployment:
      modal run modal_fish.py::download_model
    """
    from huggingface_hub import snapshot_download

    hf_token = os.environ.get("HF_TOKEN")
    snapshot_download(
        repo_id="fishaudio/fish-speech-1.4",
        local_dir=f"{MODEL_DIR}/fish-speech-1.4",
        token=hf_token,
        ignore_patterns=["*.gguf"],
    )
    print(f"Fish Audio model downloaded to {MODEL_DIR}/fish-speech-1.4")


@app.function(
    image=image,
    gpu="A10",
    volumes={MODEL_DIR: model_volume},
    secrets=[modal.Secret.from_name("aura-fish-secrets")],
    min_containers=1,
    timeout=3600,
    scaledown_window=300,
)
@modal.web_server(port=FISH_PORT, startup_timeout=300)
def serve():
    """
    Start the fish-speech HTTP API server.

    Exposes /v1/tts (POST) and /health (GET) on port 8080.
    The FishAudioTTSAdapter in app/adapters/tts.py calls /v1/tts directly.

    After deploying, set in .env:
      FISH_AUDIO_URL=https://<your-modal-url>
    """
    checkpoint_dir = pathlib.Path(f"{MODEL_DIR}/fish-speech-1.4")
    decoder_checkpoint = checkpoint_dir / DECODER_FILENAME

    if not checkpoint_dir.exists():
        raise RuntimeError(
            f"Llama checkpoint directory not found at {checkpoint_dir}. "
            "Run: modal run modal_fish.py::download_model"
        )

    if not decoder_checkpoint.exists():
        raise RuntimeError(
            f"Decoder checkpoint not found at {decoder_checkpoint}. "
            "Run: modal run modal_fish.py::download_model and verify the downloaded files."
        )

    listen_addr = f"0.0.0.0:{FISH_PORT}"

    cmd = [
        sys.executable,
        "-m",
        "tools.api",
        "--listen",
        listen_addr,
        "--llama-checkpoint-path",
        str(checkpoint_dir),
        "--decoder-checkpoint-path",
        str(decoder_checkpoint),
        "--decoder-config-name",
        DECODER_CONFIG_NAME,
        "--device",
        "cuda",
    ]

    print(f"Starting fish-speech API: {' '.join(cmd)}")
    subprocess.Popen(cmd, cwd=APP_DIR)