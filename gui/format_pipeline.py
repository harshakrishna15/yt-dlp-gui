from __future__ import annotations

from typing import Any

from . import yt_dlp_helpers as helpers
from .shared_types import FormatInfo, FormatLookup

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
