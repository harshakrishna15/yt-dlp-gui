from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths


def system_downloads_path() -> Path:
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    ).strip()
    if location:
        return Path(location).expanduser()
    return Path.home() / "Downloads"
