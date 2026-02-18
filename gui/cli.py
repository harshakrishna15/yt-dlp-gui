from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m gui")
    parser.add_argument(
        "--ui",
        choices=("tk", "qt"),
        default="tk",
        help="Choose GUI frontend (default: tk).",
    )
    return parser


def _run_qt() -> int:
    try:
        from . import qt_app
    except ModuleNotFoundError as exc:
        missing = str(getattr(exc, "name", "") or "")
        if missing.startswith("PySide6"):
            sys.stderr.write(
                "PySide6 is not installed. Install optional Qt deps and retry:\n"
                "  pip install -r requirements-qt.txt\n"
            )
            return 2
        raise
    return int(qt_app.main())


def _run_tk() -> int:
    from .app import main as tk_main

    tk_main()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    if args.ui == "qt":
        return _run_qt()
    return _run_tk()
