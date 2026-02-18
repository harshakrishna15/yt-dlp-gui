from __future__ import annotations

from pathlib import Path

from .shared_types import HistoryItem


def normalize_output_path(output_path: Path) -> str:
    if not output_path:
        return ""
    try:
        return str(output_path.expanduser().resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return str(output_path)


def canonicalize_output_path(normalized_path: str) -> tuple[str, str]:
    path_obj = Path(normalized_path)
    canonical_stem = _trim_epoch_suffix(path_obj.stem)
    canonical_path = str(path_obj.with_name(f"{canonical_stem}{path_obj.suffix}"))
    return path_obj.name, canonical_path


def upsert_history_entry(
    history: list[HistoryItem],
    seen_paths: set[str],
    *,
    normalized_path: str,
    source_url: str,
    timestamp: str,
    max_entries: int,
) -> None:
    if not normalized_path:
        return
    file_name, canonical_path = canonicalize_output_path(normalized_path)

    for idx, item in enumerate(history):
        if item.get("canonical_path", item.get("path", "")) != canonical_path:
            continue
        item["timestamp"] = timestamp
        item["path"] = normalized_path
        item["name"] = file_name
        item["source_url"] = source_url
        item["canonical_path"] = canonical_path
        if idx > 0:
            history.pop(idx)
            history.insert(0, item)
        return

    seen_paths.add(canonical_path)
    history.insert(
        0,
        {
            "timestamp": timestamp,
            "path": normalized_path,
            "name": file_name,
            "source_url": source_url,
            "canonical_path": canonical_path,
        },
    )
    while len(history) > max(1, int(max_entries)):
        removed = history.pop()
        removed_path = removed.get("canonical_path", removed.get("path", ""))
        if removed_path:
            seen_paths.discard(removed_path)


def _trim_epoch_suffix(stem: str) -> str:
    # yt-dlp output templates include epoch-like suffixes; trim for dedupe.
    idx = len(stem)
    digits = 0
    while idx > 0 and stem[idx - 1].isdigit():
        idx -= 1
        digits += 1
    if digits >= 6 and idx > 0 and stem[idx - 1] == "_":
        return stem[: idx - 1]
    return stem
