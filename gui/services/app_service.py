from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from . import preflight

from ..common import download, formats as formats_mod, yt_dlp_helpers as helpers
from ..core import download_plan as core_download_plan
from ..core import format_selection as core_format_selection
from ..core import options as core_options
from ..common.types import (
    DownloadOptions,
    DownloadRequest,
    FormatInfo,
    ProgressUpdate,
    QueueSettings,
    ResolvedFormat,
)


def build_download_options(
    *,
    custom_filename_raw: str,
    edit_friendly_encoder_raw: str,
) -> DownloadOptions:
    return core_options.build_download_options(
        custom_filename_raw=custom_filename_raw,
        edit_friendly_encoder_raw=edit_friendly_encoder_raw,
        timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
        retries_default=download.YDL_ATTEMPT_RETRIES,
        backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
        fragments_default=download.YDL_MAX_CONCURRENT_FRAGMENTS,
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
    settings = core_options.build_queue_settings(
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
    selector = core_format_selection.queue_format_selector(
        mode=mode, container=format_filter, codec=codec_filter, info=dict(format_info),
    )
    if selector:
        settings["format_selector"] = selector
    estimated_bytes = helpers.estimate_filesize_bytes(dict(format_info))
    if estimated_bytes:
        settings["estimated_size_bytes"] = estimated_bytes
    return settings


def resolve_format_for_url(
    *,
    url: str,
    settings: QueueSettings | Mapping[str, Any],
    log: Callable[[str], None],
    cancel_event: threading.Event | None = None,
    on_status: Callable[[str], None] | None = None,
) -> ResolvedFormat:
    if cancel_event is not None and cancel_event.is_set():
        raise helpers.yt_dlp_cli.MetadataCancelled()
    selector = settings.get("format_selector")
    if selector:
        audio_only = settings.get("mode") == "audio"
        return {
            "fmt_label": str(settings.get("format_label") or "Best available"),
            "fmt_info": {"custom_format": str(selector), "is_audio_only": audio_only,
                         "vcodec": "none" if audio_only else "unknown", "acodec": "unknown",
                         "filesize_approx": settings.get("estimated_size_bytes")},
            "format_filter": str(settings.get("format_filter") or ""),
            "is_playlist": False,
            "title": "",
        }
    info = helpers.fetch_info(url, cancel_event=cancel_event, on_status=on_status)
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
    _playlist_items, was_normalized = core_download_plan.normalize_playlist_items(
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
        playlist_items_raw=playlist_items_raw,
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
        fragments_default=download.YDL_MAX_CONCURRENT_FRAGMENTS,
    )


def run_download_request(
    *,
    request: DownloadRequest,
    cancel_event: threading.Event | None,
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
    record_output: Callable[[Path], None] | None = None,
) -> str:
    output_dir = request["output_dir"]
    update_progress({"status": "preparing", "message": "Checking destination and media tools..."})
    preflight.check_download(request, cancel_event)
    update_progress({"status": "preparing", "message": "Downloading..."})
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
        concurrent_fragments=int(request["concurrent_fragments"]),
        subtitle_languages=list(request["subtitle_languages"]),
        write_subtitles=bool(request["write_subtitles"]),
        embed_subtitles=bool(request["embed_subtitles"]),
        audio_language=str(request["audio_language"]),
        custom_filename=str(request["custom_filename"]),
        edit_friendly_encoder=str(request["edit_friendly_encoder"]),
        record_output=record_output,
    )
