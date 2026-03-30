from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class StatusPresenter:
    last_source_feedback_log: tuple[str, str] | None = None

    def set_status(
        self,
        text: str,
        *,
        set_status_text: Callable[[str], None],
        append_log: Callable[[str], None],
        log: bool = True,
    ) -> None:
        value = (text or "").strip() or "Idle"
        set_status_text(value)
        if log:
            append_log(f"[status] {value}")

    def set_source_feedback(
        self,
        text: str,
        *,
        tone: str,
        append_log: Callable[[str], None],
    ) -> None:
        tone_value = (
            tone
            if tone in {"neutral", "loading", "success", "warning", "error", "hidden"}
            else "neutral"
        )
        message = str(text or "").strip()
        if tone_value == "neutral":
            self.last_source_feedback_log = None
            return
        if not message:
            if tone_value == "hidden":
                self.last_source_feedback_log = None
            return
        key = (tone_value, message)
        if self.last_source_feedback_log == key:
            return
        self.last_source_feedback_log = key
        prefix_map = {
            "neutral": "[source]",
            "loading": "[source][loading]",
            "success": "[source][success]",
            "warning": "[source][warning]",
            "error": "[source][error]",
        }
        prefix = prefix_map.get(tone_value, "[source]")
        append_log(f"{prefix} {message}")
