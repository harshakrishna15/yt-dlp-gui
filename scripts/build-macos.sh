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
python3 -m pip install pyinstaller pillow

# Remove prior outputs to avoid interactive delete prompts and stale locks.
rm -rf build dist

# Generate a fresh macOS app icon for the app bundle.
python3 scripts/make-macos-icon.py --output build/yt-dlp-gui-icon.png --size 1024

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "yt-dlp-gui" \
  --icon "build/yt-dlp-gui-icon.png" \
  --add-data "font:font" \
  pyinstaller_entry.py

echo "Build complete: dist/yt-dlp-gui.app"
