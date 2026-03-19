from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from ..common.types import QueueItem

_IGNORED_SOURCE_SUBTITLE = "Choose export settings to start downloading."


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _item_settings(
    item: QueueItem | Mapping[str, object],
) -> Mapping[str, object]:
    settings = item.get("settings")
    if isinstance(settings, Mapping):
        return settings
    return {}


def normalize_source_summary(
    summary: Mapping[str, object] | None,
) -> dict[str, str] | None:
    if not isinstance(summary, Mapping):
        return None
    return {
        "badge_text": _clean_text(summary.get("badge_text")),
        "eyebrow_text": _clean_text(summary.get("eyebrow_text")),
        "subtitle_text": _clean_text(summary.get("subtitle_text")),
        "detail_one_text": _clean_text(summary.get("detail_one_text")),
        "detail_two_text": _clean_text(summary.get("detail_two_text")),
        "detail_three_text": _clean_text(summary.get("detail_three_text")),
    }


@dataclass(frozen=True)
class QueuePreviewInputs:
    url: str = ""
    preview_title: str = ""
    source_summary: Mapping[str, object] | None = None
    playlist_mode: bool = False
    mode: str = ""
    container: str = ""
    is_fetching: bool = False
    has_filtered_formats: bool = False
    selected_quality: str = ""
    folder_text: str = ""
    queue_count: int = 0
    playlist_items: str = ""


@dataclass(frozen=True)
class QueuePreviewModel:
    badge_text: str
    heading_text: str
    placeholder_text: str
    subtitle_text: str
    detail_one_text: str
    detail_two_text: str
    detail_three_text: str


def build_queue_preview_model(inputs: QueuePreviewInputs) -> QueuePreviewModel:
    summary = normalize_source_summary(inputs.source_summary) or {}
    url = _clean_text(inputs.url)
    preview_title = _clean_text(inputs.preview_title)
    mode = _clean_text(inputs.mode).lower()
    container = _clean_text(inputs.container).upper()
    playlist_items = _clean_text(inputs.playlist_items)
    selected_quality = _clean_text(inputs.selected_quality) or "Auto quality"
    folder_text = _clean_text(inputs.folder_text) or "Output folder"

    badge = _clean_text(summary.get("badge_text")).upper()
    if badge:
        badge_text = badge
    elif inputs.playlist_mode:
        badge_text = "LIST"
    elif mode == "audio":
        badge_text = "AUD"
    elif mode == "video":
        badge_text = "VID"
    elif url:
        badge_text = "URL"
    else:
        badge_text = "PLAN"

    if preview_title:
        heading_text = "Ready to queue"
    elif url:
        heading_text = "Next queue item"
    else:
        heading_text = "Download plan"

    if url:
        placeholder_text = "Analyze the URL to confirm formats and availability."
    else:
        placeholder_text = "Paste a URL to build the next queue item."

    subtitle_parts: list[str] = []
    raw_subtitle = _clean_text(summary.get("subtitle_text"))
    if raw_subtitle and raw_subtitle != _IGNORED_SOURCE_SUBTITLE:
        subtitle_parts.append(raw_subtitle)
    detail_two = _clean_text(summary.get("detail_two_text"))
    if detail_two:
        subtitle_parts.append(detail_two)
    if subtitle_parts:
        subtitle_text = " · ".join(subtitle_parts)
    elif url:
        subtitle_text = (
            "Format, folder, and queue status stay pinned here while you work."
        )
    else:
        subtitle_text = "Set defaults once, then keep adding items to the queue."

    if not mode:
        detail_one_text = "Choose mode"
    else:
        detail_one_parts = ["Audio" if mode == "audio" else "Video"]
        if container:
            detail_one_parts.append(container)
        if inputs.is_fetching:
            detail_one_parts.append("Loading formats")
        elif inputs.has_filtered_formats:
            detail_one_parts.append(selected_quality)
        elif url:
            detail_one_parts.append("Analyze for quality")
        detail_one_text = " • ".join(detail_one_parts)

    if inputs.playlist_mode:
        detail_three_text = (
            f"Items {playlist_items}" if playlist_items else "All playlist items"
        )
    elif inputs.queue_count <= 0:
        detail_three_text = "Queue empty"
    else:
        suffix = "item" if inputs.queue_count == 1 else "items"
        detail_three_text = f"{inputs.queue_count} queued {suffix}"

    return QueuePreviewModel(
        badge_text=badge_text,
        heading_text=heading_text,
        placeholder_text=placeholder_text,
        subtitle_text=subtitle_text,
        detail_one_text=detail_one_text,
        detail_two_text=folder_text,
        detail_three_text=detail_three_text,
    )


@dataclass(frozen=True)
class QueueSummaryContext:
    current_url: str = ""
    current_preview_title: str = ""
    current_item_title: str = ""
    progress_text: str = ""
    speed_text: str = ""
    eta_text: str = ""


@dataclass(frozen=True)
class QueueSummaryEntry:
    list_text: str
    badge_text: str
    title: str
    meta: str
    status_text: str
    tone: str


def queue_badge_for_mode(mode: str) -> str:
    normalized = _clean_text(mode).lower()
    if normalized == "audio":
        return "AUD"
    if normalized == "video":
        return "VID"
    return "URL"


def build_queue_list_text(
    item: QueueItem | Mapping[str, object], *, idx: int, active: bool
) -> str:
    settings = _item_settings(item)
    prefix = "> " if active else ""
    url = _clean_text(item.get("url"))
    mode = _clean_text(settings.get("mode")) or "-"
    container = _clean_text(settings.get("format_filter")) or "-"
    codec = _clean_text(settings.get("codec_filter")) or "-"
    label = _clean_text(settings.get("format_label")) or "-"
    return f"{prefix}{idx}. {url} [{mode}/{container}/{codec}] {label}"


def _summary_title_from_url(url: str) -> str:
    clean = _clean_text(url)
    if not clean:
        return "Queued item"
    parsed = urlparse(clean)
    query = parse_qs(parsed.query)
    if "v" in query and query["v"]:
        host = parsed.netloc.replace("www.", "") or "youtube"
        return f"{host} · {query['v'][0]}"
    path = parsed.path.strip("/") or parsed.netloc or clean
    compact_path = re.sub(r"\s+", " ", path).strip()
    if len(compact_path) > 48:
        return f"{compact_path[:45].rstrip()}..."
    return compact_path


def _queue_summary_title(
    item: QueueItem | Mapping[str, object],
    *,
    current_url: str,
    current_preview_title: str,
) -> str:
    settings = _item_settings(item)
    custom_filename = _clean_text(settings.get("custom_filename"))
    if custom_filename:
        return custom_filename
    item_url = _clean_text(item.get("url"))
    if item_url and item_url == _clean_text(current_url):
        preview_title = _clean_text(current_preview_title)
        if preview_title:
            return preview_title
    format_label = _clean_text(settings.get("format_label"))
    if format_label and format_label != "-":
        return format_label
    return _summary_title_from_url(item_url)


def _queue_summary_meta(item: QueueItem | Mapping[str, object], *, idx: int) -> str:
    settings = _item_settings(item)
    mode = _clean_text(settings.get("mode")).lower()
    mode_text = "Audio only" if mode == "audio" else "Video & audio"
    container = _clean_text(settings.get("format_filter")).upper()
    format_label = _clean_text(settings.get("format_label"))
    parts: list[str] = []
    if container and container != "-":
        parts.append(container)
    if format_label and format_label != "-":
        parts.append(format_label)
    parts.append(mode_text)
    return " · ".join(part for part in parts if part) or f"Queue item {idx}"


def metric_value(label_text: str, prefix: str, fallback: str = "") -> str:
    text = _clean_text(label_text)
    if not text.startswith(prefix):
        return fallback
    value = text[len(prefix) :].strip()
    if not value or value == "-":
        return fallback
    return value


def _queue_active_summary_meta(
    item: QueueItem | Mapping[str, object], *, idx: int, context: QueueSummaryContext
) -> str:
    parts: list[str] = []
    progress = metric_value(context.progress_text, "Progress:")
    speed = metric_value(context.speed_text, "Speed:")
    eta = metric_value(context.eta_text, "ETA:")
    if progress:
        parts.append(progress)
    if speed:
        parts.append(speed)
    if eta:
        parts.append(f"ETA {eta}")

    settings = _item_settings(item)
    container = _clean_text(settings.get("format_filter")).upper()
    format_label = _clean_text(settings.get("format_label"))
    if container and container != "-":
        parts.append(container)
    if format_label and format_label != "-":
        parts.append(format_label)
    if parts:
        return " · ".join(parts)
    return _queue_summary_meta(item, idx=idx)


def build_queue_summary_entry(
    item: QueueItem | Mapping[str, object],
    *,
    idx: int,
    active: bool,
    context: QueueSummaryContext | None = None,
) -> QueueSummaryEntry:
    resolved_context = context or QueueSummaryContext()
    settings = _item_settings(item)
    title = _queue_summary_title(
        item,
        current_url=resolved_context.current_url,
        current_preview_title=resolved_context.current_preview_title,
    )
    if active:
        current_item_title = _clean_text(resolved_context.current_item_title)
        if current_item_title and current_item_title != "-":
            title = current_item_title
        meta = _queue_active_summary_meta(item, idx=idx, context=resolved_context)
        status_text = "Downloading"
        tone = "active"
    else:
        meta = _queue_summary_meta(item, idx=idx)
        status_text = "Queued"
        tone = "default"
    return QueueSummaryEntry(
        list_text=build_queue_list_text(item, idx=idx, active=active),
        badge_text=queue_badge_for_mode(_clean_text(settings.get("mode"))),
        title=title,
        meta=meta,
        status_text=status_text,
        tone=tone,
    )
