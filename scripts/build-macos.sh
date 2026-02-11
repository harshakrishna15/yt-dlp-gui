#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment at .venv"
  python3 -m venv .venv
fi

source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

# Remove prior outputs to avoid interactive delete prompts and stale locks.
rm -rf build dist

python3 -m PyInstaller --noconfirm --clean yt-dlp-gui.spec

echo "Build complete: dist/yt-dlp-gui.app"
