from typing import Any

from .shared_types import FormatInfo
from .tooling import resolve_binary

try:
    import yt_dlp
except ModuleNotFoundError as exc:
    raise SystemExit(
        "yt-dlp is not installed. Activate your venv and run: pip install -r requirements.txt"
    ) from exc


def fetch_info(url: str) -> dict:
    """Fetch info dict without downloading."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "playlist_items": "1",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False, process=True)


def detect_toolchain() -> dict[str, str]:
    yt_dlp_bin, yt_dlp_source = resolve_binary("yt-dlp")
    ffmpeg_bin, ffmpeg_source = resolve_binary("ffmpeg")
    ffprobe_bin, ffprobe_source = resolve_binary("ffprobe")
    yt_dlp_module_version = getattr(getattr(yt_dlp, "version", None), "__version__", "unknown")
    return {
        "yt_dlp_module_version": str(yt_dlp_module_version),
        "yt_dlp_binary_source": yt_dlp_source,
        "yt_dlp_binary_path": str(yt_dlp_bin) if yt_dlp_bin else "not found",
        "ffmpeg_source": ffmpeg_source,
        "ffmpeg_path": str(ffmpeg_bin) if ffmpeg_bin else "not found",
        "ffprobe_source": ffprobe_source,
        "ffprobe_path": str(ffprobe_bin) if ffprobe_bin else "not found",
    }

def split_and_filter_formats(
    formats: list[FormatInfo],
) -> tuple[list[FormatInfo], list[FormatInfo]]:
    """Split formats into video and audio lists, trimming low-quality entries."""
    video_heights = [fmt.get("height") or 0 for fmt in formats if (fmt.get("vcodec") or "") != "none"]
    max_height = max(video_heights) if video_heights else 0
    video_min_height = 0 if max_height <= 480 else 480

    audio_formats = [f for f in formats if (f.get("vcodec") or "") == "none"]
    max_audio_br = max((f.get("abr") or f.get("tbr") or 0) for f in audio_formats) if audio_formats else 0
    audio_min_br = 0 if max_audio_br <= 128 else 128

    video_list: list[FormatInfo] = []
    audio_list: list[FormatInfo] = []
    for fmt in formats:
        vcodec = fmt.get("vcodec") or ""
        height = fmt.get("height") or 0
        abr = fmt.get("abr") or fmt.get("tbr") or 0
        if vcodec != "none":
            if height and height < video_min_height:
                continue
            video_list.append(fmt)
        else:
            if abr and abr < audio_min_br:
                continue
            audio_list.append(fmt)
    return video_list, audio_list


def collapse_formats(formats: list[FormatInfo]) -> list[FormatInfo]:
    """Collapse near-duplicate formats (same container/codecs/resolution/fps), keep best bitrate."""
    collapsed: dict[tuple, FormatInfo] = {}
    for fmt in formats:
        vcodec = fmt.get("vcodec") or ""
        acodec = fmt.get("acodec") or ""
        ext = fmt.get("ext") or ""
        height = fmt.get("height") or 0
        fps = fmt.get("fps") or 0
        abr = fmt.get("abr") or 0
        tbr = fmt.get("tbr") or 0
        is_audio = vcodec == "none"
        sig = (
            is_audio,
            ext,
            vcodec if not is_audio else acodec,
            height if not is_audio else 0,
            fps if not is_audio else 0,
        )
        current = collapsed.get(sig)
        if current is None or (tbr or abr or 0) > (current.get("tbr") or current.get("abr") or 0):
            collapsed[sig] = fmt
    return list(collapsed.values())


def sort_formats(formats: list[FormatInfo]) -> list[FormatInfo]:
    def sort_key(fmt: FormatInfo) -> tuple:
        vcodec = fmt.get("vcodec") or ""
        ext = fmt.get("ext") or ""
        height = fmt.get("height") or 0
        abr = fmt.get("abr") or fmt.get("tbr") or 0
        is_audio = vcodec == "none"
        return (
            1 if is_audio else 0,
            0 if ext == "mp4" else 1,
            0 if "avc" in vcodec else 1,
            -height,
            -abr,
        )

    return sorted(formats, key=sort_key)


def label_format(fmt: FormatInfo) -> str:
    fmt_id = fmt.get("format_id", "")
    ext = (fmt.get("ext") or "").upper()
    vcodec = fmt.get("vcodec") or ""
    acodec = fmt.get("acodec") or ""
    height = fmt.get("height")
    width = fmt.get("width")
    fps = fmt.get("fps")
    note = fmt.get("format_note") or ""
    abr = fmt.get("abr") or fmt.get("tbr")
    size_estimate = estimate_filesize_bytes(fmt)
    size_text = humanize_bytes(size_estimate) if size_estimate else ""

    if vcodec == "none":
        quality = f"{int(abr)}k" if abr else "Audio"
        codec = acodec or "audio"
        size_part = f" ~{size_text}" if size_text else ""
        return f"Audio {ext} {quality} ({codec}){size_part} [{fmt_id}]"

    res = f"{height}p" if height else "Video"
    if height and width:
        res = f"{height}p {width}x{height}"
    fps_txt = f"{fps}fps" if fps else ""
    codec_txt = " + ".join([c for c in [vcodec, acodec] if c and c != "none"])
    parts = [res, ext]
    if fps_txt:
        parts.append(fps_txt)
    if note:
        parts.append(f"[{note}]")
    if size_text:
        parts.append(f"~{size_text}")
    if codec_txt:
        parts.append(f"({codec_txt})")
    label = " ".join(parts)
    return f"{label} [{fmt_id}]"


def estimate_filesize_bytes(fmt: FormatInfo) -> int | None:
    value = fmt.get("filesize")
    if not value:
        value = fmt.get("filesize_approx")
    try:
        size_i = int(value)
    except Exception:
        return None
    if size_i <= 0:
        return None
    return size_i


def humanize_bytes(size_bytes: int | None) -> str:
    if not size_bytes:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    units = ["KiB", "MiB", "GiB", "TiB"]
    value = float(size_bytes)
    unit_idx = -1
    while value >= 1024.0 and unit_idx < len(units) - 1:
        value /= 1024.0
        unit_idx += 1
    if unit_idx <= 0:
        return f"{value:.0f} {units[max(0, unit_idx)]}"
    return f"{value:.1f} {units[unit_idx]}"


def build_labeled_formats(formats: list[FormatInfo]) -> list[tuple[str, FormatInfo]]:
    ordered = sort_formats(collapse_formats(formats))
    seen_labels = set()
    labeled: list[tuple[str, FormatInfo]] = []
    for fmt in ordered:
        fmt_id = fmt.get("format_id")
        if not fmt_id:
            continue
        label = label_format(fmt)
        if label in seen_labels:
            label = f"{label} ({fmt_id})"
        seen_labels.add(label)
        labeled.append((label, fmt))
    return labeled


def extract_audio_languages(formats: list[FormatInfo]) -> list[str]:
    """Collect normalized audio language codes from available audio formats."""
    seen: set[str] = set()
    languages: list[str] = []
    for fmt in formats:
        if (fmt.get("vcodec") or "") != "none":
            continue
        lang_raw = fmt.get("language")
        if not isinstance(lang_raw, str):
            continue
        lang = lang_raw.strip().lower()
        if not lang or lang in {"none", "und", "unknown", "n/a", "na"}:
            continue
        if lang in seen:
            continue
        seen.add(lang)
        languages.append(lang)
    return sorted(languages)
