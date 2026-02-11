$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

function Get-SystemPython {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return @{
      Command = "py"
      Args = @("-3")
    }
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return @{
      Command = "python"
      Args = @()
    }
  }
  if (Get-Command python3 -ErrorAction SilentlyContinue) {
    return @{
      Command = "python3"
      Args = @()
    }
  }

  throw "No Python interpreter found in PATH. Install Python 3 and ensure py/python is available."
}

$PythonCmd = Get-SystemPython

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment at .venv"
  & $PythonCmd.Command @($PythonCmd.Args) -m venv .venv
}

$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment Python not found at $VenvPython"
}

# Guardrail: refuse package installs unless running in a virtual environment.
$env:PIP_REQUIRE_VIRTUALENV = "true"

& $VenvPython -m pip install -r requirements.txt
& $VenvPython -m pip install pyinstaller
& $VenvPython -m PyInstaller yt-dlp-gui.spec

Write-Host "Build complete: dist\yt-dlp-gui\yt-dlp-gui.exe"
