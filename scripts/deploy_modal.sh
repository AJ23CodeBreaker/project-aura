#!/usr/bin/env bash
# Project Aura — Modal Deployment Script (bash)
#
# STUB: review all steps before running. Not yet verified against a live account.
# Run from the repository root.

set -euo pipefail

echo "Project Aura — Modal deploy"

# ---------------------------------------------------------------------------
# Step 1: Activate virtual environment
# ---------------------------------------------------------------------------
source "$(dirname "$0")/../.venv/bin/activate"

# ---------------------------------------------------------------------------
# Step 2: Authenticate with Modal (run once per machine)
# ---------------------------------------------------------------------------
# modal token new

# ---------------------------------------------------------------------------
# Step 3: Create Modal secrets (run once, before first deploy)
# ---------------------------------------------------------------------------
# modal secret create project-aura-secrets \
#   SESSION_SECRET_KEY="your-session-secret-here" \
#   ADULT_MODE_ENABLED="false"
#
# Add provider keys once selected (Phase 3+):
# modal secret create project-aura-secrets \
#   STT_API_KEY="..." \
#   LLM_API_KEY="..." \
#   TTS_API_KEY="..." \
#   REDIS_URL="..."

# ---------------------------------------------------------------------------
# Step 4: Deploy
# ---------------------------------------------------------------------------
echo "Deploying modal_app.py ..."
modal deploy modal_app.py

echo "Deploy complete."
