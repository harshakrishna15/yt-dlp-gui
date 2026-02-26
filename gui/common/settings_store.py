from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_DEFAULT_UI_LAYOUT = "Simple"
_VALID_UI_LAYOUTS = {"simple", "classic"}
_DEFAULT_NETWORK_TIMEOUT = "20"
_DEFAULT_NETWORK_RETRIES = "1"
_DEFAULT_RETRY_BACKOFF = "1.5"
_DEFAULT_CONCURRENT_FRAGMENTS = "4"


def user_settings_path() -> Path:
    override = os.environ.get("YT_DLP_GUI_SETTINGS_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".yt-dlp-gui" / "settings.json"


def default_settings(*, default_output_dir: str | None = None) -> dict[str, Any]:
    output_dir = str(default_output_dir or "").strip() or str(Path.home() / "Downloads")
    timeout, retries, backoff, fragments = _network_defaults()
    return {
        "output_dir": output_dir,
        "subtitle_languages": "",
        "write_subtitles": False,
        "network_timeout": timeout,
        "network_retries": retries,
        "retry_backoff": backoff,
        "concurrent_fragments": fragments,
        "ui_layout": _DEFAULT_UI_LAYOUT,
        "show_header_icons": True,
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

    subtitle_languages = str(payload.get("subtitle_languages", "")).strip()
    out["subtitle_languages"] = subtitle_languages
    out["write_subtitles"] = bool(payload.get("write_subtitles"))

    timeout = str(payload.get("network_timeout", "")).strip()
    retries = str(payload.get("network_retries", "")).strip()
    backoff = str(payload.get("retry_backoff", "")).strip()
    fragments = str(payload.get("concurrent_fragments", "")).strip()
    out["network_timeout"] = timeout or str(defaults["network_timeout"])
    out["network_retries"] = retries or str(defaults["network_retries"])
    out["retry_backoff"] = backoff or str(defaults["retry_backoff"])
    out["concurrent_fragments"] = _coerce_fragments(
        fragments or str(defaults["concurrent_fragments"])
    )

    layout = str(payload.get("ui_layout", "")).strip().lower()
    if layout in _VALID_UI_LAYOUTS:
        out["ui_layout"] = "Classic" if layout == "classic" else "Simple"

    out["show_header_icons"] = bool(
        payload.get("show_header_icons", defaults.get("show_header_icons", True))
    )
    out["open_folder_after_download"] = bool(payload.get("open_folder_after_download"))
    return out


def _network_defaults() -> tuple[str, str, str, str]:
    try:
        from . import download

        return (
            str(download.YDL_SOCKET_TIMEOUT_SECONDS),
            str(download.YDL_ATTEMPT_RETRIES),
            str(download.YDL_RETRY_BACKOFF_SECONDS),
            str(download.YDL_MAX_CONCURRENT_FRAGMENTS),
        )
    except Exception:
        return (
            _DEFAULT_NETWORK_TIMEOUT,
            _DEFAULT_NETWORK_RETRIES,
            _DEFAULT_RETRY_BACKOFF,
            _DEFAULT_CONCURRENT_FRAGMENTS,
        )


def _coerce_fragments(value: str) -> str:
    try:
        parsed = int(float(str(value or "").strip()))
    except (TypeError, ValueError, OverflowError):
        parsed = int(_DEFAULT_CONCURRENT_FRAGMENTS)
    parsed = max(1, min(4, parsed))
    return str(parsed)
