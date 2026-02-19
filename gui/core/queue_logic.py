from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..common.types import QueueItem, QueueSettings


QUEUE_ADD_STATUS_BY_ISSUE = {
    "missing_url": "Queue add failed: missing URL",
    "playlist": "Queue add failed: playlists not allowed",
    "formats": "Queue add failed: formats not loaded",
    "mode": "Queue add failed: choose audio or video mode first",
    "codec": "Queue add failed: choose a codec first",
    "container": "Queue add failed: choose a container first",
    "format": "Queue add failed: choose a format first",
}

QUEUE_ADD_LOG_BY_ISSUE = {
    "missing_url": "[queue] missing URL",
    "playlist": "[queue] playlists cannot be added (use single video URLs)",
    "formats": "[queue] formats not loaded",
    "mode": "[queue] missing mode (audio/video)",
    "codec": "[queue] missing codec",
    "container": "[queue] missing container",
    "format": "[queue] missing format",
}

QUEUE_START_MISSING_DETAIL_BY_ISSUE = {
    "mode": "audio/video mode",
    "codec": "a codec choice",
    "container": "a container choice",
    "format": "a format choice",
}


def queue_settings_issue(settings: Mapping[str, Any]) -> str | None:
    mode = settings.get("mode")
    if mode not in {"audio", "video"}:
        return "mode"
    if mode == "video" and not settings.get("codec_filter"):
        return "codec"
    if not settings.get("format_filter"):
        return "container"
    if not settings.get("format_label"):
        return "format"
    return None


def queue_add_issue(
    *,
    url: str,
    playlist_mode: bool,
    formats_loaded: bool,
    settings: Mapping[str, Any],
) -> str | None:
    if not str(url or "").strip():
        return "missing_url"
    if playlist_mode:
        return "playlist"
    if not formats_loaded:
        return "formats"
    return queue_settings_issue(settings)


def queue_add_feedback(issue: str) -> tuple[str, str]:
    status = QUEUE_ADD_STATUS_BY_ISSUE.get(issue, "Queue add failed")
    log = QUEUE_ADD_LOG_BY_ISSUE.get(issue, "[queue] missing settings")
    return status, log


def queue_start_missing_detail(issue: str) -> str:
    return QUEUE_START_MISSING_DETAIL_BY_ISSUE.get(issue, "settings")


def first_invalid_queue_item(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
) -> tuple[int, str] | None:
    for idx, item in enumerate(queue_items, start=1):
        settings = (item or {}).get("settings") or {}
        issue = queue_settings_issue(settings)
        if issue:
            return (idx, issue)
    return None


def next_non_empty_queue_index(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    start_index: int,
) -> int | None:
    idx = max(0, int(start_index))
    while idx < len(queue_items):
        item = queue_items[idx] or {}
        url = str(item.get("url", "")).strip()
        if url:
            return idx
        idx += 1
    return None


def queue_item(url: str, settings: QueueSettings) -> QueueItem:
    return {"url": str(url), "settings": settings}
