# Project Aura — Modal Deployment Script (PowerShell)
#
# STUB: review all steps before running. Not yet verified against a live account.
# Run from the repository root.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Project Aura — Modal deploy" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Step 1: Activate virtual environment
# ---------------------------------------------------------------------------
$activateScript = Join-Path $PSScriptRoot ".." ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    Write-Error "Virtual environment not found. Run: python -m venv .venv && pip install -r requirements.txt"
}

# ---------------------------------------------------------------------------
# Step 2: Authenticate with Modal (run once per machine)
# ---------------------------------------------------------------------------
# Uncomment and run the first time only:
# modal token new

# ---------------------------------------------------------------------------
# Step 3: Create Modal secrets (run once, before first deploy)
#
# Replace placeholder values with real ones before running.
# Add provider keys here as they are selected in Phase 3+.
# ---------------------------------------------------------------------------
# modal secret create project-aura-secrets `
#   SESSION_SECRET_KEY="your-session-secret-here" `
#   ADULT_MODE_ENABLED="false"
#
# Add provider keys once selected:
# modal secret create project-aura-secrets `
#   STT_API_KEY="..." `
#   LLM_API_KEY="..." `
#   TTS_API_KEY="..." `
#   REDIS_URL="..."

# ---------------------------------------------------------------------------
# Step 4: Deploy
# ---------------------------------------------------------------------------
Write-Host "Deploying modal_app.py ..." -ForegroundColor Yellow
modal deploy modal_app.py

Write-Host "Deploy complete." -ForegroundColor Green
