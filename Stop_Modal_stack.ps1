cd C:\project-aura
.\.venv\Scripts\Activate.ps1

Write-Host "Stopping old app (optional fallback)..."
modal app stop -y project-aura

Write-Host "Stopping active main backend..."
modal app stop -y project-aura-fresh

Write-Host "Stopping Fish TTS..."
modal app stop -y aura-fish

Write-Host "Stopping vLLM..."
modal app stop -y aura-vllm

Write-Host ""
Write-Host "Remaining Modal apps:"
modal app list
