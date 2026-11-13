# Export exact dependencies from the Python virtual environment used to run this project.
# Usage: .\scripts\export_environment.ps1
# Optional: .\scripts\export_environment.ps1 -PythonExe "C:\path\to\.venv\Scripts\python.exe"
param(
    [string]$PythonExe = "I:\Projects\vision_language_robotics_prototype\.venv\Scripts\python.exe"
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $projectRoot
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Cannot find Python at $PythonExe. Activate your environment and rerun with -PythonExe (Get-Command python).Source"
}
Write-Host 'Capturing installed dependencies from:' $PythonExe
& $PythonExe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'pip check failed. Fix incompatible dependencies before exporting.' }
$freeze = & $PythonExe -m pip freeze
if ($LASTEXITCODE -ne 0) { throw 'pip freeze failed.' }
$freeze | Set-Content -Path (Join-Path $projectRoot 'requirements-lock.txt') -Encoding utf8
& $PythonExe -c 'import sys,torch;print("Python:",sys.version.split()[0]);print("PyTorch:",torch.__version__);print("CUDA build:",torch.version.cuda);print("CUDA available:",torch.cuda.is_available());print("GPU:",torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Not found")'
if ($LASTEXITCODE -ne 0) { throw 'PyTorch check failed.' }
Write-Host 'Created requirements-lock.txt. Review it for local paths/private URLs before git add.'
Write-Host 'Note: The lock reflects the shared Python environment, including any unrelated packages.'
