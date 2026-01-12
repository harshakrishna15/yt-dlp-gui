#!/usr/bin/env python3
"""
Cross-platform launcher for the yt-dlp GUI.
Double-click this file or run `python run_gui.py`.
Prefers the local .venv interpreter if present.
"""

import os
import sys
from pathlib import Path


def main() -> None:
    here = Path(__file__).resolve().parent
    repo_root = here
    venv_candidates = [
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "Scripts" / "python.exe",
    ]
    python_bin = next((p for p in venv_candidates if p.exists()), Path(sys.executable))
    package_dir = repo_root / "gui"
    if not package_dir.exists():
        sys.stderr.write("Could not find gui/\n")
        sys.exit(1)
    os.execv(str(python_bin), [str(python_bin), "-m", "gui"])


if __name__ == "__main__":
    main()
