from __future__ import annotations

from typing import Any

from .types import FormatInfo


def formats_from_info(info: dict[str, Any]) -> list[FormatInfo]:
    entry: dict[str, Any] = info
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = info.get("entries")
        try:
            entry = next(iter(entries), {}) if entries is not None else {}
        except TypeError:
            entry = {}
    return entry.get("formats") or []
