from __future__ import annotations

from typing import Any, TypedDict, TypeAlias

FormatInfo: TypeAlias = dict[str, Any]
FormatLookup: TypeAlias = dict[str, FormatInfo]


class FormatsCacheEntry(TypedDict):
    video_labels: list[str]
    video_lookup: FormatLookup
    audio_labels: list[str]
    audio_lookup: FormatLookup


class ProgressUpdate(TypedDict, total=False):
    status: str
    percent: float | None
    speed: str
    eta: str
