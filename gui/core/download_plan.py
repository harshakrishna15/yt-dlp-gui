from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..shared_types import DownloadOptions, DownloadRequest, QueueSettings, ResolvedFormat
from . import options as core_options


def normalize_playlist_items(value: str) -> tuple[str | None, bool]:
    raw = value or ""
    normalized = re.sub(r"\s+", "", raw)
    return (normalized or None), bool(raw and normalized != raw)


def parse_download_options_from_queue_settings(
    settings: Mapping[str, Any],
    *,
    timeout_default: int,
    retries_default: int,
    backoff_default: float,
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
        "subtitle_languages": core_options.coerce_subtitle_languages(
            settings.get("subtitle_languages", "")
        ),
        "write_subtitles": bool(settings.get("write_subtitles")),
        "embed_subtitles": bool(settings.get("embed_subtitles")),
        "audio_language": str(settings.get("audio_language", "")),
        "custom_filename": str(settings.get("custom_filename", "")),
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
    playlist_items, _was_normalized = normalize_playlist_items(playlist_items_raw)
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
        "subtitle_languages": list(options["subtitle_languages"]),
        "write_subtitles": bool(options["write_subtitles"]),
        "embed_subtitles": bool(options["embed_subtitles"]),
        "audio_language": str(options["audio_language"]),
        "custom_filename": str(options["custom_filename"]),
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
) -> DownloadRequest:
    parsed_options = parse_download_options_from_queue_settings(
        settings,
        timeout_default=timeout_default,
        retries_default=retries_default,
        backoff_default=backoff_default,
    )
    playlist_items, _was_normalized = normalize_playlist_items(
        str(settings.get("playlist_items", ""))
    )
    return {
        "url": url,
        "output_dir": Path(
            str(settings.get("output_dir") or default_output_dir)
        ).expanduser(),
        "fmt_info": resolved.get("fmt_info"),
        "fmt_label": str(resolved.get("fmt_label", "")),
        "format_filter": str(resolved.get("format_filter", "")),
        "convert_to_mp4": bool(settings.get("convert_to_mp4")),
        "playlist_enabled": bool(resolved.get("is_playlist")),
        "playlist_items": playlist_items,
        "network_timeout_s": int(parsed_options["network_timeout_s"]),
        "network_retries": int(parsed_options["network_retries"]),
        "retry_backoff_s": float(parsed_options["retry_backoff_s"]),
        "subtitle_languages": list(parsed_options["subtitle_languages"]),
        "write_subtitles": bool(parsed_options["write_subtitles"]),
        "embed_subtitles": bool(parsed_options["embed_subtitles"]),
        "audio_language": str(parsed_options["audio_language"]),
        "custom_filename": str(parsed_options["custom_filename"]),
    }
