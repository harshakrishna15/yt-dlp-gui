from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_ASSET_FILENAMES = (
    "combo-down-arrow.svg",
    "downloads.svg",
    "downloads-active.svg",
    "settings.svg",
    "settings-active.svg",
    "queue.svg",
    "queue-active.svg",
    "logs.svg",
    "logs-active.svg",
    "logs-alert.svg",
    "tmp-mac-app-icon.png",
    "tmp-windows-app-icon.png",
)


def candidate_assets_dirs() -> tuple[Path, ...]:
    module_assets = Path(__file__).resolve().parent / "assets"
    candidates: list[Path] = [module_assets]
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        root = Path(bundle_root)
        candidates.extend(
            [
                root / "gui" / "qt" / "assets",
                root / "_internal" / "gui" / "qt" / "assets",
            ]
        )
    return tuple(candidates)


def assets_dir() -> Path:
    for candidate in candidate_assets_dirs():
        if candidate.is_dir():
            return candidate
    return candidate_assets_dirs()[0]


def asset_path(filename: str) -> Path:
    for directory in candidate_assets_dirs():
        path = directory / filename
        if path.is_file():
            return path
    return assets_dir() / filename
