#!/usr/bin/env bash
set -e
ROOT="$(cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-python3}"

echo "Creating venv with $PYTHON_BIN..."
$PYTHON_BIN -m venv .venv
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing requirements..."
pip install -r requirements.txt

cat <<'EOM'
Setup complete.
- Activate: source .venv/bin/activate
- Run: python run_gui.py
If you see _tkinter errors, install a Python build with Tk (e.g., python.org installer or Homebrew python-tk).
EOM
