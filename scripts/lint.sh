#!/usr/bin/env bash
set -euo pipefail

if ! python3 -m ruff --version >/dev/null 2>&1; then
  echo "ruff is not installed. Run: pip install -r requirements-dev.txt" >&2
  exit 1
fi
if ! python3 -m black --version >/dev/null 2>&1; then
  echo "black is not installed. Run: pip install -r requirements-dev.txt" >&2
  exit 1
fi

python3 -m ruff check .
python3 -m black --check .
