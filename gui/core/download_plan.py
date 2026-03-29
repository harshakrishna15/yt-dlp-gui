from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..common import settings_store
from ..common.types import DownloadOptions, DownloadRequest, QueueSettings, ResolvedFormat
from . import options as core_options

PLAYLIST_ITEMS_ERROR_TEXT = "Playlist items must use numbers and ranges like 1-5,7,10-."


def _parse_playlist_items(value: str) -> list[tuple[int, int | None]]:
    ranges: list[tuple[int, int | None]] = []
    for chunk in str(value or "").split(","):
        clean = chunk.strip()
        if not clean:
            continue
        if "-" in clean:
            start_s, end_s = [part.strip() for part in clean.split("-", 1)]
            if not start_s:
                continue
            try:
                start_i = int(start_s)
            except ValueError:
                continue
            if start_i <= 0:
                continue
            if end_s:
                try:
                    end_i = int(end_s)
                except ValueError:
                    continue
                if end_i <= 0 or end_i < start_i:
                    continue
            else:
                end_i = None
            ranges.append((start_i, end_i))
            continue
        try:
            index = int(clean)
        except ValueError:
            continue
        if index <= 0:
            continue
        ranges.append((index, index))
    return _merge_playlist_ranges(ranges)


def _merge_playlist_ranges(
    ranges: list[tuple[int, int | None]],
) -> list[tuple[int, int | None]]:
    if not ranges:
        return []
    ordered = sorted(
        ranges,
        key=lambda item: (item[0], float("inf") if item[1] is None else item[1]),
    )
    merged: list[list[int | None]] = []
    for start, end in ordered:
        if not merged:
            merged.append([start, end])
            continue
        last_start, last_end = merged[-1]
        if last_end is None:
            continue
        if start <= (int(last_end) + 1):
            merged[-1][1] = None if end is None else max(int(last_end), int(end))
            continue
        merged.append([start, end])
    return [(int(start), None if end is None else int(end)) for start, end in merged]


def _format_playlist_items(ranges: list[tuple[int, int | None]]) -> str | None:
    if not ranges:
        return None
    parts: list[str] = []
    for start, end in ranges:
        if end is None:
            parts.append(f"{start}-")
        elif start == end:
            parts.append(str(start))
        else:
            parts.append(f"{start}-{end}")
    return ",".join(parts)


def normalize_playlist_items(value: str) -> tuple[str | None, bool]:
    raw = value or ""
    compact = re.sub(r"\s+", "", raw)
    normalized = _format_playlist_items(_parse_playlist_items(compact))
    return normalized, bool(raw and raw != (normalized or ""))


def parse_download_options_from_queue_settings(
    settings: Mapping[str, Any],
    *,
    timeout_default: int,
    retries_default: int,
    backoff_default: float,
    fragments_default: int,
) -> DownloadOptions:
    return {
        "network_timeout_s": core_options.parse_int_setting(
            str(settings.get("network_timeout_s", "")),
            default=timeout_default,
            minimum=1,
            maximum=300,
        ),
        "network_retries": core_options.parse_int_setting(
            str(settings.get("network_retries", "")),
            default=retries_default,
            minimum=0,
            maximum=10,
        ),
        "retry_backoff_s": core_options.parse_float_setting(
            str(settings.get("retry_backoff_s", "")),
            default=backoff_default,
            minimum=0.0,
            maximum=30.0,
        ),
        "concurrent_fragments": core_options.parse_int_setting(
            str(settings.get("concurrent_fragments", "")),
            default=fragments_default,
            minimum=1,
            maximum=4,
        ),
        "subtitle_languages": core_options.coerce_subtitle_languages(
            settings.get("subtitle_languages", "")
        ),
        "write_subtitles": bool(settings.get("write_subtitles")),
        "embed_subtitles": bool(settings.get("embed_subtitles")),
        "audio_language": str(settings.get("audio_language", "")),
        "custom_filename": str(settings.get("custom_filename", "")),
        "edit_friendly_encoder": core_options.normalize_edit_friendly_encoder_preference(
            str(settings.get("edit_friendly_encoder", "auto"))
        ),
    }


def build_single_download_request(
    *,
    url: str,
    output_dir: Path,
    fmt_info: dict | None,
    fmt_label: str,
    format_filter: str,
    convert_to_mp4: bool,
    playlist_enabled: bool,
    playlist_items_raw: str,
    options: DownloadOptions,
) -> DownloadRequest:
    playlist_items_raw_text = str(playlist_items_raw or "")
    playlist_items, _was_normalized = normalize_playlist_items(playlist_items_raw_text)
    if playlist_enabled and playlist_items_raw_text.strip() and playlist_items is None:
        raise ValueError(PLAYLIST_ITEMS_ERROR_TEXT)
    if not playlist_enabled:
        playlist_items = None
    return {
        "url": url,
        "output_dir": output_dir,
        "fmt_info": fmt_info,
        "fmt_label": fmt_label,
        "format_filter": format_filter,
        "convert_to_mp4": bool(convert_to_mp4),
        "playlist_enabled": bool(playlist_enabled),
        "playlist_items": playlist_items,
        "network_timeout_s": int(options["network_timeout_s"]),
        "network_retries": int(options["network_retries"]),
        "retry_backoff_s": float(options["retry_backoff_s"]),
        "concurrent_fragments": int(options["concurrent_fragments"]),
        "subtitle_languages": list(options["subtitle_languages"]),
        "write_subtitles": bool(options["write_subtitles"]),
        "embed_subtitles": bool(options["embed_subtitles"]),
        "audio_language": str(options["audio_language"]),
        "custom_filename": str(options["custom_filename"]),
        "edit_friendly_encoder": str(options["edit_friendly_encoder"]),
    }


def build_queue_download_request(
    *,
    url: str,
    settings: QueueSettings | Mapping[str, Any],
    resolved: ResolvedFormat | Mapping[str, Any],
    default_output_dir: str,
    timeout_default: int,
    retries_default: int,
    backoff_default: float,
    fragments_default: int,
) -> DownloadRequest:
    parsed_options = parse_download_options_from_queue_settings(
        settings,
        timeout_default=timeout_default,
        retries_default=retries_default,
        backoff_default=backoff_default,
        fragments_default=fragments_default,
    )
    playlist_items_raw = str(settings.get("playlist_items", ""))
    playlist_items, _was_normalized = normalize_playlist_items(playlist_items_raw)
    if bool(resolved.get("is_playlist")) and playlist_items_raw.strip() and playlist_items is None:
        raise ValueError(PLAYLIST_ITEMS_ERROR_TEXT)
    return {
        "url": url,
        "output_dir": settings_store.resolve_output_dir_path(
            settings.get("output_dir"),
            default_output_dir=default_output_dir,
        ),
        "fmt_info": resolved.get("fmt_info"),
        "fmt_label": str(resolved.get("fmt_label", "")),
        "format_filter": str(resolved.get("format_filter", "")),
        "convert_to_mp4": bool(settings.get("convert_to_mp4")),
        "playlist_enabled": bool(resolved.get("is_playlist")),
        "playlist_items": playlist_items,
        "network_timeout_s": int(parsed_options["network_timeout_s"]),
        "network_retries": int(parsed_options["network_retries"]),
        "retry_backoff_s": float(parsed_options["retry_backoff_s"]),
        "concurrent_fragments": int(parsed_options["concurrent_fragments"]),
        "subtitle_languages": list(parsed_options["subtitle_languages"]),
        "write_subtitles": bool(parsed_options["write_subtitles"]),
        "embed_subtitles": bool(parsed_options["embed_subtitles"]),
        "audio_language": str(parsed_options["audio_language"]),
        "custom_filename": str(parsed_options["custom_filename"]),
        "edit_friendly_encoder": str(parsed_options["edit_friendly_encoder"]),
    }
