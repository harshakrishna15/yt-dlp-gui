import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from ..core import options as core_options
from .types import FormatInfo, ProgressUpdate
from .tooling import resolve_binary

AUDIO_OUTPUT_CODECS = {"m4a", "mp3", "opus", "wav", "flac"}
DOWNLOAD_SUCCESS = "success"
DOWNLOAD_ERROR = "error"
DOWNLOAD_CANCELLED = "cancelled"

# Conservative retry/timeout defaults to reduce transient network failures.
YDL_SOCKET_TIMEOUT_SECONDS = 20
YDL_RETRIES = 10
YDL_FRAGMENT_RETRIES = 10
YDL_EXTRACTOR_RETRIES = 5
YDL_FILE_ACCESS_RETRIES = 3
YDL_ATTEMPT_RETRIES = 1
YDL_RETRY_BACKOFF_SECONDS = 1.5
YDL_PLAYLIST_SLEEP_MIN_SECONDS = 1.0
YDL_PLAYLIST_SLEEP_MAX_SECONDS = 2.5
YDL_MAX_CONCURRENT_FRAGMENTS = 4

# Default MP4 editing preset aimed at smoother Final Cut Pro playback.
EDIT_FRIENDLY_VIDEO_CODEC = "libx264"
EDIT_FRIENDLY_VIDEO_PRESET = "medium"
EDIT_FRIENDLY_VIDEO_PROFILE = "high"
EDIT_FRIENDLY_VIDEO_LEVEL = "4.1"
EDIT_FRIENDLY_AUDIO_CODEC = "aac"
EDIT_FRIENDLY_AUDIO_BITRATE = "192k"
EDIT_FRIENDLY_AUDIO_SAMPLE_RATE = "48000"
EDIT_FRIENDLY_HARDWARE_VIDEO_CODECS = (
    "h264_videotoolbox",
    "h264_nvenc",
    "h264_amf",
    "h264_qsv",
)


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
    network_timeout_s: int = YDL_SOCKET_TIMEOUT_SECONDS,
    concurrent_fragments: int = YDL_MAX_CONCURRENT_FRAGMENTS,
    subtitle_languages: list[str] | None = None,
    write_subtitles: bool = False,
    embed_subtitles: bool = False,
    audio_language: str = "",
    custom_filename: str = "",
    record_output: Callable[[Path], None] | None = None,
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

    custom_stem = core_options.sanitize_custom_filename(custom_filename)
    if playlist_enabled:
        outtmpl = str(output_dir / "%(playlist_index)s - %(title)s_%(epoch)s.%(ext)s")
    elif custom_stem:
        outtmpl = str(output_dir / f"{custom_stem}_%(epoch)s.%(ext)s")
    else:
        outtmpl = str(output_dir / "%(title)s_%(epoch)s.%(ext)s")

    log(f"[start] {url}")
    if fmt_label:
        log(f"[format] {fmt_label}")

    ranges: list[tuple[int, int | None]] = []
    if playlist_enabled and playlist_items:
        ranges = _parse_playlist_items(playlist_items)

    ffmpeg_path, ffmpeg_source = resolve_binary("ffmpeg")

    try:
        requested_fragments = int(float(concurrent_fragments))
    except (TypeError, ValueError, OverflowError):
        requested_fragments = YDL_MAX_CONCURRENT_FRAGMENTS
    fragments = max(1, min(YDL_MAX_CONCURRENT_FRAGMENTS, requested_fragments))

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "format": fmt,
        "progress_hooks": [
            _progress_hook_factory(
                log,
                update_progress,
                cancel_event,
                ranges,
                record_output=record_output,
            )
        ],
        "postprocessor_hooks": [
            _postprocessor_hook_factory(log, record_output=record_output)
        ],
        "noplaylist": not playlist_enabled,
        "merge_output_format": merge_output_format,
        "postprocessors": postprocessors,
        "postprocessor_args": pp_args,
        "socket_timeout": max(1, int(network_timeout_s)),
        "retries": YDL_RETRIES,
        "fragment_retries": YDL_FRAGMENT_RETRIES,
        "extractor_retries": YDL_EXTRACTOR_RETRIES,
        "file_access_retries": YDL_FILE_ACCESS_RETRIES,
        "concurrent_fragment_downloads": fragments,
        "skip_unavailable_fragments": True,
        "continuedl": True,
    }

    # Always pull and embed artwork for both audio and video outputs.
    opts["writethumbnail"] = True
    postprocessors.append({"key": "EmbedThumbnail"})

    if write_subtitles:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        if subtitle_languages:
            opts["subtitleslangs"] = subtitle_languages
        if embed_subtitles and not is_audio_only:
            postprocessors.append({"key": "FFmpegEmbedSubtitle"})
    audio_lang_clean = (audio_language or "").strip()
    if audio_lang_clean and audio_lang_clean.lower() not in {"any", "auto"}:
        opts["format_sort"] = [f"lang:{audio_lang_clean.lower()}"]
    if ffmpeg_path:
        opts["ffmpeg_location"] = str(ffmpeg_path)
        log(f"[ffmpeg] source={ffmpeg_source} path={ffmpeg_path}")
    else:
        log("[ffmpeg] source=missing (some merges/conversions may fail)")
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
    if playlist_enabled:
        opts["sleep_interval"] = float(YDL_PLAYLIST_SLEEP_MIN_SECONDS)
        opts["max_sleep_interval"] = float(
            max(YDL_PLAYLIST_SLEEP_MIN_SECONDS, YDL_PLAYLIST_SLEEP_MAX_SECONDS)
        )
        log(
            "[playlist] random_delay="
            f"{opts['sleep_interval']:.1f}-{opts['max_sleep_interval']:.1f}s"
        )
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
    network_retries: int = YDL_ATTEMPT_RETRIES,
    network_timeout_s: int = YDL_SOCKET_TIMEOUT_SECONDS,
    retry_backoff_s: float = YDL_RETRY_BACKOFF_SECONDS,
    concurrent_fragments: int = YDL_MAX_CONCURRENT_FRAGMENTS,
    subtitle_languages: list[str] | None = None,
    write_subtitles: bool = False,
    embed_subtitles: bool = False,
    audio_language: str = "",
    custom_filename: str = "",
    edit_friendly_encoder: str = "auto",
    record_output: Callable[[Path], None] | None = None,
) -> str:
    """Run a yt-dlp download with progress callbacks."""
    start_ts = time.time()
    result = DOWNLOAD_SUCCESS
    attempts = max(1, int(network_retries) + 1)
    update_warning_logged = {"value": False}

    def _safe_update(payload: ProgressUpdate) -> None:
        try:
            update_progress(payload)
        except Exception as exc:
            if update_warning_logged["value"]:
                return
            update_warning_logged["value"] = True
            log(f"[progress] UI update failed: {exc}")

    def _mark_cancelled() -> None:
        nonlocal result
        result = DOWNLOAD_CANCELLED
        log("[cancelled] Download cancelled.")
        _safe_update({"status": "cancelled"})

    for attempt in range(1, attempts + 1):
        if cancel_event is not None and cancel_event.is_set():
            _mark_cancelled()
            break
        attempt_outputs: list[Path] = []
        seen_outputs: set[str] = set()

        def _record_output(path: Path) -> None:
            try:
                candidate = Path(path)
            except (TypeError, ValueError):
                return
            key = str(candidate)
            if key and key not in seen_outputs:
                seen_outputs.add(key)
                attempt_outputs.append(candidate)
            if record_output is None:
                return
            try:
                record_output(candidate)
            except (OSError, RuntimeError, TypeError, ValueError):
                pass

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
            network_timeout_s=network_timeout_s,
            concurrent_fragments=concurrent_fragments,
            subtitle_languages=subtitle_languages,
            write_subtitles=write_subtitles,
            embed_subtitles=embed_subtitles,
            audio_language=audio_language,
            custom_filename=custom_filename,
            record_output=_record_output,
        )
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except DownloadCancelled:
            _mark_cancelled()
            break
        except KeyboardInterrupt:
            _mark_cancelled()
            break
        except Exception as exc:  # broad to surface in UI
            result = DOWNLOAD_ERROR
            log(f"[error] {exc}")
            if attempt >= attempts:
                break
            wait_s = max(0.0, float(retry_backoff_s)) * (2 ** (attempt - 1))
            log(
                f"[retry] Attempt {attempt}/{attempts - 1} failed; "
                f"retrying in {wait_s:.1f}s"
            )
            if wait_s > 0:
                deadline = time.time() + wait_s
                while time.time() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        _mark_cancelled()
                        break
                    try:
                        time.sleep(0.1)
                    except KeyboardInterrupt:
                        _mark_cancelled()
                        break
                if result == DOWNLOAD_CANCELLED:
                    break
            continue
        else:
            try:
                _postprocess_edit_friendly_mp4(
                    output_paths=attempt_outputs,
                    format_filter=format_filter,
                    fmt_info=fmt_info,
                    edit_friendly_encoder=edit_friendly_encoder,
                    cancel_event=cancel_event,
                    update_progress=_safe_update,
                    log=log,
                )
            except DownloadCancelled:
                _mark_cancelled()
                break
            except Exception as exc:
                log(f"[fcp] edit-friendly step failed: {exc}")
            result = DOWNLOAD_SUCCESS
            log("[done] Download complete.")
            break
    elapsed = time.time() - start_ts
    log(f"[time] Total item time: {format_duration(elapsed)}")
    return result


def _postprocess_edit_friendly_mp4(
    *,
    output_paths: list[Path],
    format_filter: str,
    fmt_info: FormatInfo | None,
    edit_friendly_encoder: str,
    cancel_event: threading.Event | None,
    update_progress: Callable[[ProgressUpdate], None],
    log: Callable[[str], None],
) -> None:
    if not _edit_friendly_mp4_required(format_filter=format_filter, fmt_info=fmt_info):
        return
    mp4_outputs = _unique_existing_mp4_paths(output_paths)
    if not mp4_outputs:
        return

    ffmpeg_path, _ffmpeg_source = resolve_binary("ffmpeg")
    if ffmpeg_path is None:
        log("[fcp] ffmpeg missing; skipped edit-friendly MP4 re-encode.")
        return
    selected_video_codec = _select_edit_friendly_video_codec(
        ffmpeg_path=ffmpeg_path,
        preferred=edit_friendly_encoder,
        log=log,
    )

    ffprobe_path, _ffprobe_source = resolve_binary("ffprobe")
    duration_by_path: dict[str, float | None] = {}
    if ffprobe_path is not None:
        for output_path in mp4_outputs:
            duration_by_path[str(output_path)] = _probe_media_duration_seconds(
                output_path, ffprobe_path
            )
    known_durations = [
        duration
        for duration in duration_by_path.values()
        if isinstance(duration, (int, float)) and duration > 0
    ]
    total_duration_s: float | None = None
    if len(known_durations) == len(mp4_outputs) and known_durations:
        total_duration_s = float(sum(known_durations))

    completed_duration_s = 0.0
    for output_path in mp4_outputs:
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled()
        duration_s = duration_by_path.get(str(output_path))
        success = _reencode_edit_friendly_mp4_file(
            input_path=output_path,
            ffmpeg_path=ffmpeg_path,
            video_codec=selected_video_codec,
            duration_s=duration_s,
            progress_offset_s=completed_duration_s,
            total_duration_s=total_duration_s,
            cancel_event=cancel_event,
            update_progress=update_progress,
            log=log,
        )
        if (not success) and selected_video_codec != EDIT_FRIENDLY_VIDEO_CODEC:
            log(
                "[fcp] Hardware encoder unavailable at runtime; "
                "falling back to libx264."
            )
            selected_video_codec = EDIT_FRIENDLY_VIDEO_CODEC
            success = _reencode_edit_friendly_mp4_file(
                input_path=output_path,
                ffmpeg_path=ffmpeg_path,
                video_codec=selected_video_codec,
                duration_s=duration_s,
                progress_offset_s=completed_duration_s,
                total_duration_s=total_duration_s,
                cancel_event=cancel_event,
                update_progress=update_progress,
                log=log,
            )
        if not success:
            log(f"[fcp] Skipped edit-friendly output for {output_path.name}.")
        if isinstance(duration_s, (int, float)) and duration_s > 0:
            completed_duration_s += float(duration_s)


def _edit_friendly_mp4_required(
    *,
    format_filter: str,
    fmt_info: FormatInfo | None,
) -> bool:
    if (format_filter or "").strip().lower() != "mp4":
        return False
    if fmt_info is None:
        return True
    return not bool(
        fmt_info.get("vcodec") in (None, "none") or fmt_info.get("is_audio_only")
    )


def _unique_existing_mp4_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        try:
            path = Path(raw)
        except (TypeError, ValueError):
            continue
        key = str(path)
        if not key or key in seen:
            continue
        seen.add(key)
        if path.suffix.lower() != ".mp4":
            continue
        if not path.exists():
            continue
        unique.append(path)
    return unique


def _reencode_edit_friendly_mp4_file(
    *,
    input_path: Path,
    ffmpeg_path: Path,
    video_codec: str,
    duration_s: float | None,
    progress_offset_s: float,
    total_duration_s: float | None,
    cancel_event: threading.Event | None,
    update_progress: Callable[[ProgressUpdate], None],
    log: Callable[[str], None],
) -> bool:
    temp_output = input_path.with_name(f"{input_path.stem}.editfriendly.tmp.mp4")
    progress_fd: int | None = None
    progress_path = Path("")
    process: subprocess.Popen[str] | None = None
    try:
        if temp_output.exists():
            temp_output.unlink()
    except OSError:
        pass

    try:
        progress_fd, progress_path_raw = tempfile.mkstemp(
            prefix="yt_dlp_gui_ffmpeg_progress_",
            suffix=".log",
        )
        progress_path = Path(progress_path_raw)
    finally:
        if progress_fd is not None:
            try:
                os.close(progress_fd)
            except OSError:
                pass

    cmd = [
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostats",
        "-progress",
        str(progress_path),
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        *_edit_friendly_video_codec_args(video_codec),
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-vsync",
        "cfr",
        "-c:a",
        EDIT_FRIENDLY_AUDIO_CODEC,
        "-b:a",
        EDIT_FRIENDLY_AUDIO_BITRATE,
        "-ar",
        EDIT_FRIENDLY_AUDIO_SAMPLE_RATE,
        "-movflags",
        "+faststart",
        str(temp_output),
    ]
    log(f"[fcp] Re-encoding for Final Cut ({video_codec}): {input_path.name}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    started_at = time.time()
    last_emit_at = 0.0
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                if process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired):
                        try:
                            process.kill()
                        except OSError:
                            pass
                try:
                    if temp_output.exists():
                        temp_output.unlink()
                except OSError:
                    pass
                raise DownloadCancelled()
            now = time.time()
            if now - last_emit_at >= 0.4:
                snapshot = _read_ffmpeg_progress_snapshot(progress_path)
                out_seconds = _ffmpeg_out_seconds(snapshot)
                speed_ratio = _ffmpeg_speed_ratio(
                    snapshot=snapshot,
                    out_seconds=out_seconds,
                    elapsed_seconds=max(0.001, now - started_at),
                )
                percent = _postprocess_progress_percent(
                    duration_s=duration_s,
                    progress_offset_s=progress_offset_s,
                    total_duration_s=total_duration_s,
                    out_seconds=out_seconds,
                )
                eta_seconds = _postprocess_eta_seconds(
                    duration_s=duration_s,
                    progress_offset_s=progress_offset_s,
                    total_duration_s=total_duration_s,
                    out_seconds=out_seconds,
                    speed_ratio=speed_ratio,
                )
                update_progress(
                    {
                        "status": "downloading",
                        "percent": percent,
                        "speed": f"{speed_ratio:.2f}x" if speed_ratio else "—",
                        "eta": format_duration(eta_seconds)
                        if eta_seconds is not None
                        else "Finalizing",
                        "playlist_eta": "",
                    }
                )
                last_emit_at = now
            return_code = process.poll()
            if return_code is not None:
                break
            time.sleep(0.15)

        stderr_text = ""
        if process.stderr is not None:
            try:
                stderr_text = process.stderr.read().strip()
            except OSError:
                stderr_text = ""
        if process.returncode != 0:
            detail = stderr_text
            message = detail.splitlines()[-1] if detail else "ffmpeg exited with an error"
            log(f"[fcp] Re-encode failed for {input_path.name}: {message}")
            try:
                if temp_output.exists():
                    temp_output.unlink()
            except OSError:
                pass
            return False

        update_progress(
            {
                "status": "downloading",
                "percent": _postprocess_progress_percent(
                    duration_s=duration_s,
                    progress_offset_s=progress_offset_s,
                    total_duration_s=total_duration_s,
                    out_seconds=duration_s if duration_s is not None else 0.0,
                ),
                "speed": "—",
                "eta": "Finalizing",
                "playlist_eta": "",
            }
        )

        try:
            os.replace(temp_output, input_path)
        except OSError as exc:
            log(f"[fcp] Failed to finalize re-encode for {input_path.name}: {exc}")
            try:
                if temp_output.exists():
                    temp_output.unlink()
            except OSError:
                pass
            return False

        log(f"[fcp] Re-encoded for Final Cut: {input_path.name}")
        return True
    finally:
        if process is not None and process.stderr is not None:
            try:
                process.stderr.close()
            except OSError:
                pass
        try:
            if progress_path and progress_path.exists():
                progress_path.unlink()
        except OSError:
            pass


def _edit_friendly_video_codec_args(video_codec: str) -> list[str]:
    codec = (video_codec or "").strip().lower() or EDIT_FRIENDLY_VIDEO_CODEC
    if codec == EDIT_FRIENDLY_VIDEO_CODEC:
        return [
            "-c:v",
            EDIT_FRIENDLY_VIDEO_CODEC,
            "-preset",
            EDIT_FRIENDLY_VIDEO_PRESET,
            "-profile:v",
            EDIT_FRIENDLY_VIDEO_PROFILE,
            "-level:v",
            EDIT_FRIENDLY_VIDEO_LEVEL,
            "-pix_fmt",
            "yuv420p",
        ]
    return [
        "-c:v",
        codec,
        "-pix_fmt",
        "yuv420p",
    ]


def _select_edit_friendly_video_codec(
    *,
    ffmpeg_path: Path,
    preferred: str,
    log: Callable[[str], None],
) -> str:
    preference = core_options.normalize_edit_friendly_encoder_preference(preferred)
    encoders = _available_h264_video_encoders(ffmpeg_path)
    manual_map = {
        "apple": "h264_videotoolbox",
        "nvidia": "h264_nvenc",
        "amd": "h264_amf",
        "intel": "h264_qsv",
        "cpu": EDIT_FRIENDLY_VIDEO_CODEC,
    }
    if preference in manual_map:
        codec = manual_map[preference]
        if codec in encoders:
            log(f"[fcp] Using manual encoder preference: {codec}")
            return codec
        log(
            f"[fcp] Preferred encoder '{preference}' unavailable; "
            "falling back to libx264."
        )
        return EDIT_FRIENDLY_VIDEO_CODEC

    preferred_hardware = _hardware_encoder_priority()
    for codec in preferred_hardware:
        if codec in encoders:
            log(f"[fcp] Using hardware encoder: {codec}")
            return codec
    if EDIT_FRIENDLY_VIDEO_CODEC in encoders:
        log("[fcp] Using software encoder: libx264")
        return EDIT_FRIENDLY_VIDEO_CODEC
    log("[fcp] Could not confirm encoder list; using libx264.")
    return EDIT_FRIENDLY_VIDEO_CODEC


def _hardware_encoder_priority() -> tuple[str, ...]:
    if sys.platform == "darwin":
        return (
            "h264_videotoolbox",
            "h264_nvenc",
            "h264_amf",
            "h264_qsv",
        )
    return (
        "h264_nvenc",
        "h264_amf",
        "h264_qsv",
        "h264_videotoolbox",
    )


def _available_h264_video_encoders(ffmpeg_path: Path) -> set[str]:
    cmd = [str(ffmpeg_path), "-hide_banner", "-encoders"]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return {EDIT_FRIENDLY_VIDEO_CODEC}
    if result.returncode != 0:
        return {EDIT_FRIENDLY_VIDEO_CODEC}
    text = f"{result.stdout}\n{result.stderr}"
    candidates = set(EDIT_FRIENDLY_HARDWARE_VIDEO_CODECS) | {EDIT_FRIENDLY_VIDEO_CODEC}
    found: set[str] = set()
    for codec in candidates:
        if re.search(rf"\b{re.escape(codec)}\b", text):
            found.add(codec)
    if not found:
        return {EDIT_FRIENDLY_VIDEO_CODEC}
    return found


def _probe_media_duration_seconds(path: Path, ffprobe_path: Path) -> float | None:
    cmd = [
        str(ffprobe_path),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    raw = (result.stdout or "").strip().splitlines()
    if not raw:
        return None
    try:
        duration = float(raw[0].strip())
    except (TypeError, ValueError, OverflowError):
        return None
    if duration <= 0:
        return None
    return duration


def _read_ffmpeg_progress_snapshot(progress_path: Path) -> dict[str, str]:
    try:
        text = progress_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    snapshot: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        snapshot[key.strip()] = value.strip()
    return snapshot


def _ffmpeg_out_seconds(snapshot: dict[str, str]) -> float | None:
    for key in ("out_time_us", "out_time_ms"):
        raw = (snapshot.get(key) or "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            continue
        if value < 0:
            continue
        return value / 1_000_000.0 if value >= 1_000.0 else value
    time_text = (snapshot.get("out_time") or "").strip()
    if not time_text:
        return None
    return _parse_hms_seconds(time_text)


def _parse_hms_seconds(value: str) -> float | None:
    match = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", str(value or "").strip())
    if match is None:
        return None
    try:
        hours = int(match.group(1) or "0")
        minutes = int(match.group(2) or "0")
        seconds = float(match.group(3) or "0")
    except (TypeError, ValueError, OverflowError):
        return None
    if minutes < 0 or seconds < 0 or hours < 0:
        return None
    return (hours * 3600) + (minutes * 60) + seconds


def _ffmpeg_speed_ratio(
    *,
    snapshot: dict[str, str],
    out_seconds: float | None,
    elapsed_seconds: float,
) -> float | None:
    raw_speed = (snapshot.get("speed") or "").strip().lower()
    if raw_speed.endswith("x"):
        raw_speed = raw_speed[:-1]
    if raw_speed and raw_speed not in {"n/a", "na", "nan", "inf"}:
        try:
            speed = float(raw_speed)
            if speed > 0:
                return speed
        except (TypeError, ValueError, OverflowError):
            pass
    if out_seconds is None or elapsed_seconds <= 0:
        return None
    estimate = out_seconds / elapsed_seconds
    if estimate <= 0:
        return None
    return estimate


def _postprocess_progress_percent(
    *,
    duration_s: float | None,
    progress_offset_s: float,
    total_duration_s: float | None,
    out_seconds: float | None,
) -> float | None:
    if duration_s is None or duration_s <= 0:
        return None
    current = max(0.0, min(float(out_seconds or 0.0), duration_s))
    if total_duration_s is not None and total_duration_s > 0:
        ratio = (progress_offset_s + current) / total_duration_s
    else:
        ratio = current / duration_s
    ratio = max(0.0, min(1.0, ratio))
    return min(99.5, 90.0 + (ratio * 9.5))


def _postprocess_eta_seconds(
    *,
    duration_s: float | None,
    progress_offset_s: float,
    total_duration_s: float | None,
    out_seconds: float | None,
    speed_ratio: float | None,
) -> float | None:
    if speed_ratio is None or speed_ratio <= 0:
        return None
    if duration_s is None or duration_s <= 0:
        return None
    current = max(0.0, min(float(out_seconds or 0.0), duration_s))
    if total_duration_s is not None and total_duration_s > 0:
        remaining = max(0.0, total_duration_s - (progress_offset_s + current))
    else:
        remaining = max(0.0, duration_s - current)
    return remaining / speed_ratio


def _progress_hook_factory(
    log: Callable[[str], None],
    update_progress: Callable[[ProgressUpdate], None],
    cancel_event: threading.Event | None,
    ranges: list[tuple[int, int | None]],
    *,
    record_output: Callable[[Path], None] | None = None,
) -> Callable[[dict], None]:
    last_log = {"ts": 0.0}
    last_item = {"key": None}
    active_item = {"key": None, "started_at": None}
    completed_items: set[int] = set()
    completed_durations_s: list[float] = []
    update_warning_logged = {"value": False}
    total_items = _playlist_ranges_count(ranges)

    def _safe_update(payload: ProgressUpdate) -> None:
        try:
            update_progress(payload)
        except Exception as exc:
            if update_warning_logged["value"]:
                return
            update_warning_logged["value"] = True
            log(f"[progress] UI update failed: {exc}")

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
        except (TypeError, ValueError, OverflowError):
            return "—"
        m, s = divmod(seconds_i, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:d}:{s:02d}"

    def _as_positive_int(value: object) -> int | None:
        try:
            parsed = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed <= 0:
            return None
        return parsed

    def _as_non_negative_float(value: object) -> float | None:
        try:
            parsed = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed < 0:
            return None
        return parsed

    def _percent_from_status_string(value: object) -> float | None:
        if not isinstance(value, str):
            return None
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", value)
        if not match:
            return None
        return _as_non_negative_float(match.group(1))

    def hook(status: dict) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled()

        info = status.get("info_dict") or {}
        playlist_index = _as_positive_int(info.get("playlist_index"))
        playlist_count = _as_positive_int(
            info.get("playlist_count") or status.get("playlist_count")
        )
        if total_items is not None:
            playlist_count = total_items
        display_index = playlist_index
        if display_index and ranges:
            display_index = _playlist_position_for_index(ranges, display_index)

        title = info.get("title") or ""
        if display_index and last_item["key"] != display_index:
            last_item["key"] = display_index
            active_item["key"] = display_index
            active_item["started_at"] = time.time()
            if playlist_count and display_index:
                log(f"[item] {display_index}/{playlist_count} {title}".strip())
            else:
                log(f"[item] {display_index} {title}".strip())
            item_text = (
                f"{display_index}/{playlist_count} {title}".strip()
                if playlist_count and display_index
                else f"{display_index} {title}".strip()
            )
            _safe_update({"status": "item", "item": item_text})

        if status.get("status") == "downloading":
            now = time.time()
            if now - last_log["ts"] >= 0.8:
                last_log["ts"] = now
                downloaded = status.get("downloaded_bytes")
                total = status.get("total_bytes") or status.get("total_bytes_estimate")
                try:
                    pct_val = (float(downloaded) / float(total) * 100.0) if downloaded and total else None
                except (TypeError, ValueError, ZeroDivisionError):
                    pct_val = None
                if pct_val is None:
                    pct_val = _percent_from_status_string(status.get("_percent_str"))
                eta_s = _as_non_negative_float(status.get("eta"))
                if pct_val is None and eta_s is not None:
                    elapsed_s = _as_non_negative_float(status.get("elapsed"))
                    if elapsed_s is not None:
                        total_time_s = elapsed_s + eta_s
                        if total_time_s > 0:
                            pct_val = (elapsed_s / total_time_s) * 100.0
                if pct_val is not None:
                    pct_val = max(0.0, min(100.0, float(pct_val)))
                speed_bps = status.get("speed")
                playlist_eta = ""
                if playlist_count and display_index and eta_s is not None:
                    remaining_after_current = max(
                        0,
                        int(playlist_count) - len(completed_items) - 1,
                    )
                    avg_item_s = (
                        (sum(completed_durations_s) / len(completed_durations_s))
                        if completed_durations_s
                        else eta_s
                    )
                    playlist_eta = _format_eta(
                        eta_s + (remaining_after_current * max(0.0, avg_item_s))
                    )
                if playlist_count and display_index and int(playlist_count) > 0:
                    completed_before_current = max(0, int(display_index) - 1)
                    item_ratio = ((pct_val or 0.0) / 100.0) if pct_val is not None else 0.0
                    playlist_ratio = (
                        completed_before_current + max(0.0, min(1.0, item_ratio))
                    ) / float(playlist_count)
                    pct_val = max(0.0, min(100.0, playlist_ratio * 100.0))
                elif playlist_count and int(playlist_count) > 0 and pct_val is None:
                    pct_val = (
                        max(0, min(len(completed_items), int(playlist_count)))
                        / float(playlist_count)
                    ) * 100.0
                _safe_update(
                    {
                        "status": "downloading",
                        "percent": pct_val,
                        "speed": _format_speed(speed_bps),
                        "eta": _format_eta(eta_s),
                        "playlist_eta": playlist_eta,
                    }
                )
        elif status.get("status") == "finished":
            if display_index and display_index not in completed_items:
                completed_items.add(display_index)
                if (
                    active_item["key"] == display_index
                    and active_item["started_at"] is not None
                ):
                    duration_s = max(0.0, time.time() - float(active_item["started_at"]))
                    completed_durations_s.append(duration_s)
                    if len(completed_durations_s) > 30:
                        completed_durations_s.pop(0)
                active_item["key"] = None
                active_item["started_at"] = None
            log("[progress] Download finished, post-processing...")
            filename = status.get("filename")
            if filename and record_output is not None:
                try:
                    record_output(Path(filename))
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
            _safe_update({"status": "finished"})

    return hook

def _postprocessor_hook_factory(
    log: Callable[[str], None],
    *,
    record_output: Callable[[Path], None] | None = None,
) -> Callable[[dict], None]:
    def hook(status: dict) -> None:
        if status.get("status") != "finished":
            return
        filename = status.get("filename")
        if not filename:
            return
        path = Path(filename)
        final_path, used_fallback = _choose_clean_name_or_epoch_fallback(path)
        if final_path == path and not used_fallback:
            if record_output is not None:
                try:
                    record_output(path)
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
            return
        if used_fallback:
            log(f"[rename] Clean name exists; using epoch suffix fallback: {path.name}")
            if record_output is not None:
                try:
                    record_output(path)
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
            return
        try:
            path.rename(final_path)
            log(f"[rename] {final_path.name}")
            if record_output is not None:
                try:
                    record_output(final_path)
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
        except OSError as exc:
            log(f"[rename] Failed to rename: {exc}")

    return hook


def _choose_clean_name_or_epoch_fallback(path: Path) -> tuple[Path, bool]:
    clean_path = _path_without_epoch_suffix(path)
    if clean_path == path:
        return path, False
    if clean_path.exists():
        return path, True
    return clean_path, False


def _path_without_epoch_suffix(path: Path) -> Path:
    # Collapse yt-dlp epoch suffixes like "Title_1700000000.ext".
    cleaned_stem = re.sub(r"_(\d{6,})$", "", path.stem)
    if cleaned_stem == path.stem:
        return path
    return path.with_name(f"{cleaned_stem}{path.suffix}")


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
            if start_i <= 0:
                continue
            if end_s:
                try:
                    end_i = int(end_s)
                except ValueError:
                    continue
                if end_i is not None and end_i <= 0:
                    continue
                if end_i is not None and end_i < start_i:
                    continue
            else:
                end_i = None
            ranges.append((start_i, end_i))
        else:
            try:
                idx = int(chunk)
            except ValueError:
                continue
            if idx <= 0:
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
        idx_raw = info.get("playlist_index")
        if isinstance(idx_raw, str):
            try:
                idx = int(idx_raw)
            except ValueError:
                return None
        elif isinstance(idx_raw, int):
            idx = idx_raw
        else:
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
