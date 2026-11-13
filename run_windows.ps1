param([string]$VenvPath = 'I:\Projects\vision_language_robotics_prototype\.venv')
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$Python=Join-Path $VenvPath 'Scripts\python.exe'
if (-not (Test-Path $Python)) { throw "Python env not found: $Python" }
& $Python -m streamlit run app.py
