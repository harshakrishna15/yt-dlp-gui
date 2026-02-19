from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from collections.abc import Sequence


def _legacy_tk_module_name() -> str:
    if __package__:
        return f"{__package__}.tkinter.app"
    return "gui.tkinter.app"


def _has_legacy_tk_frontend() -> bool:
    return importlib.util.find_spec(_legacy_tk_module_name()) is not None


def _ui_choices() -> tuple[str, ...]:
    if _has_legacy_tk_frontend():
        return ("qt", "tk")
    return ("qt",)


def _build_parser() -> argparse.ArgumentParser:
    ui_choices = _ui_choices()
    help_suffix = ""
    if "tk" in ui_choices:
        help_suffix = " tk is legacy/compatibility only."

    parser = argparse.ArgumentParser(prog="python -m gui")
    parser.add_argument(
        "--ui",
        choices=ui_choices,
        default="qt",
        help=f"Choose GUI frontend (default: qt).{help_suffix}",
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


def _run_tk() -> int:
    if not _has_legacy_tk_frontend():
        sys.stderr.write("Tk frontend is not available in this build.\n")
        return 2

    sys.stderr.write(
        "[legacy] Tk frontend is kept for compatibility and is no longer under active development.\n"
    )
    tk_module = importlib.import_module(".tkinter.app", package=__package__)
    tk_main = tk_module.main

    tk_main()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    if args.ui == "tk":
        return _run_tk()
    return _run_qt()
