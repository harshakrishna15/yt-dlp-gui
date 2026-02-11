import time
import threading
from pathlib import Path
from typing import Any, Callable
import re
import shutil

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from .shared_types import FormatInfo, ProgressUpdate

AUDIO_OUTPUT_CODECS = {"m4a", "mp3", "opus", "wav", "flac"}


def build_ydl_opts(
    *,
    url: str,
    output_dir: Path,
    fmt_info: FormatInfo | None,
    fmt_label: str,
    format_filter: str,
    convert_to_mp4: bool,
    playlist_enabled: bool,
    playlist_items: str | None,
    cancel_event: threading.Event | None,
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
) -> dict[str, Any]:
    fmt_id = fmt_info.get("format_id") if fmt_info else None
    is_audio_only = bool(
        fmt_info
        and (fmt_info.get("vcodec") in (None, "none") or fmt_info.get("is_audio_only"))
    )
    is_video_only = bool(
        fmt_info and fmt_info.get("acodec") in (None, "none") and not is_audio_only
    )

    if fmt_info and fmt_info.get("custom_format"):
        fmt = fmt_info["custom_format"]
    elif fmt_id and is_video_only:
        fmt = f"{fmt_id}+bestaudio/best"
    elif fmt_id:
        fmt = fmt_id
    else:
        fmt = "bestvideo+bestaudio/best"

    selected_container = format_filter if format_filter in {"mp4", "webm"} else ""
    fmt_ext = (fmt_info.get("ext") or "").lower() if fmt_info else ""
    target_container = selected_container or fmt_ext or None

    postprocessors: list[dict[str, Any]] = []
    pp_args: list[str] = []
    merge_output_format = target_container if target_container in {"mp4", "webm"} else None

    if is_audio_only or fmt == "bestaudio/best":
        merge_output_format = None
        desired_audio = (format_filter or "").lower()
        preferred_audio_codec = (
            desired_audio if desired_audio in AUDIO_OUTPUT_CODECS else "m4a"
        )
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": preferred_audio_codec,
            }
        ]
        pp_args = []
    elif target_container == "mp4":
        postprocessors = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]
        pp_args = ["-movflags", "+faststart"]
    elif target_container == "webm" and convert_to_mp4:
        merge_output_format = "mp4"
        postprocessors = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]
        pp_args = ["-movflags", "+faststart"]

    if playlist_enabled:
        outtmpl = str(output_dir / "%(playlist_index)s - %(title)s_%(epoch)s.%(ext)s")
    else:
        outtmpl = str(output_dir / "%(title)s_%(epoch)s.%(ext)s")

    log(f"[start] {url}")
    if fmt_label:
        log(f"[format] {fmt_label}")

    ranges: list[tuple[int, int | None]] = []
    if playlist_enabled and playlist_items:
        ranges = _parse_playlist_items(playlist_items)

    ffmpeg_location: str | None = None
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        ffmpeg_location = ffmpeg_path
    else:
        brew_ffmpeg = Path("/opt/homebrew/bin/ffmpeg")
        if brew_ffmpeg.exists():
            ffmpeg_location = str(brew_ffmpeg)

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "format": fmt,
        "progress_hooks": [
            _progress_hook_factory(log, update_progress, cancel_event, ranges)
        ],
        "postprocessor_hooks": [_postprocessor_hook_factory(log)],
        "noplaylist": not playlist_enabled,
        "merge_output_format": merge_output_format,
        "postprocessors": postprocessors,
        "postprocessor_args": pp_args,
    }
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
        log(f"[ffmpeg] {ffmpeg_location}")
    if playlist_enabled and playlist_items:
        opts["playlist_items"] = playlist_items
        opts["extractor_args"] = {
            "youtube": {"playlist_items": playlist_items},
        }
        log(f"[playlist] items={playlist_items}")
        simple_range = re.fullmatch(r"\d+\s*-\s*\d+", playlist_items)
        if simple_range:
            start_s, end_s = [part.strip() for part in playlist_items.split("-", 1)]
            try:
                start_i = int(start_s)
                end_i = int(end_s)
            except ValueError:
                start_i = None
                end_i = None
            if start_i is not None and end_i is not None:
                opts["playlist_start"] = start_i
                opts["playlist_end"] = end_i
        if ranges:
            opts["match_filter"] = _playlist_match_filter(ranges)
    return opts


def run_download(
    url: str,
    output_dir: Path,
    fmt_info: FormatInfo | None,
    fmt_label: str,
    format_filter: str,
    convert_to_mp4: bool,
    playlist_enabled: bool,
    playlist_items: str | None,
    cancel_event: threading.Event | None,
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
) -> None:
    """Run a yt-dlp download with progress callbacks."""
    opts = build_ydl_opts(
        url=url,
        output_dir=output_dir,
        fmt_info=fmt_info,
        fmt_label=fmt_label,
        format_filter=format_filter,
        convert_to_mp4=convert_to_mp4,
        playlist_enabled=playlist_enabled,
        playlist_items=playlist_items,
        cancel_event=cancel_event,
        log=log,
        update_progress=update_progress,
    )
    start_ts = time.time()
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except DownloadCancelled:
        log("[cancelled] Download cancelled.")
        try:
            update_progress({"status": "cancelled"})
        except Exception:
            pass
    except Exception as exc:  # broad to surface in UI
        log(f"[error] {exc}")
    else:
        log("[done] Download complete.")
    finally:
        elapsed = time.time() - start_ts
        log(f"[time] Elapsed: {format_duration(elapsed)}")


def _progress_hook_factory(
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
    cancel_event: threading.Event | None,
    ranges: list[tuple[int, int | None]],
) -> Callable[[dict], None]:
    last_log = {"ts": 0.0}
    last_item = {"key": None}
    total_items = _playlist_ranges_count(ranges)

    def _format_speed(bytes_per_sec: float | None) -> str:
        if not bytes_per_sec or bytes_per_sec <= 0:
            return "—"
        units = ["B/s", "KiB/s", "MiB/s", "GiB/s", "TiB/s"]
        value = float(bytes_per_sec)
        unit_idx = 0
        while value >= 1024 and unit_idx < len(units) - 1:
            value /= 1024.0
            unit_idx += 1
        if unit_idx == 0:
            return f"{value:.0f} {units[unit_idx]}"
        return f"{value:.2f} {units[unit_idx]}"

    def _format_eta(seconds: float | None) -> str:
        if seconds is None:
            return "—"
        try:
            seconds_i = int(max(0, seconds))
        except Exception:
            return "—"
        m, s = divmod(seconds_i, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:d}:{s:02d}"

    def hook(status: dict) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled()

        info = status.get("info_dict") or {}
        playlist_index = info.get("playlist_index")
        playlist_count = info.get("playlist_count") or status.get("playlist_count")
        if total_items is not None:
            playlist_count = total_items
        title = info.get("title") or ""
        if playlist_index and last_item["key"] != playlist_index:
            last_item["key"] = playlist_index
            display_index = playlist_index
            if ranges:
                display_index = _playlist_position_for_index(ranges, playlist_index)
            if playlist_count and display_index:
                log(f"[item] {display_index}/{playlist_count} {title}".strip())
            else:
                log(f"[item] {display_index} {title}".strip())
            item_text = (
                f"{display_index}/{playlist_count} {title}".strip()
                if playlist_count and display_index
                else f"{display_index} {title}".strip()
            )
            update_progress({"status": "item", "item": item_text})

        if status.get("status") == "downloading":
            now = time.time()
            if now - last_log["ts"] >= 0.8:
                last_log["ts"] = now
                downloaded = status.get("downloaded_bytes")
                total = status.get("total_bytes") or status.get("total_bytes_estimate")
                try:
                    pct_val = (float(downloaded) / float(total) * 100.0) if downloaded and total else None
                except Exception:
                    pct_val = None
                speed_bps = status.get("speed")
                eta_s = status.get("eta")
                update_progress(
                    {
                        "status": "downloading",
                        "percent": pct_val,
                        "speed": _format_speed(speed_bps),
                        "eta": _format_eta(eta_s),
                    }
                )
        elif status.get("status") == "finished":
            log("[progress] Download finished, post-processing...")
            update_progress({"status": "finished"})

    return hook


def _postprocessor_hook_factory(log: Callable[[str], None]) -> Callable[[dict], None]:
    def hook(status: dict) -> None:
        if status.get("status") != "finished":
            return
        filename = status.get("filename")
        info = status.get("info_dict") or {}
        epoch = info.get("epoch")
        if not filename or not epoch:
            return
        path = Path(filename)
        suffix = f"_{epoch}"
        if suffix not in path.stem:
            return
        cleaned_stem = path.stem.replace(suffix, "")
        clean_path = path.with_name(f"{cleaned_stem}{path.suffix}")
        if clean_path.exists():
            return
        try:
            path.rename(clean_path)
            log(f"[rename] {clean_path.name}")
        except Exception as exc:
            log(f"[rename] Failed to rename: {exc}")

    return hook


def _parse_playlist_items(items: str) -> list[tuple[int, int | None]]:
    ranges: list[tuple[int, int | None]] = []
    for chunk in items.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, end_s = [part.strip() for part in chunk.split("-", 1)]
            if not start_s:
                continue
            try:
                start_i = int(start_s)
            except ValueError:
                continue
            if end_s:
                try:
                    end_i = int(end_s)
                except ValueError:
                    end_i = None
            else:
                end_i = None
            ranges.append((start_i, end_i))
        else:
            try:
                idx = int(chunk)
            except ValueError:
                continue
            ranges.append((idx, idx))
    return ranges


def _playlist_match_filter(
    ranges: list[tuple[int, int | None]],
) -> Callable[[dict[str, Any]], str | None]:
    def _matches(idx: int) -> bool:
        for start, end in ranges:
            if idx < start:
                continue
            if end is None or idx <= end:
                return True
        return False

    def _filter(info: dict[str, Any]) -> str | None:
        idx = info.get("playlist_index")
        if not isinstance(idx, int):
            return None
        if _matches(idx):
            return None
        return "skip playlist item"

    return _filter


def _playlist_ranges_count(ranges: list[tuple[int, int | None]]) -> int | None:
    if not ranges:
        return None
    total = 0
    for start, end in ranges:
        if end is None:
            return None
        total += max(0, end - start + 1)
    return total


def _playlist_position_for_index(
    ranges: list[tuple[int, int | None]], idx: int
) -> int | None:
    if not ranges:
        return idx
    position = 0
    for start, end in ranges:
        if idx < start:
            continue
        if end is None or idx <= end:
            position += idx - start + 1
            return position
        position += max(0, end - start + 1)
    return None


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
