from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from ..common import download, formats as formats_mod, history_store, yt_dlp_helpers as helpers
from ..core import download_plan as core_download_plan
from ..core import format_selection as core_format_selection
from ..core import options as core_options
from ..common.types import (
    DownloadOptions,
    DownloadRequest,
    FormatInfo,
    HistoryItem,
    ProgressUpdate,
    QueueSettings,
    ResolvedFormat,
)


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
) -> DownloadOptions:
    return core_options.build_download_options(
        network_timeout_raw=network_timeout_raw,
        network_retries_raw=network_retries_raw,
        retry_backoff_raw=retry_backoff_raw,
        subtitle_languages_raw=subtitle_languages_raw,
        write_subtitles_requested=write_subtitles_requested,
        embed_subtitles_requested=embed_subtitles_requested,
        is_video_mode=is_video_mode,
        audio_language_raw=audio_language_raw,
        custom_filename_raw=custom_filename_raw,
        timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
        retries_default=download.YDL_ATTEMPT_RETRIES,
        backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
    )


def build_queue_settings(
    *,
    mode: str,
    format_filter: str,
    codec_filter: str,
    convert_to_mp4: bool,
    format_label: str,
    format_info: FormatInfo | Mapping[str, Any],
    output_dir: str,
    playlist_items: str,
    options: DownloadOptions,
) -> QueueSettings:
    estimated_size = helpers.humanize_bytes(
        helpers.estimate_filesize_bytes(dict(format_info))
    )
    return core_options.build_queue_settings(
        mode=mode,
        format_filter=format_filter,
        codec_filter=codec_filter,
        convert_to_mp4=convert_to_mp4,
        format_label=format_label,
        estimated_size=estimated_size,
        output_dir=output_dir,
        playlist_items=playlist_items,
        options=options,
    )


def resolve_format_for_url(
    *,
    url: str,
    settings: QueueSettings | Mapping[str, Any],
    log: Callable[[str], None],
) -> ResolvedFormat:
    info = helpers.fetch_info(url)
    formats = formats_mod.formats_from_info(info)
    return core_format_selection.resolve_format_for_info(
        info=info,
        formats=formats,
        settings=settings,
        log=log,
    )


def build_single_download_request(
    *,
    url: str,
    output_dir: Path,
    fmt_info: FormatInfo | None,
    fmt_label: str,
    format_filter: str,
    convert_to_mp4: bool,
    playlist_enabled: bool,
    playlist_items_raw: str,
    options: DownloadOptions,
) -> tuple[DownloadRequest, bool]:
    playlist_items, was_normalized = core_download_plan.normalize_playlist_items(
        playlist_items_raw
    )
    request = core_download_plan.build_single_download_request(
        url=url,
        output_dir=output_dir,
        fmt_info=fmt_info,
        fmt_label=fmt_label,
        format_filter=format_filter,
        convert_to_mp4=convert_to_mp4,
        playlist_enabled=playlist_enabled,
        playlist_items_raw=playlist_items or "",
        options=options,
    )
    return request, was_normalized


def build_queue_download_request(
    *,
    url: str,
    settings: QueueSettings | Mapping[str, Any],
    resolved: ResolvedFormat | Mapping[str, Any],
    default_output_dir: str,
) -> DownloadRequest:
    return core_download_plan.build_queue_download_request(
        url=url,
        settings=settings,
        resolved=resolved,
        default_output_dir=default_output_dir,
        timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
        retries_default=download.YDL_ATTEMPT_RETRIES,
        backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
    )


def run_download_request(
    *,
    request: DownloadRequest,
    cancel_event: threading.Event | None,
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
    record_output: Callable[[Path], None] | None = None,
    ensure_output_dir: bool = False,
) -> str:
    output_dir = request["output_dir"]
    if ensure_output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    return download.run_download(
        url=request["url"],
        output_dir=output_dir,
        fmt_info=request["fmt_info"],
        fmt_label=request["fmt_label"],
        format_filter=request["format_filter"],
        convert_to_mp4=bool(request["convert_to_mp4"]),
        playlist_enabled=bool(request["playlist_enabled"]),
        playlist_items=request["playlist_items"],
        cancel_event=cancel_event,
        log=log,
        update_progress=update_progress,
        network_retries=int(request["network_retries"]),
        network_timeout_s=int(request["network_timeout_s"]),
        retry_backoff_s=float(request["retry_backoff_s"]),
        subtitle_languages=list(request["subtitle_languages"]),
        write_subtitles=bool(request["write_subtitles"]),
        embed_subtitles=bool(request["embed_subtitles"]),
        audio_language=str(request["audio_language"]),
        custom_filename=str(request["custom_filename"]),
        record_output=record_output,
    )


def record_history_output(
    *,
    history: list[HistoryItem],
    seen_paths: set[str],
    output_path: Path,
    source_url: str,
    max_entries: int,
    timestamp: datetime | None = None,
) -> bool:
    normalized = history_store.normalize_output_path(output_path)
    if not normalized:
        return False
    now = timestamp or datetime.now()
    history_store.upsert_history_entry(
        history,
        seen_paths,
        normalized_path=normalized,
        source_url=source_url,
        timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
        max_entries=max_entries,
    )
    return True

