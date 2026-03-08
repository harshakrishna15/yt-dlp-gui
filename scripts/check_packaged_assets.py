#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.qt.assets_manifest import REQUIRED_ASSET_FILENAMES


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify that packaged Qt asset files are present in a build output."
    )
    parser.add_argument(
        "bundle_dir",
        help="Path to the packaged app directory (for example dist/yt-dlp-gui.app or dist/pyinstaller_entry).",
    )
    return parser


def candidate_assets_dirs(bundle_dir: Path) -> tuple[Path, ...]:
    return (
        bundle_dir / "gui" / "qt" / "assets",
        bundle_dir / "_internal" / "gui" / "qt" / "assets",
        bundle_dir / "Contents" / "Resources" / "gui" / "qt" / "assets",
        bundle_dir / "Contents" / "Frameworks" / "gui" / "qt" / "assets",
        bundle_dir / "Contents" / "Frameworks" / "_internal" / "gui" / "qt" / "assets",
        bundle_dir / "Contents" / "MacOS" / "_internal" / "gui" / "qt" / "assets",
    )


def find_assets_dir(bundle_dir: Path) -> Path | None:
    for candidate in candidate_assets_dirs(bundle_dir):
        if candidate.is_dir():
            return candidate
    return None


def missing_required_assets(assets_dir: Path) -> list[str]:
    missing: list[str] = []
    for filename in REQUIRED_ASSET_FILENAMES:
        if not (assets_dir / filename).is_file():
            missing.append(filename)
    return missing


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    bundle_dir = Path(args.bundle_dir).expanduser().resolve()
    if not bundle_dir.exists():
        sys.stderr.write(f"[missing] bundle directory not found: {bundle_dir}\n")
        return 1

    assets_dir = find_assets_dir(bundle_dir)
    if assets_dir is None:
        sys.stderr.write(
            "[missing] could not find packaged asset directory at:\n"
        )
        for candidate in candidate_assets_dirs(bundle_dir):
            sys.stderr.write(f"  - {candidate}\n")
        return 1

    missing = missing_required_assets(assets_dir)
    if missing:
        sys.stderr.write(
            f"[missing] packaged assets directory is incomplete: {assets_dir}\n"
        )
        for filename in missing:
            sys.stderr.write(f"  - {filename}\n")
        return 1

    sys.stdout.write(f"[ok] packaged assets present: {assets_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
