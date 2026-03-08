from __future__ import annotations

from typing import Any

from . import yt_dlp_helpers as helpers
from .types import FormatInfo, FormatLookup, SourceSummary

BEST_AUDIO_LABEL = "Best audio only"
BEST_AUDIO_INFO: FormatInfo = {
    "custom_format": "bestaudio/best",
    "is_audio_only": True,
}


def _normalize_preview_title(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def preview_title_from_info(info: dict[str, Any]) -> str:
    title = _normalize_preview_title(info.get("title"))
    if title:
        return title
    entries = info.get("entries")
    if isinstance(entries, list) and entries:
        first = entries[0] or {}
        return _normalize_preview_title(first.get("title"))
    return ""


def _coerce_positive_int(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _compact_duration_label(value: object) -> str:
    try:
        total_seconds = int(float(value))
    except (TypeError, ValueError):
        return ""
    if total_seconds <= 0:
        return ""
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def _creator_label_from_info(info: dict[str, Any]) -> str:
    candidates = (
        info.get("channel"),
        info.get("uploader"),
        info.get("playlist_uploader"),
        info.get("uploader_id"),
    )
    for candidate in candidates:
        clean = _normalize_preview_title(candidate)
        if clean:
            return clean
    return ""


def source_summary_from_info(
    info: dict[str, Any],
    *,
    video_format_count: int = 0,
    audio_format_count: int = 0,
) -> SourceSummary:
    is_playlist = bool(
        info.get("_type") == "playlist" or info.get("entries") is not None
    )
    creator_label = _creator_label_from_info(info)
    playlist_count = _coerce_positive_int(
        info.get("playlist_count")
        or info.get("n_entries")
        or info.get("entry_count")
    )
    if playlist_count <= 0:
        entries = info.get("entries")
        if isinstance(entries, list):
            playlist_count = len([entry for entry in entries if entry])
    duration_label = _compact_duration_label(info.get("duration"))

    detail_one = "Formats ready"
    detail_two = ""
    detail_three = ""

    if is_playlist:
        if playlist_count > 0:
            detail_two = f"{playlist_count} items"
        subtitle = creator_label or "Review the playlist items before downloading."
        return {
            "badge_text": "LIST",
            "eyebrow_text": "Playlist ready",
            "subtitle_text": subtitle,
            "detail_one_text": detail_one,
            "detail_two_text": detail_two,
            "detail_three_text": detail_three,
        }

    if duration_label:
        detail_two = duration_label
    if video_format_count > 0:
        suffix = "format" if video_format_count == 1 else "formats"
        detail_three = f"{video_format_count} video {suffix}"
    elif audio_format_count > 0:
        suffix = "option" if audio_format_count == 1 else "options"
        detail_three = f"{audio_format_count} audio {suffix}"

    subtitle = creator_label or "Choose export settings to start downloading."
    return {
        "badge_text": "VID",
        "eyebrow_text": "Video ready",
        "subtitle_text": subtitle,
        "detail_one_text": detail_one,
        "detail_two_text": detail_two,
        "detail_three_text": detail_three,
    }


def build_labeled_sets(
    formats: list[FormatInfo],
) -> tuple[list[tuple[str, FormatInfo]], list[tuple[str, FormatInfo]]]:
    video_formats, audio_formats = helpers.split_and_filter_formats(formats)
    video_labeled = helpers.build_labeled_formats(video_formats)
    audio_labeled = helpers.build_labeled_formats(audio_formats)
    audio_labeled.insert(0, (BEST_AUDIO_LABEL, dict(BEST_AUDIO_INFO)))
    return video_labeled, audio_labeled


def build_format_collections(formats: list[FormatInfo]) -> dict[str, list | FormatLookup]:
    video_labeled, audio_labeled = build_labeled_sets(formats)
    return {
        "video_labels": [label for label, _ in video_labeled],
        "video_lookup": {label: fmt for label, fmt in video_labeled},
        "audio_labels": [label for label, _ in audio_labeled],
        "audio_lookup": {label: fmt for label, fmt in audio_labeled},
        "audio_languages": helpers.extract_audio_languages(formats),
    }
