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
    if mode == "audio":
        return None
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


def normalize_selected_indices(
    selected_indices: Sequence[int],
    *,
    queue_length: int,
) -> list[int]:
    max_length = max(0, int(queue_length))
    unique: set[int] = set()
    normalized: list[int] = []
    for raw in selected_indices:
        idx = int(raw)
        if idx < 0 or idx >= max_length or idx in unique:
            continue
        unique.add(idx)
        normalized.append(idx)
    normalized.sort()
    return normalized


def remove_selected_queue_items(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    selected_indices: Sequence[int],
) -> list[QueueItem]:
    items: list[QueueItem] = [dict(item or {}) for item in queue_items]
    for idx in sorted(set(int(i) for i in selected_indices), reverse=True):
        if 0 <= idx < len(items):
            items.pop(idx)
    return items


def move_selected_queue_items_up(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    selected_indices: Sequence[int],
) -> tuple[list[QueueItem], bool]:
    items: list[QueueItem] = [dict(item or {}) for item in queue_items]
    moved = False
    for idx in normalize_selected_indices(selected_indices, queue_length=len(items)):
        if idx <= 0 or idx >= len(items):
            continue
        items[idx - 1], items[idx] = items[idx], items[idx - 1]
        moved = True
    return items, moved


def move_selected_queue_items_down(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    selected_indices: Sequence[int],
) -> tuple[list[QueueItem], bool]:
    items: list[QueueItem] = [dict(item or {}) for item in queue_items]
    moved = False
    ordered = normalize_selected_indices(selected_indices, queue_length=len(items))
    for idx in reversed(ordered):
        if idx < 0 or idx >= len(items) - 1:
            continue
        items[idx + 1], items[idx] = items[idx], items[idx + 1]
        moved = True
    return items, moved


def reorder_queue_items(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    item_order: Sequence[int],
) -> tuple[list[QueueItem], bool]:
    items: list[QueueItem] = [dict(item or {}) for item in queue_items]
    if len(item_order) != len(items):
        return items, False

    normalized: list[int] = []
    seen: set[int] = set()
    for raw_index in item_order:
        index = int(raw_index)
        if index in seen or index < 0 or index >= len(items):
            return items, False
        seen.add(index)
        normalized.append(index)

    if normalized == list(range(len(items))):
        return items, False
    return [items[index] for index in normalized], True


def clear_queue_items(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
) -> tuple[list[QueueItem], bool]:
    if not queue_items:
        return [], False
    return [], True
