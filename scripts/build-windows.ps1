$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment at .venv"
  py -3 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller yt-dlp-gui.spec

Write-Host "Build complete: dist\yt-dlp-gui\yt-dlp-gui.exe"
