from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from ..common.types import QueueItem


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _item_settings(
    item: QueueItem | Mapping[str, object],
) -> Mapping[str, object]:
    settings = item.get("settings")
    if isinstance(settings, Mapping):
        return settings
    return {}


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


@dataclass(frozen=True)
class QueueListEntry:
    title: str
    meta: str
    tooltip: str


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


def queue_item_display_title(
    item: QueueItem | Mapping[str, object],
    *,
    current_url: str = "",
    current_preview_title: str = "",
) -> str:
    stored_title = _clean_text(item.get("title"))
    if stored_title:
        return stored_title
    item_url = _clean_text(item.get("url"))
    if item_url and item_url == _clean_text(current_url):
        preview_title = _clean_text(current_preview_title)
        if preview_title:
            return preview_title
    return _summary_title_from_url(item_url)


def queue_item_settings_text(item: QueueItem | Mapping[str, object]) -> str:
    settings = _item_settings(item)
    mode = _clean_text(settings.get("mode")).lower()
    container = _clean_text(settings.get("format_filter")).upper()
    codec = _clean_text(settings.get("codec_filter")).upper()
    format_label = _clean_text(settings.get("format_label"))
    playlist_items = _clean_text(settings.get("playlist_items"))
    custom_filename = _clean_text(settings.get("custom_filename"))

    parts: list[str] = []
    if mode == "audio":
        parts.append("Audio")
    elif mode == "video":
        parts.append("Video")
    if container and container != "-":
        parts.append(container)
    if mode == "video" and codec and codec != "-":
        parts.append(codec)
    if format_label and format_label != "-":
        parts.append(format_label)
    if playlist_items:
        parts.append(f"Items {playlist_items}")
    if custom_filename:
        parts.append(f"Save as {custom_filename}")
    return " · ".join(parts)


def build_queue_list_entry(
    item: QueueItem | Mapping[str, object],
    *,
    idx: int,
    active: bool,
    context: QueueSummaryContext | None = None,
) -> QueueListEntry:
    resolved_context = context or QueueSummaryContext()
    title = queue_item_display_title(
        item,
        current_url=resolved_context.current_url,
        current_preview_title=resolved_context.current_preview_title,
    )
    if active:
        current_item_title = _clean_text(resolved_context.current_item_title)
        if current_item_title and current_item_title != "-":
            title = current_item_title
    settings_text = queue_item_settings_text(item)
    meta_parts: list[str] = []
    if active:
        meta_parts.append("Downloading")
    if settings_text:
        meta_parts.append(settings_text)
    meta = " · ".join(meta_parts) or f"Queue item {idx}"
    tooltip_parts = [part for part in (title, meta, _clean_text(item.get("url"))) if part]
    return QueueListEntry(
        title=title or f"Queue item {idx}",
        meta=meta,
        tooltip="\n".join(tooltip_parts),
    )


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
    title = queue_item_display_title(
        item,
        current_url=current_url,
        current_preview_title=current_preview_title,
    )
    if title and title != "Queued item":
        return title
    settings = _item_settings(item)
    format_label = _clean_text(settings.get("format_label"))
    if format_label and format_label != "-":
        return format_label
    return title


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
