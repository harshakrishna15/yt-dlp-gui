from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QFontMetrics

from ..core import error_feedback as core_error_feedback
from ..services import app_service
from ..common.types import HistoryItem, SourceSummary
from .constants import HISTORY_MAX_ENTRIES, LOG_MAX_LINES, MIN_WINDOW_HEIGHT
from .state import preview_title_fields

if TYPE_CHECKING:
    from .app import QtYtDlpGui


class WindowFeedbackMixin:
    def _refresh_download_result_view(self: "QtYtDlpGui") -> None:
        show_latest_output = self._latest_output_path is not None
        compact_mode = self.isVisible() and (
            self.height() <= (MIN_WINDOW_HEIGHT - 40)
        )
        card_state = "ready" if show_latest_output else "empty"
        if self.download_result_card.property("state") != card_state:
            self.download_result_card.setProperty("state", card_state)
            self._refresh_widget_style(self.download_result_card)
            self._refresh_widget_style(self.download_result_title)
            self._refresh_widget_style(self.download_result_path)
        if show_latest_output:
            self.download_result_title.setText("Latest completed download")
            self._refresh_last_output_text()
        else:
            self.download_result_title.setText("No completed download yet.")
            self.download_result_path.setText(
                "Files will appear here after a download finishes."
            )
            self.download_result_path.setToolTip("")

        self.open_last_output_folder_button.setVisible(show_latest_output)
        self.copy_output_path_button.setVisible(show_latest_output)
        self.open_last_output_folder_button.setEnabled(
            show_latest_output
            and bool(self._latest_output_path and self._latest_output_path.parent.exists())
        )
        self.copy_output_path_button.setEnabled(show_latest_output)
        self.download_result_card.setVisible(show_latest_output or not compact_mode)

    def _clear_last_output_path(self: "QtYtDlpGui") -> None:
        self._latest_output_path = None
        self.download_result_path.setText(
            "Files will appear here after a download finishes."
        )
        self.download_result_path.setToolTip("")
        self._refresh_download_result_view()

    def _refresh_last_output_text(self: "QtYtDlpGui") -> None:
        if self._latest_output_path is None:
            self.download_result_path.setText(
                "Files will appear here after a download finishes."
            )
            self.download_result_path.setToolTip("")
            return
        full_text = str(self._latest_output_path)
        width = max(80, self.download_result_path.width() - 4)
        metrics = QFontMetrics(self.download_result_path.font())
        shown_text = metrics.elidedText(
            full_text,
            Qt.TextElideMode.ElideMiddle,
            width,
        )
        self.download_result_path.setText(shown_text)
        self.download_result_path.setToolTip(full_text)

    def _set_last_output_path(self: "QtYtDlpGui", output_path: Path) -> None:
        resolved = Path(output_path).expanduser()
        self._latest_output_path = resolved
        self.download_result_path.setToolTip(str(resolved))
        self._refresh_download_result_view()
        QTimer.singleShot(0, self._refresh_last_output_text)

    def _open_last_output_folder(self: "QtYtDlpGui") -> None:
        if self._latest_output_path is None:
            return
        folder = self._latest_output_path.parent
        if not folder.exists():
            return
        self._effects.desktop.open_path(folder)

    def _copy_last_output_path(self: "QtYtDlpGui") -> None:
        if self._latest_output_path is None:
            return
        self._effects.clipboard.set_text(str(self._latest_output_path))
        self._set_status("Output path copied", log=False)

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
        if isinstance(summary, dict):
            badge_text = str(summary.get("badge_text") or "URL").strip() or "URL"
            eyebrow_text = (
                str(summary.get("eyebrow_text") or "Source preview").strip()
                or "Source preview"
            )
            subtitle_text = (
                str(summary.get("subtitle_text") or "").strip()
                or "Choose export settings to start downloading."
            )
            detail_texts = [
                str(summary.get("detail_one_text") or "").strip(),
                str(summary.get("detail_two_text") or "").strip(),
                str(summary.get("detail_three_text") or "").strip(),
            ]
        else:
            badge_text = "URL"
            eyebrow_text = "Source preview"
            subtitle_text = "Title, creator, and duration will appear here."
            detail_texts = ["", "", ""]

        self.source_preview_badge.setText(badge_text)
        self.preview_title_label.setText(eyebrow_text)
        self.source_preview_subtitle.setText(subtitle_text)

        for widget, text in zip(
            (
                self.source_preview_detail_one,
                self.source_preview_detail_two,
                self.source_preview_detail_three,
            ),
            detail_texts,
        ):
            widget.setText(text)
            widget.setVisible(bool(text))

    def _set_preview_title(self: "QtYtDlpGui", title: str) -> None:
        shown, tooltip = preview_title_fields(title)
        self.preview_value.setText(shown)
        self.preview_value.setToolTip(tooltip)
        has_title = bool(str(title or "").strip())
        self.preview_value.setVisible(has_title)
        self.source_preview_placeholder.setVisible(not has_title)
        self._set_widget_property(
            self.preview_value,
            "state",
            "ready" if has_title else "empty",
        )

    def _record_download_output(
        self: "QtYtDlpGui", output_path: Path, source_url: str = ""
    ) -> None:
        recorded = app_service.record_history_output(
            history=self.download_history,
            seen_paths=self._history_seen_paths,
            output_path=output_path,
            source_url=source_url,
            max_entries=HISTORY_MAX_ENTRIES,
        )
        if not recorded:
            return
        self._set_last_output_path(output_path)
        self._refresh_history_panel()

    def _refresh_history_panel(self: "QtYtDlpGui") -> None:
        self.history_list.clear()
        for item in self.download_history:
            timestamp = item.get("timestamp", "")
            name = item.get("name", "")
            self.history_list.addItem(f"{timestamp}  {name}")
        self._refresh_history_panel_state()

    def _selected_history_item(self: "QtYtDlpGui") -> HistoryItem | None:
        row = self.history_list.currentRow()
        if row < 0 or row >= len(self.download_history):
            return None
        return self.download_history[row]

    def _open_selected_history_file(self: "QtYtDlpGui") -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        self._effects.desktop.open_path(path)

    def _open_selected_history_folder(self: "QtYtDlpGui") -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        self._effects.desktop.open_path(path.parent)

    def _clear_download_history(self: "QtYtDlpGui") -> None:
        if not self.download_history:
            return
        self.download_history.clear()
        self._history_seen_paths.clear()
        self._refresh_history_panel()
        self._set_status("Download history cleared")

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

    def _reset_progress_summary(self: "QtYtDlpGui") -> None:
        self._stop_progress_animation()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: -")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")
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
                self._animate_progress_bar_to(float(percent))
                self.progress_label.setText(f"Progress: {float(percent):.1f}%")
            if isinstance(speed, str):
                self.speed_label.setText(f"Speed: {speed or '-'}")
            eta_text = str(eta).strip() if isinstance(eta, str) else ""
            if playlist_eta:
                self.eta_label.setText(f"ETA: {eta_text or '-'} / {playlist_eta}")
            elif eta_text:
                self.eta_label.setText(f"ETA: {eta_text}")
            else:
                self.eta_label.setText("ETA: -")
        elif status == "item":
            if not self._show_progress_item:
                return
            item = str(payload.get("item") or "").strip()
            if item:
                self._set_current_item_from_text(item)
        elif status == "finished":
            self.eta_label.setText("ETA: Finalizing")
        elif status == "cancelled":
            self._reset_progress_summary()
