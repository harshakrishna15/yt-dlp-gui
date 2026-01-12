from __future__ import annotations

from typing import Any

from .shared_types import FormatInfo


def formats_from_info(info: dict[str, Any]) -> list[FormatInfo]:
    entry: dict[str, Any] = info
    if info.get("_type") == "playlist" and info.get("entries"):
        entry = info["entries"][0] or {}
    return entry.get("formats") or []
