# Reuse your existing environment. This script NEVER installs a new copy of PyTorch.
param([string]$VenvPath = 'I:\Projects\vision_language_robotics_prototype\.venv')
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$Python=Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $Python)) { throw "Python env not found: $Python" }
& $Python --version
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
& $Python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency conflict' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $Python scripts\run_demo.py
if ($LASTEXITCODE -ne 0) { throw 'Demo output generation failed' }
Write-Host 'Setup complete! Launch with:' -ForegroundColor Green
Write-Host ('& "'+$Python+'" -m streamlit run app.py')
