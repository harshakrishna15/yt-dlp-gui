from __future__ import annotations

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
)


def assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets"
