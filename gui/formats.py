from __future__ import annotations

from typing import Any

try:
    from .shared_types import FormatInfo
except ImportError:  # Support running as a script (python gui/app.py)
    from shared_types import FormatInfo  # type: ignore


def formats_from_info(info: dict[str, Any]) -> list[FormatInfo]:
    entry: dict[str, Any] = info
    if info.get("_type") == "playlist" and info.get("entries"):
        entry = info["entries"][0] or {}
    return entry.get("formats") or []

