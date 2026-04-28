cd C:\project-aura
.\.venv\Scripts\Activate.ps1

Write-Host "Deploying aura-vllm..."
modal deploy modal_vllm.py
if ($LASTEXITCODE -ne 0) { throw "aura-vllm deploy failed" }

Write-Host "Deploying aura-fish..."
modal deploy modal_fish.py
if ($LASTEXITCODE -ne 0) { throw "aura-fish deploy failed" }

Write-Host "Deploying project-aura-fresh..."
modal deploy modal_app.py
if ($LASTEXITCODE -ne 0) { throw "project-aura-fresh deploy failed" }

Write-Host ""
Write-Host "Current Modal apps:"
modal app list

Write-Host ""
Write-Host "Starting the frontend server:"
python -m http.server 5500 --directory frontend