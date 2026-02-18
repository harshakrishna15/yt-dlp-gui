from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ..shared_types import DownloadOptions, QueueSettings


def parse_int_setting(
    value: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default
    return max(minimum, min(maximum, parsed))


def parse_float_setting(
    value: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(minimum, min(maximum, parsed))


def parse_subtitle_languages(value: str) -> list[str]:
    languages: list[str] = []
    for token in (value or "").split(","):
        clean = token.strip().lower()
        if clean and clean not in languages:
            languages.append(clean)
    return languages


def sanitize_custom_filename(value: str) -> str:
    stem = re.sub(r"\s+", " ", (value or "").strip())
    stem = re.sub(r'[\\/:*?"<>|]+', " ", stem)
    stem = stem.strip().strip(".")
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", stem).strip()
    if stem in {"", ".", ".."}:
        return ""
    return stem[:160]


def coerce_subtitle_languages(value: object) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for token in value:
            clean = str(token).strip().lower()
            if clean and clean not in out:
                out.append(clean)
        return out
    return parse_subtitle_languages(str(value or ""))


def build_download_options(
    *,
    network_timeout_raw: str,
    network_retries_raw: str,
    retry_backoff_raw: str,
    subtitle_languages_raw: str,
    write_subtitles_requested: bool,
    embed_subtitles_requested: bool,
    is_video_mode: bool,
    audio_language_raw: str,
    custom_filename_raw: str,
    timeout_default: int,
    retries_default: int,
    backoff_default: float,
) -> DownloadOptions:
    subtitle_languages = parse_subtitle_languages(subtitle_languages_raw)
    write_subtitles = bool(write_subtitles_requested) and bool(is_video_mode)
    embed_subtitles = write_subtitles and bool(embed_subtitles_requested)
    return {
        "network_timeout_s": parse_int_setting(
            network_timeout_raw,
            default=timeout_default,
            minimum=1,
            maximum=300,
        ),
        "network_retries": parse_int_setting(
            network_retries_raw,
            default=retries_default,
            minimum=0,
            maximum=10,
        ),
        "retry_backoff_s": parse_float_setting(
            retry_backoff_raw,
            default=backoff_default,
            minimum=0.0,
            maximum=30.0,
        ),
        "subtitle_languages": subtitle_languages,
        "write_subtitles": write_subtitles,
        "embed_subtitles": embed_subtitles,
        "audio_language": (audio_language_raw or "").strip(),
        "custom_filename": sanitize_custom_filename(custom_filename_raw),
    }


def build_queue_settings(
    *,
    mode: str,
    format_filter: str,
    codec_filter: str,
    convert_to_mp4: bool,
    format_label: str,
    estimated_size: str,
    output_dir: str,
    playlist_items: str,
    options: Mapping[str, Any],
) -> QueueSettings:
    return {
        "mode": mode,
        "format_filter": format_filter,
        "codec_filter": codec_filter,
        "convert_to_mp4": bool(convert_to_mp4),
        "format_label": format_label,
        "estimated_size": estimated_size,
        "output_dir": output_dir,
        "playlist_items": (playlist_items or "").strip(),
        "network_timeout_s": options["network_timeout_s"],
        "network_retries": options["network_retries"],
        "retry_backoff_s": options["retry_backoff_s"],
        "subtitle_languages": list(options["subtitle_languages"]),
        "write_subtitles": bool(options["write_subtitles"]),
        "embed_subtitles": bool(options["embed_subtitles"]),
        "audio_language": options["audio_language"],
        "custom_filename": options["custom_filename"],
    }
