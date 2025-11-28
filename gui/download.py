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
    update_progress: Callable[[float], None],
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
    log: Callable[[str], None], update_progress: Callable[[float], None]
) -> Callable[[dict], None]:
    last_log = {"ts": 0.0}

    def hook(status: dict) -> None:
        if status.get("status") == "downloading":
            percent = status.get("_percent_str", "").strip()
            speed = status.get("_speed_str", "").strip()
            eta = status.get("_eta_str", "").strip()
            try:
                pct_val = float(percent.replace("%", ""))
            except Exception:
                pct_val = None
            if pct_val is not None:
                update_progress(pct_val)
            now = time.time()
            if now - last_log["ts"] >= 0.8:
                last_log["ts"] = now
                log(f"[progress] {percent} at {speed} (eta {eta})")
        elif status.get("status") == "finished":
            log("[progress] Download finished, post-processing...")
            update_progress(100)

    return hook


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
