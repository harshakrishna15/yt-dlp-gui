from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QFontMetrics

from ..core import error_feedback as core_error_feedback
from ..common.types import SourceSummary
from .constants import LOG_MAX_LINES

if TYPE_CHECKING:
    from .app import QtYtDlpGui


class WindowFeedbackMixin:
    def _set_metric_label_text(self: "QtYtDlpGui", label, text: str) -> None:
        label.setText(text)
        label.updateGeometry()

    def _set_post_download_output_dir(
        self: "QtYtDlpGui", output_path: Path
    ) -> None:
        resolved = Path(output_path).expanduser()
        self._post_download_output_dir = resolved

    def _clear_post_download_output_dir(self: "QtYtDlpGui") -> None:
        self._post_download_output_dir = None

    def _elide_text_right_with_dots(
        self: "QtYtDlpGui",
        text: str,
        *,
        width: int,
        metrics: QFontMetrics,
    ) -> str:
        clean = str(text or "")
        if width <= 0:
            return "..."
        if metrics.horizontalAdvance(clean) <= width:
            return clean
        dots = "..."
        dots_width = metrics.horizontalAdvance(dots)
        if dots_width >= width:
            return dots
        low = 0
        high = len(clean)
        while low < high:
            mid = (low + high + 1) // 2
            candidate = clean[:mid]
            if metrics.horizontalAdvance(candidate) + dots_width <= width:
                low = mid
            else:
                high = mid - 1
        trimmed = clean[:low].rstrip()
        if not trimmed:
            return dots
        return f"{trimmed}{dots}"

    def _refresh_current_item_text(self: "QtYtDlpGui") -> None:
        progress_clean = str(self._current_item_progress or "-").strip() or "-"
        title_clean = (
            re.sub(r"\s+", " ", str(self._current_item_title or "-").strip()) or "-"
        )
        prefix = "Item: " if progress_clean == "-" else f"Item: {progress_clean} - "
        full_text = f"{prefix}{title_clean}"
        metrics = QFontMetrics(self.item_label.font())
        if (not self.isVisible()) or self.item_label.width() <= 0:
            shown_text = full_text
        else:
            width = max(80, self.item_label.width() - 4)
            if metrics.horizontalAdvance(full_text) <= width:
                shown_text = full_text
            else:
                prefix_width = metrics.horizontalAdvance(prefix)
                if prefix_width >= width:
                    shown_text = self._elide_text_right_with_dots(
                        full_text,
                        width=width,
                        metrics=metrics,
                    )
                else:
                    shown_title = self._elide_text_right_with_dots(
                        title_clean,
                        width=max(0, width - prefix_width),
                        metrics=metrics,
                    )
                    shown_text = f"{prefix}{shown_title}"
        self.item_label.setText(shown_text)
        self.item_label.setToolTip(str(self._current_item_title_tooltip or "-"))
        self._refresh_ready_summary_text()

    def _set_current_item_display(
        self: "QtYtDlpGui", *, progress: str, title: str
    ) -> None:
        progress_clean = str(progress or "-").strip() or "-"
        raw_title = str(title if title is not None else "-")
        if not raw_title.strip():
            raw_title = "-"
        title_clean = re.sub(r"\s+", " ", raw_title.strip()) or "-"
        self._current_item_progress = progress_clean
        self._current_item_title = title_clean
        self._current_item_title_tooltip = raw_title
        self._refresh_current_item_text()
        self.item_label.setVisible(True)

    def _set_current_item_from_text(self: "QtYtDlpGui", item: str) -> None:
        clean = re.sub(r"\s+", " ", str(item or "").strip())
        if not clean:
            self._set_current_item_display(progress="-", title="-")
            return
        match = re.match(r"^(\d+/\d+)\s+(.+)$", clean)
        if match:
            self._set_current_item_display(
                progress=match.group(1),
                title=match.group(2),
            )
            return
        self._set_current_item_display(progress="-", title=clean)

    def _append_log(self: "QtYtDlpGui", text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        error_text = core_error_feedback.error_text_from_log(clean)
        if error_text:
            self._last_error_log = error_text
        self._log_lines.append(clean)
        if len(self._log_lines) > LOG_MAX_LINES:
            self._log_lines = self._log_lines[-LOG_MAX_LINES:]
        self.logs_view.appendPlainText(clean)
        self._refresh_logs_panel_state()
        if self._active_panel_name != "logs" and self._is_attention_log(clean):
            self._set_logs_alert(True)

    def _clear_logs(self: "QtYtDlpGui") -> None:
        self._log_lines.clear()
        self._last_error_log = ""
        self._status_presenter.last_source_feedback_log = None
        self._last_source_feedback_log = None
        self.logs_view.clear()
        self._refresh_logs_panel_state()
        self._set_logs_alert(False)

    def _set_status(self: "QtYtDlpGui", text: str, *, log: bool = True) -> None:
        self._status_presenter.set_status(
            text,
            set_status_text=self.status_value.setText,
            append_log=self._append_log,
            log=log,
        )

    def _set_source_summary(
        self: "QtYtDlpGui", summary: SourceSummary | dict[str, object] | None
    ) -> None:
        del summary
        self._refresh_queue_preview_card()

    def _set_preview_title(self: "QtYtDlpGui", title: str) -> None:
        self._preview_title_raw = str(title or "").strip()
        self._refresh_queue_preview_card()

    def _refresh_queue_preview_card(self: "QtYtDlpGui") -> None:
        return

    def _refresh_queue_empty_state(self: "QtYtDlpGui") -> None:
        return

    def _stop_progress_animation(self: "QtYtDlpGui") -> None:
        if self._progress_anim is None:
            return
        anim = self._progress_anim
        self._progress_anim = None
        if anim in self._active_animations:
            self._active_animations.remove(anim)
        anim.stop()
        anim.deleteLater()

    def _animate_progress_bar_to(
        self: "QtYtDlpGui", percent: float, *, immediate: bool = False
    ) -> None:
        clamped = max(0.0, min(100.0, float(percent)))
        target = int(round(clamped * 10))
        if immediate:
            self._stop_progress_animation()
            self.progress_bar.setValue(target)
            return
        if target == self.progress_bar.value():
            return
        self._stop_progress_animation()
        anim = QPropertyAnimation(self.progress_bar, b"value", self)
        anim.setDuration(220)
        anim.setStartValue(self.progress_bar.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_anim = anim
        self._track_animation(anim)
        anim.start()

    def _queue_overall_progress_percent(
        self: "QtYtDlpGui", item_percent: float = 0.0
    ) -> float | None:
        if not self.queue_active or self.queue_index is None:
            return None
        total_items = len(self.queue_items)
        if total_items <= 0:
            return None
        completed_before_current = max(
            0,
            min(int(self.queue_index), total_items),
        )
        current_ratio = max(0.0, min(100.0, float(item_percent))) / 100.0
        return (
            (float(completed_before_current) + current_ratio) / float(total_items)
        ) * 100.0

    def _prepare_next_queue_item_progress(self: "QtYtDlpGui") -> None:
        overall_percent = self._queue_overall_progress_percent(0.0)
        if overall_percent is not None:
            self._animate_progress_bar_to(overall_percent, immediate=True)
            self._set_metric_label_text(
                self.progress_label, f"Progress: {overall_percent:.1f}%"
            )
        self._set_metric_label_text(self.speed_label, "Speed: -")
        self._set_metric_label_text(self.eta_label, "ETA: -")

    def _reset_progress_summary(self: "QtYtDlpGui") -> None:
        self._stop_progress_animation()
        self.progress_bar.setValue(0)
        self._set_metric_label_text(self.progress_label, "Progress: -")
        self._set_metric_label_text(self.speed_label, "Speed: -")
        self._set_metric_label_text(self.eta_label, "ETA: -")
        self._set_current_item_display(progress="-", title="-")
        self._set_metrics_visible(False)

    def _on_progress_update(self: "QtYtDlpGui", payload: object) -> None:
        if not isinstance(payload, dict):
            return
        status = payload.get("status")
        if status == "downloading":
            self._set_metrics_visible(True)
            percent = payload.get("percent")
            speed = payload.get("speed")
            eta = payload.get("eta")
            playlist_eta = str(payload.get("playlist_eta") or "").strip()
            if isinstance(percent, (int, float)):
                display_percent = float(percent)
                queue_percent = self._queue_overall_progress_percent(display_percent)
                if queue_percent is not None:
                    display_percent = queue_percent
                self._animate_progress_bar_to(display_percent)
                self._set_metric_label_text(
                    self.progress_label, f"Progress: {display_percent:.1f}%"
                )
            if isinstance(speed, str):
                self._set_metric_label_text(self.speed_label, f"Speed: {speed or '-'}")
            eta_text = str(eta).strip() if isinstance(eta, str) else ""
            if playlist_eta:
                self._set_metric_label_text(
                    self.eta_label, f"ETA: {eta_text or '-'} / {playlist_eta}"
                )
            elif eta_text:
                self._set_metric_label_text(self.eta_label, f"ETA: {eta_text}")
            else:
                self._set_metric_label_text(self.eta_label, "ETA: -")
        elif status == "item":
            if not self._show_progress_item:
                return
            queue_percent = self._queue_overall_progress_percent(0.0)
            if queue_percent is not None:
                self._animate_progress_bar_to(queue_percent, immediate=True)
                self._set_metric_label_text(
                    self.progress_label, f"Progress: {queue_percent:.1f}%"
                )
                self._set_metric_label_text(self.speed_label, "Speed: -")
                self._set_metric_label_text(self.eta_label, "ETA: -")
            item = str(payload.get("item") or "").strip()
            if item:
                self._set_current_item_from_text(item)
        elif status == "finished":
            queue_percent = self._queue_overall_progress_percent(100.0)
            if queue_percent is not None:
                self._animate_progress_bar_to(queue_percent, immediate=True)
                self._set_metric_label_text(
                    self.progress_label, f"Progress: {queue_percent:.1f}%"
                )
            self._set_metric_label_text(self.eta_label, "ETA: Finalizing")
        elif status == "cancelled":
            self._reset_progress_summary()
        if self.queue_active:
            self._refresh_queue_panel()
