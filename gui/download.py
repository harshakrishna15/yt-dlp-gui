import time
from pathlib import Path
from typing import Callable, Dict, Tuple

from yt_dlp import YoutubeDL


def run_download(
    url: str,
    output_dir: Path,
    fmt_info: dict | None,
    fmt_label: str,
    format_filter: str,
    convert_to_mp4: bool,
    log: Callable[[str], None],
    update_progress: Callable[[dict], None],
) -> None:
    """Run a yt-dlp download with progress callbacks."""
    fmt_id = fmt_info.get("format_id") if fmt_info else None
    is_audio_only = fmt_info and (
        fmt_info.get("vcodec") in (None, "none") or fmt_info.get("is_audio_only")
    )
    is_video_only = (
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

    postprocessors: list[dict] = []
    pp_args: list[str] = []
    merge_output_format = target_container if target_container in {"mp4", "webm"} else None

    if is_audio_only or fmt == "bestaudio/best":
        merge_output_format = None
        preferred_audio_codec = "opus" if target_container == "webm" else "m4a"
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
        pp_args = [
            "-movflags",
            "+faststart",
        ]
    elif target_container == "webm" and convert_to_mp4:
        merge_output_format = "mp4"
        postprocessors = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]
        pp_args = ["-movflags", "+faststart"]
    else:
        postprocessors = []
        pp_args = []

    opts = {
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "format": fmt,
        "progress_hooks": [
            _progress_hook_factory(log, update_progress),
        ],
        "noplaylist": False,
        "merge_output_format": merge_output_format,
        "postprocessors": postprocessors,
        "postprocessor_args": pp_args,
    }

    log(f"[start] {url}")
    start_ts = time.time()
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # broad to surface in UI
        log(f"[error] {exc}")
    else:
        log("[done] Download complete.")
    finally:
        elapsed = time.time() - start_ts
        log(f"[time] Elapsed: {format_duration(elapsed)}")


def _progress_hook_factory(
    log: Callable[[str], None], update_progress: Callable[[dict], None]
) -> Callable[[dict], None]:
    last_log = {"ts": 0.0}

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


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
