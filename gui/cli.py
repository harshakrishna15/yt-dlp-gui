from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m gui")
    parser.add_argument(
        "--ui",
        choices=("qt",),
        default="qt",
        help="Choose GUI frontend (default: qt).",
    )
    return parser


def _run_qt() -> int:
    try:
        from .qt import app as qt_app
    except ModuleNotFoundError as exc:
        missing = str(getattr(exc, "name", "") or "")
        if missing.startswith("PySide6"):
            sys.stderr.write(
                "PySide6 is not installed. Install app dependencies and retry:\n"
                "  pip install -r requirements.txt\n"
            )
            return 2
        raise
    return int(qt_app.main())


def main(argv: Sequence[str] | None = None) -> int:
    _build_parser().parse_args(list(argv) if argv is not None else None)
    return _run_qt()
