from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from . import queue_logic as core_queue_logic
from ..common.types import QueueItem

SINGLE_START_TITLE_BY_ISSUE = {
    "missing_url": "Missing URL",
    "formats_unavailable": "Formats unavailable",
}

SINGLE_START_MESSAGE_BY_ISSUE = {
    "missing_url": "Please paste a video URL to download.",
    "formats_unavailable": "Formats have not been loaded yet.",
}


def single_start_issue(*, url: str, formats_loaded: bool) -> str | None:
    if not str(url or "").strip():
        return "missing_url"
    if not formats_loaded:
        return "formats_unavailable"
    return None


def single_start_error_text(issue: str) -> tuple[str, str]:
    return (
        SINGLE_START_TITLE_BY_ISSUE.get(issue, "Download unavailable"),
        SINGLE_START_MESSAGE_BY_ISSUE.get(issue, "Download cannot start right now."),
    )


@dataclass(frozen=True)
class QueueStartCheck:
    can_start: bool
    invalid_index: int | None = None
    invalid_issue: str | None = None


def validate_queue_start(
    *,
    is_downloading: bool,
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
) -> QueueStartCheck:
    if is_downloading or not queue_items:
        return QueueStartCheck(can_start=False)
    invalid = core_queue_logic.first_invalid_queue_item(queue_items)
    if invalid is None:
        return QueueStartCheck(can_start=True)
    idx, issue = invalid
    return QueueStartCheck(
        can_start=False,
        invalid_index=idx,
        invalid_issue=issue,
    )


@dataclass(frozen=True)
class QueueRunItem:
    index: int
    display_index: int
    total: int
    url: str
    settings: Mapping[str, Any]


def next_queue_run_item(
    queue_items: Sequence[QueueItem | Mapping[str, Any]],
    start_index: int,
) -> QueueRunItem | None:
    index = core_queue_logic.next_non_empty_queue_index(queue_items, start_index)
    if index is None:
        return None
    item = queue_items[index] or {}
    return QueueRunItem(
        index=index,
        display_index=index + 1,
        total=len(queue_items),
        url=str(item.get("url", "")).strip(),
        settings=item.get("settings") or {},
    )


@dataclass(frozen=True)
class QueueProgressUpdate:
    failed_items: int
    cancel_requested: bool
    should_finish: bool
    finish_cancelled: bool
    next_index: int | None = None


def advance_queue_progress(
    *,
    queue_length: int,
    current_index: int,
    failed_items: int,
    cancel_requested: bool,
    had_error: bool,
    cancelled: bool,
) -> QueueProgressUpdate:
    next_failed_items = failed_items + (1 if had_error else 0)
    next_cancel_requested = cancel_requested or cancelled
    if next_cancel_requested:
        return QueueProgressUpdate(
            failed_items=next_failed_items,
            cancel_requested=True,
            should_finish=True,
            finish_cancelled=True,
            next_index=None,
        )
    next_index = current_index + 1
    if next_index >= max(0, int(queue_length)):
        return QueueProgressUpdate(
            failed_items=next_failed_items,
            cancel_requested=False,
            should_finish=True,
            finish_cancelled=False,
            next_index=None,
        )
    return QueueProgressUpdate(
        failed_items=next_failed_items,
        cancel_requested=False,
        should_finish=False,
        finish_cancelled=False,
        next_index=next_index,
    )


def queue_finish_outcome(*, cancelled: bool, failed_items: int) -> str:
    if cancelled:
        return "cancelled"
    if failed_items:
        return "failed"
    return "success"
