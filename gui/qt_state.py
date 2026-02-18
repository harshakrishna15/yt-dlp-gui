from __future__ import annotations

PREVIEW_TITLE_TOOLTIP_DEFAULT = "Detected title from the source URL."


def preview_title_fields(title: str) -> tuple[str, str]:
    clean = (title or "").strip()
    shown = clean or "-"
    tooltip = clean or PREVIEW_TITLE_TOOLTIP_DEFAULT
    return shown, tooltip

