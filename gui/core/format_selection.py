from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .. import format_pipeline


@dataclass(frozen=True)
class ModeSelectionResult:
    labels: list[str]
    lookup: dict[str, dict]
    codec_fallback_used: bool = False


def codec_matches_preference(vcodec_raw: str, codec_pref: str) -> bool:
    vcodec = (vcodec_raw or "").strip().lower()
    pref = (codec_pref or "").strip().lower()
    if not pref or pref == "any":
        return True
    if pref.startswith("avc1"):
        return ("avc1" in vcodec) or ("h264" in vcodec)
    if pref.startswith("av01"):
        return ("av01" in vcodec) or ("av1" in vcodec)
    return pref in vcodec


def _filter_video_formats(
    *,
    labels: list[str],
    lookup: dict[str, dict],
    format_filter: str,
    codec_filter: str,
    allow_any_codec: bool,
) -> tuple[list[str], dict[str, dict]]:
    filtered_labels: list[str] = []
    filtered_lookup: dict[str, dict] = {}
    if format_filter in {"mp4", "webm"} and (allow_any_codec or codec_filter):
        for label in labels:
            fmt_info = lookup.get(label) or {}
            if fmt_info.get("custom_format"):
                filtered_labels.append(label)
                filtered_lookup[label] = fmt_info
                continue
            ext = (fmt_info.get("ext") or "").lower()
            if format_filter == "mp4" and ext != "mp4":
                continue
            if format_filter == "webm" and ext != "webm":
                continue
            if not allow_any_codec and codec_filter.lower() != "any":
                vcodec = (fmt_info.get("vcodec") or "").lower()
                if not codec_matches_preference(vcodec, codec_filter):
                    continue
            filtered_labels.append(label)
            filtered_lookup[label] = fmt_info
    return filtered_labels, filtered_lookup


def select_mode_formats(
    *,
    mode: str,
    container: str,
    codec: str,
    video_labels: list[str],
    video_lookup: dict[str, dict],
    audio_labels: list[str],
    audio_lookup: dict[str, dict],
    video_containers: tuple[str, ...] = ("mp4", "webm"),
    required_video_codecs: tuple[str, ...] = ("avc1", "av01"),
) -> ModeSelectionResult:
    if mode == "audio":
        labels = list(audio_labels)
        lookup = dict(audio_lookup)
        if not labels:
            labels = [format_pipeline.BEST_AUDIO_LABEL]
            lookup = {
                format_pipeline.BEST_AUDIO_LABEL: dict(format_pipeline.BEST_AUDIO_INFO)
            }
        return ModeSelectionResult(labels=labels, lookup=lookup, codec_fallback_used=False)

    if mode != "video":
        return ModeSelectionResult(labels=[], lookup={}, codec_fallback_used=False)

    if container not in video_containers or codec not in required_video_codecs:
        return ModeSelectionResult(labels=[], lookup={}, codec_fallback_used=False)

    labels, lookup = _filter_video_formats(
        labels=list(video_labels),
        lookup=dict(video_lookup),
        format_filter=container,
        codec_filter=codec,
        allow_any_codec=False,
    )
    codec_fallback_used = False
    if codec and not labels:
        labels, lookup = _filter_video_formats(
            labels=list(video_labels),
            lookup=dict(video_lookup),
            format_filter=container,
            codec_filter=codec,
            allow_any_codec=True,
        )
        codec_fallback_used = bool(labels)

    if not labels:
        labels = ["Best available"]
        lookup = {"Best available": {"custom_format": "bestvideo+bestaudio/best"}}

    return ModeSelectionResult(
        labels=labels,
        lookup=lookup,
        codec_fallback_used=codec_fallback_used,
    )


def resolve_format_for_info(
    *,
    info: dict[str, Any],
    formats: list[dict[str, Any]],
    settings: dict[str, Any],
    log: Callable[[str], None],
) -> dict[str, Any]:
    if not formats:
        raise RuntimeError("No formats found for URL.")

    collections = format_pipeline.build_format_collections(formats)
    video_labels = list(collections["video_labels"])
    video_lookup = dict(collections["video_lookup"])
    audio_labels = list(collections["audio_labels"])
    audio_lookup = dict(collections["audio_lookup"])

    mode = settings.get("mode")
    format_filter = settings.get("format_filter")
    codec_filter = settings.get("codec_filter") or ""
    desired_label = settings.get("format_label") or ""

    if mode == "audio":
        if desired_label in audio_labels:
            label = desired_label
        elif audio_labels:
            label = audio_labels[0]
            if desired_label:
                log(f"[queue] format '{desired_label}' missing; using '{label}'")
        else:
            label = format_pipeline.BEST_AUDIO_LABEL
        return {
            "fmt_label": label,
            "fmt_info": audio_lookup.get(label) or dict(format_pipeline.BEST_AUDIO_INFO),
            "format_filter": format_filter,
            "is_playlist": bool(
                info.get("_type") == "playlist" or info.get("entries") is not None
            ),
            "title": info.get("title") or "",
        }

    filtered_labels, filtered_lookup = _filter_video_formats(
        labels=video_labels,
        lookup=video_lookup,
        format_filter=str(format_filter or ""),
        codec_filter=str(codec_filter),
        allow_any_codec=False,
    )
    if format_filter in {"mp4", "webm"} and codec_filter and not filtered_labels:
        log("[queue] chosen codec not available; using any codec for container")
        filtered_labels, filtered_lookup = _filter_video_formats(
            labels=video_labels,
            lookup=video_lookup,
            format_filter=str(format_filter or ""),
            codec_filter=str(codec_filter),
            allow_any_codec=True,
        )

    if not filtered_labels:
        filtered_labels.append("Best available")
        filtered_lookup["Best available"] = {"custom_format": "bestvideo+bestaudio/best"}

    if desired_label in filtered_labels:
        label = desired_label
    else:
        label = filtered_labels[0]
        if desired_label:
            log(f"[queue] format '{desired_label}' missing; using '{label}'")

    return {
        "fmt_label": label,
        "fmt_info": filtered_lookup.get(label) or {"custom_format": "best"},
        "format_filter": format_filter,
        "is_playlist": bool(
            info.get("_type") == "playlist" or info.get("entries") is not None
        ),
        "title": info.get("title") or "",
    }
