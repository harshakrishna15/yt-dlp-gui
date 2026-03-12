from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def user_settings_path() -> Path:
    override = os.environ.get("YT_DLP_GUI_SETTINGS_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".yt-dlp-gui" / "settings.json"


def default_settings(*, default_output_dir: str | None = None) -> dict[str, Any]:
    output_dir = str(default_output_dir or "").strip() or str(Path.home() / "Downloads")
    return {
        "output_dir": output_dir,
        "edit_friendly_encoder": "auto",
        "open_folder_after_download": False,
    }


def load_settings(*, default_output_dir: str | None = None) -> dict[str, Any]:
    settings = default_settings(default_output_dir=default_output_dir)
    path = user_settings_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return settings
    if not isinstance(payload, dict):
        return settings
    return _normalize_settings(payload, defaults=settings)


def save_settings(
    settings: Mapping[str, Any],
    *,
    default_output_dir: str | None = None,
) -> bool:
    defaults = default_settings(default_output_dir=default_output_dir)
    normalized = _normalize_settings(settings, defaults=defaults)
    path = user_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(normalized, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def _normalize_settings(
    payload: Mapping[str, Any],
    *,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    out = dict(defaults)

    output_dir = str(payload.get("output_dir", "")).strip()
    if output_dir:
        out["output_dir"] = output_dir

    out["edit_friendly_encoder"] = _coerce_edit_friendly_encoder(
        payload.get("edit_friendly_encoder", defaults.get("edit_friendly_encoder", "auto"))
    )
    out["open_folder_after_download"] = bool(payload.get("open_folder_after_download"))
    return out


def _coerce_edit_friendly_encoder(value: object) -> str:
    raw = str(value or "").strip().lower()
    allowed = {"auto", "apple", "nvidia", "amd", "intel", "cpu"}
    if raw in allowed:
        return raw
    aliases = {
        "videotoolbox": "apple",
        "nvenc": "nvidia",
        "amf": "amd",
        "qsv": "intel",
        "libx264": "cpu",
        "x264": "cpu",
    }
    mapped = aliases.get(raw, "")
    if mapped in allowed:
        return mapped
    return "auto"
