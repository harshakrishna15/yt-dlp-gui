from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, TypeAlias

FormatInfo: TypeAlias = dict[str, Any]
FormatLookup: TypeAlias = dict[str, FormatInfo]


class FormatsCacheEntry(TypedDict):
    video_labels: list[str]
    video_lookup: FormatLookup
    audio_labels: list[str]
    audio_lookup: FormatLookup
    audio_languages: list[str]
    preview_title: str
    source_summary: "SourceSummary"


class SourceSummary(TypedDict):
    badge_text: str
    eyebrow_text: str
    subtitle_text: str
    detail_one_text: str
    detail_two_text: str
    detail_three_text: str


class ProgressUpdate(TypedDict, total=False):
    status: str
    percent: float | None
    speed: str
    eta: str
    playlist_eta: str
    item: str


class DownloadOptions(TypedDict):
    network_timeout_s: int
    network_retries: int
    retry_backoff_s: float
    concurrent_fragments: int
    subtitle_languages: list[str]
    write_subtitles: bool
    embed_subtitles: bool
    audio_language: str
    custom_filename: str
    edit_friendly_encoder: str


class QueueSettings(TypedDict, total=False):
    mode: str
    format_filter: str
    codec_filter: str
    convert_to_mp4: bool
    format_label: str
    estimated_size: str
    output_dir: str
    playlist_items: str
    network_timeout_s: int
    network_retries: int
    retry_backoff_s: float
    concurrent_fragments: int
    subtitle_languages: list[str]
    write_subtitles: bool
    embed_subtitles: bool
    audio_language: str
    custom_filename: str
    edit_friendly_encoder: str


class QueueItem(TypedDict, total=False):
    url: str
    settings: QueueSettings


class HistoryItem(TypedDict, total=False):
    timestamp: str
    path: str
    name: str
    title: str
    format_label: str
    file_size_bytes: int
    source_url: str
    canonical_path: str
    queue_settings: QueueSettings


class ResolvedFormat(TypedDict, total=False):
    fmt_label: str
    fmt_info: FormatInfo
    format_filter: str
    is_playlist: bool
    title: str


class DownloadRequest(TypedDict):
    url: str
    output_dir: Path
    fmt_info: FormatInfo | None
    fmt_label: str
    format_filter: str
    convert_to_mp4: bool
    playlist_enabled: bool
    playlist_items: str | None
    network_timeout_s: int
    network_retries: int
    retry_backoff_s: float
    concurrent_fragments: int
    subtitle_languages: list[str]
    write_subtitles: bool
    embed_subtitles: bool
    audio_language: str
    custom_filename: str
    edit_friendly_encoder: str
