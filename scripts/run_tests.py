#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run project unittests with clean Ctrl+C handling.")
    parser.add_argument(
        "-s",
        "--start-directory",
        default="tests",
        help="Directory to start discovery from (default: tests)",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default="test*.py",
        help="Pattern for test files (default: test*.py)",
    )
    parser.add_argument(
        "-t",
        "--top-level-directory",
        default=None,
        help="Top-level directory of project (optional)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="Increase output verbosity (-v, -vv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    verbosity = max(1, int(args.verbose))
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    start_dir = Path(args.start_directory)
    if not start_dir.is_absolute():
        start_dir = repo_root / start_dir
    top_level_dir = (
        str(Path(args.top_level_directory).resolve())
        if args.top_level_directory
        else None
    )

    try:
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(start_dir),
            pattern=args.pattern,
            top_level_dir=top_level_dir,
        )
        result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
        return 0 if result.wasSuccessful() else 1
    except KeyboardInterrupt:
        sys.stderr.write("\n[interrupted] Test run cancelled by user.\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
