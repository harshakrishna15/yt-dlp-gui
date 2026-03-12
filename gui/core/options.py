from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ..common.types import DownloadOptions, QueueSettings

EDIT_FRIENDLY_ENCODER_OPTIONS = {
    "auto",
    "apple",
    "nvidia",
    "amd",
    "intel",
    "cpu",
}


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


def normalize_edit_friendly_encoder_preference(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "auto": "auto",
        "automatic": "auto",
        "default": "auto",
        "apple": "apple",
        "videotoolbox": "apple",
        "h264_videotoolbox": "apple",
        "nvidia": "nvidia",
        "nvenc": "nvidia",
        "h264_nvenc": "nvidia",
        "amd": "amd",
        "amf": "amd",
        "h264_amf": "amd",
        "intel": "intel",
        "qsv": "intel",
        "h264_qsv": "intel",
        "cpu": "cpu",
        "x264": "cpu",
        "libx264": "cpu",
    }
    normalized = aliases.get(raw, raw)
    if normalized in EDIT_FRIENDLY_ENCODER_OPTIONS:
        return normalized
    return "auto"


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
    custom_filename_raw: str,
    edit_friendly_encoder_raw: str,
    timeout_default: int,
    retries_default: int,
    backoff_default: float,
    fragments_default: int,
) -> DownloadOptions:
    return {
        "network_timeout_s": int(timeout_default),
        "network_retries": int(retries_default),
        "retry_backoff_s": float(backoff_default),
        "concurrent_fragments": int(fragments_default),
        "subtitle_languages": [],
        "write_subtitles": False,
        "embed_subtitles": False,
        "audio_language": "",
        "custom_filename": sanitize_custom_filename(custom_filename_raw),
        "edit_friendly_encoder": normalize_edit_friendly_encoder_preference(
            edit_friendly_encoder_raw
        ),
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
        "concurrent_fragments": options["concurrent_fragments"],
        "subtitle_languages": list(options["subtitle_languages"]),
        "write_subtitles": bool(options["write_subtitles"]),
        "embed_subtitles": bool(options["embed_subtitles"]),
        "audio_language": options["audio_language"],
        "custom_filename": options["custom_filename"],
        "edit_friendly_encoder": options["edit_friendly_encoder"],
    }
