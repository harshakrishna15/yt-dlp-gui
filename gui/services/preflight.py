from __future__ import annotations

import errno
import shutil
import tempfile
import threading

from ..common.tooling import resolve_binary
from ..common.types import DownloadRequest
from ..common.yt_dlp_cli import MetadataCancelled
from ..common.yt_dlp_helpers import estimate_filesize_bytes, humanize_bytes


def check_download(request: DownloadRequest, cancel_event: threading.Event | None) -> None:
    def check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise MetadataCancelled()

    check_cancel()
    info = request.get("fmt_info") or {}
    container = request.get("format_filter", "")
    audio_only = bool(info.get("is_audio_only") or info.get("vcodec") == "none")
    processing = (audio_only or container == "mp4" or request.get("convert_to_mp4")
                  or request.get("embed_subtitles") or bool(info.get("custom_format"))
                  or info.get("acodec") in {None, "none"})
    if processing:
        for name in ("ffmpeg", "ffprobe"):
            check_cancel()
            if resolve_binary(name)[0] is None:
                raise RuntimeError(f"Required media tool missing: {name}")

    output_dir = request["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    check_cancel()
    # Test a real write, not just permission bits (ACLs and network volumes differ).
    with tempfile.TemporaryFile(dir=output_dir, prefix=".yt-dlp-gui-check-") as probe:
        probe.write(b"\0")
        probe.flush()
    check_cancel()
    estimated = estimate_filesize_bytes(info)
    free = shutil.disk_usage(output_dir).free
    # Format sizes may exclude the audio stream or grow during conversion.
    required = (estimated * (3 if processing else 1)) if estimated else 0
    if free == 0 or (required and free < required):
        raise OSError(errno.ENOSPC,
                      f"Insufficient free disk space: {humanize_bytes(free) or '0 B'} available; "
                      f"about {humanize_bytes(required) or 'more space'} needed including processing.")
    check_cancel()
