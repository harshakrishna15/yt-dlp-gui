"""Bounded, cancellable inspection without decoding the downloaded video."""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from .yt_dlp_cli import MetadataCancelled


def _check_cancel(event: threading.Event | None) -> None:
    if event is not None and event.is_set():
        raise MetadataCancelled()


def _probe(binary: Path, path: Path, args: list[str], event, consume):
    _check_cancel(event)
    # Spool packet metadata to disk so a long video cannot fill RAM or a pipe.
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            [str(binary), "-v", "error", *args, str(path)],
            stdout=output, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 20
        try:
            while process.poll() is None:
                _check_cancel(event)
                if time.monotonic() >= deadline or output.tell() > 64 * 1024 * 1024:
                    return None
                time.sleep(0.05)
            _check_cancel(event)
            if process.returncode or output.tell() > 64 * 1024 * 1024:
                return None
            output.seek(0)
            return consume(output)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)


def probe_media(path: Path, binary: Path, cancel_event=None) -> dict:
    try:
        result = _probe(binary, path, ["-show_streams", "-show_format", "-of", "json"],
                        cancel_event, json.load)
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def media_duration(info: dict) -> float | None:
    try:
        value = float(info.get("format", {}).get("duration", 0))
        return value if math.isfinite(value) and value > 0 else None
    except (TypeError, ValueError):
        return None


def compatible_streams(info: dict) -> dict | None:
    streams = info.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1:
        return None
    video = videos[0]
    try:
        if (video.get("codec_name") != "h264"
                or video.get("pix_fmt") != "yuv420p"
                or video.get("profile") not in {"Baseline", "Constrained Baseline", "Main", "High"}
                or not 0 < int(video.get("level", 0)) <= 41
                or video.get("field_order") != "progressive"
                or video.get("color_transfer") in {"smpte2084", "arib-std-b67"}
                or any(int(video.get(d, 0)) <= 0 or int(video[d]) % 2 for d in ("width", "height"))):
            return None
        rate = Fraction(video.get("avg_frame_rate", "0"))
        if rate <= 0 or rate != Fraction(video.get("r_frame_rate", "0")):
            return None
        if any(a.get("codec_name") != "aac" or a.get("profile") != "LC"
               or int(a.get("sample_rate", 0)) != 48000 for a in audios):
            return None
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return video


def is_edit_compatible(path: Path, binary: Path, info: dict, cancel_event=None) -> bool:
    video = compatible_streams(info)
    if video is None:
        return False
    try:
        ticks = 1 / (Fraction(video["avg_frame_rate"]) * Fraction(video["time_base"]))
        if ticks.denominator != 1:
            return False

        def constant_timing(output):
            count = 0
            previous = None
            packets = None
            # Equal nominal/average rates alone do not prove constant timing.
            for event, packet in ET.iterparse(output, events=("start", "end")):
                _check_cancel(cancel_event)
                if event == "start" and packet.tag == "packets":
                    packets = packet
                if event != "end" or packet.tag != "packet":
                    continue
                dts = int(packet.attrib["dts"])
                if int(packet.attrib["duration"]) != ticks or (previous is not None and dts - previous != ticks):
                    return False
                previous = dts
                count += 1
                packet.clear()
                if packets is not None:
                    packets.remove(packet)
            return count > 1

        return bool(_probe(binary, path, [
            "-select_streams", str(video["index"]), "-show_packets",
            "-show_entries", "packet=dts,duration", "-of", "xml",
        ], cancel_event, constant_timing))
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OSError, ET.ParseError, subprocess.SubprocessError):
        return False
