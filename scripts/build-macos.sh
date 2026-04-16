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
BUNDLE_ID="$(python3 -c 'from gui.app_meta import APP_BUNDLE_IDENTIFIER; print(APP_BUNDLE_IDENTIFIER)')"

# Remove prior outputs to avoid interactive delete prompts and stale locks.
rm -rf build dist

# Generate a fresh macOS app icon for the app bundle.
python3 scripts/make-macos-icon.py --output build/yt-dlp-gui-icon.icns --size 1024 --variant macos

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "yt-dlp-gui" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --icon "build/yt-dlp-gui-icon.icns" \
  --hidden-import "PySide6.QtSvg" \
  --add-data "gui/qt/assets:gui/qt/assets" \
  pyinstaller_entry.py

echo "Build complete: dist/yt-dlp-gui.app"
