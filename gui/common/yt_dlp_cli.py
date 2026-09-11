from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


PROGRESS_PREFIX = "__YTDLPGUI_PROGRESS__"
ITEM_PREFIX = "__YTDLPGUI_ITEM__"
OUTPUT_PREFIX = "__YTDLPGUI_OUTPUT__"


@dataclass(frozen=True)
class YtDlpProcessResult:
    returncode: int
    cancelled: bool


class MetadataCancelled(Exception):
    """Metadata lookup was intentionally cancelled."""


def fetch_info(
    binary: Path,
    url: str,
    *,
    cancel_event: threading.Event | None = None,
    on_status: Callable[[str], None] | None = None,
    timeout: float = 90,
    prefix_args: tuple[str, ...] = (),
) -> dict[str, Any]:
    if cancel_event is not None and cancel_event.is_set():
        raise MetadataCancelled()
    command = [
        str(binary), *prefix_args, "--ignore-config", "--color", "never",
        "--dump-single-json", "--skip-download", "--no-quiet", "--no-progress",
        "--socket-timeout", "15", "--retries", "1", "--extractor-retries", "1",
        "--playlist-items", "1", "--", str(url),
    ]
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            start_new_session=sys.platform != "win32",
            creationflags=_process_creation_flags(),
        )
    except OSError as exc:
        raise RuntimeError(f"Could not run yt-dlp: {exc}") from exc
    events: queue.Queue[tuple[str, str | None]] = queue.Queue()

    def read_stream(kind, stream):
        try:
            for line in stream:
                events.put((kind, line.rstrip("\r\n")))
        finally:
            events.put((kind, None))

    readers = [
        threading.Thread(target=read_stream, args=(kind, stream), daemon=True)
        for kind, stream in (("stdout", process.stdout), ("stderr", process.stderr))
    ]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + max(0, timeout)
    streams = len(readers)
    payload = None
    last_error = ""
    completed = False
    try:
        while streams or process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                raise MetadataCancelled()
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Analysis timed out after {timeout:g} seconds.")
            try:
                kind, line = events.get(timeout=0.05)
            except queue.Empty:
                continue
            if line is None:
                streams -= 1
                continue
            if not line:
                continue
            if len(line) > 64 * 1024 * 1024:
                raise RuntimeError("yt-dlp metadata exceeded the size limit.")
            if kind == "stdout" and line.startswith("{"):
                parsed = _parse_json(line)
                if isinstance(parsed, dict):
                    payload = parsed
                    continue
            if kind == "stderr":
                last_error = line
            if on_status:
                on_status(line[:4000])
        if cancel_event is not None and cancel_event.is_set():
            raise MetadataCancelled()
        if process.wait() != 0:
            raise RuntimeError(last_error or "yt-dlp metadata lookup failed")
        if payload is None:
            raise RuntimeError("yt-dlp returned invalid metadata.")
        completed = True
        return payload
    finally:
        if not completed and (process.poll() is None or streams):
            _terminate_process_tree(process)
        for reader in readers:
            reader.join(timeout=2)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def build_download_args(
    binary: Path,
    *,
    url: str,
    options: dict[str, Any],
) -> list[str]:
    args = [
        str(binary),
        "--ignore-config",
        "--color",
        "never",
        "--newline",
        "--progress",
        "--no-simulate",
        "--progress-template",
        f"download:{PROGRESS_PREFIX}%(progress)j",
        "--print",
        f"before_dl:{ITEM_PREFIX}%(.{{title,playlist_index,playlist_count}})j",
        "--print",
        f"after_move:{OUTPUT_PREFIX}%(filepath)j",
    ]

    _add_value(args, "--output", options.get("outtmpl"))
    _add_value(args, "--format", options.get("format"))
    args.append("--no-playlist" if options.get("noplaylist") else "--yes-playlist")
    _add_value(args, "--merge-output-format", options.get("merge_output_format"))
    _add_value(args, "--socket-timeout", options.get("socket_timeout"))
    _add_value(args, "--retries", options.get("retries"))
    _add_value(args, "--fragment-retries", options.get("fragment_retries"))
    _add_value(args, "--extractor-retries", options.get("extractor_retries"))
    _add_value(args, "--file-access-retries", options.get("file_access_retries"))
    _add_value(
        args,
        "--concurrent-fragments",
        options.get("concurrent_fragment_downloads"),
    )
    if options.get("skip_unavailable_fragments"):
        args.append("--skip-unavailable-fragments")
    if options.get("continuedl"):
        args.append("--continue")

    postprocessors = list(options.get("postprocessors") or [])
    for processor in postprocessors:
        key = str((processor or {}).get("key") or "")
        if key == "FFmpegExtractAudio":
            args.append("--extract-audio")
            _add_value(args, "--audio-format", processor.get("preferredcodec"))
        elif key == "FFmpegVideoConvertor":
            _add_value(args, "--recode-video", processor.get("preferedformat"))
        elif key == "EmbedThumbnail":
            args.append("--embed-thumbnail")
        elif key == "FFmpegEmbedSubtitle":
            args.append("--embed-subs")

    postprocessor_args = list(options.get("postprocessor_args") or [])
    if postprocessor_args:
        args.extend(
            [
                "--postprocessor-args",
                "ffmpeg_o:" + " ".join(str(value) for value in postprocessor_args),
            ]
        )
    if options.get("writethumbnail"):
        args.append("--write-thumbnail")
    if options.get("writesubtitles"):
        args.extend(["--write-subs", "--write-auto-subs"])
    subtitles = list(options.get("subtitleslangs") or [])
    if subtitles:
        args.extend(["--sub-langs", ",".join(str(value) for value in subtitles)])
    for sort_value in list(options.get("format_sort") or []):
        args.extend(["--format-sort", str(sort_value)])
    _add_value(args, "--ffmpeg-location", options.get("ffmpeg_location"))

    playlist_items = str(options.get("playlist_items") or "").strip()
    if playlist_items:
        args.extend(["--playlist-items", _playlist_items_cli_spec(playlist_items)])
    _add_value(args, "--sleep-interval", options.get("sleep_interval"))
    _add_value(args, "--max-sleep-interval", options.get("max_sleep_interval"))

    args.extend(["--", str(url)])
    return args


def run_download_process(
    args: list[str],
    *,
    cancel_event: threading.Event | None,
    on_progress: Callable[[dict[str, Any]], None],
    on_output: Callable[[Path], None],
    log: Callable[[str], None],
) -> YtDlpProcessResult:
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        start_new_session=sys.platform != "win32",
        creationflags=_process_creation_flags(),
    )
    events: queue.Queue[tuple[str, str | None]] = queue.Queue()

    def _read_stream(kind: str, stream) -> None:
        try:
            for line in stream:
                events.put((kind, line.rstrip("\r\n")))
        finally:
            events.put((kind, None))

    readers = (
        threading.Thread(
            target=_read_stream,
            args=("stdout", process.stdout),
            daemon=True,
        ),
        threading.Thread(
            target=_read_stream,
            args=("stderr", process.stderr),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()

    open_streams = 2
    cancelled = False
    current_info: dict[str, Any] = {}
    while open_streams > 0:
        if (
            not cancelled
            and cancel_event is not None
            and cancel_event.is_set()
        ):
            cancelled = True
            _terminate_process_tree(process)
        try:
            kind, line = events.get(timeout=0.1)
        except queue.Empty:
            if process.poll() is not None and not any(reader.is_alive() for reader in readers):
                break
            continue
        if line is None:
            open_streams -= 1
            continue
        if not line:
            continue
        if kind == "stderr":
            log(line)
            continue
        if line.startswith(ITEM_PREFIX):
            payload = _parse_json(line[len(ITEM_PREFIX) :])
            if isinstance(payload, dict):
                current_info = payload
                _emit_progress(
                    process,
                    on_progress,
                    {"status": "starting", "info_dict": current_info},
                )
            continue
        if line.startswith(PROGRESS_PREFIX):
            payload = _parse_json(line[len(PROGRESS_PREFIX) :])
            if isinstance(payload, dict):
                payload["info_dict"] = current_info
                _emit_progress(process, on_progress, payload)
            continue
        if line.startswith(OUTPUT_PREFIX):
            payload = _parse_json(line[len(OUTPUT_PREFIX) :])
            if isinstance(payload, str) and payload.strip():
                on_output(Path(payload))
            continue
        log(line)

    for reader in readers:
        reader.join(timeout=1)
    returncode = process.wait()
    return YtDlpProcessResult(returncode=returncode, cancelled=cancelled)


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if sys.platform == "win32":
        if process.poll() is not None:
            return
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5,
                creationflags=_creation_flags(),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
            process.wait()
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
        pass
    finally:
        # The leader may exit before descendants holding its pipes open.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        process.wait()


def _emit_progress(
    process: subprocess.Popen[str],
    callback: Callable[[dict[str, Any]], None],
    payload: dict[str, Any],
) -> None:
    try:
        callback(payload)
    except BaseException:
        _terminate_process_tree(process)
        raise


def _add_value(args: list[str], option: str, value: object) -> None:
    if value is None or value == "":
        return
    args.extend([option, str(value)])


def _playlist_items_cli_spec(value: str) -> str:
    converted: list[str] = []
    for chunk in str(value or "").split(","):
        clean = chunk.strip()
        if "-" in clean:
            start, end = clean.split("-", 1)
            clean = f"{start.strip()}:{end.strip()}"
        if clean:
            converted.append(clean)
    return ",".join(converted)


def _parse_json(value: str) -> object:
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _last_nonempty_line(value: str) -> str:
    lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if sys.platform == "win32" else 0


def _process_creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) | int(
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    )
