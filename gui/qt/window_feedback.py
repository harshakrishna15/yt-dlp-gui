from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QFontMetrics

from ..common import download, yt_dlp_helpers as helpers
from ..core import error_feedback as core_error_feedback
from ..core import queue_presentation
from ..services import app_service
from ..common.types import HistoryItem, SourceSummary
from .constants import HISTORY_MAX_ENTRIES, LOG_MAX_LINES, MIN_WINDOW_HEIGHT
from .state import preview_title_fields

if TYPE_CHECKING:
    from .app import QtYtDlpGui


class WindowFeedbackMixin:
    def _format_session_speed_bps(
        self: "QtYtDlpGui", speed_bps: float | None
    ) -> str:
        if speed_bps is None or speed_bps <= 0:
            return "-"
        units = ["B/s", "KiB/s", "MiB/s", "GiB/s", "TiB/s"]
        value = float(speed_bps)
        unit_idx = 0
        while value >= 1024.0 and unit_idx < len(units) - 1:
            value /= 1024.0
            unit_idx += 1
        if unit_idx == 0:
            return f"{value:.0f} {units[unit_idx]}"
        return f"{value:.2f} {units[unit_idx]}"

    def _format_session_success_rate(
        self: "QtYtDlpGui", completed: int, failed: int
    ) -> str:
        processed = max(0, int(completed)) + max(0, int(failed))
        if processed <= 0:
            return "-"
        return f"{(max(0, int(completed)) / processed) * 100.0:.0f}%"

    def _refresh_session_metrics(
        self: "QtYtDlpGui", *, now_ts: float | None = None
    ) -> None:
        completed = max(0, int(self._session_completed_items))
        failed = max(0, int(self._session_failed_items))
        avg_speed_bps = (
            self._session_speed_sample_total_bps / self._session_speed_sample_count
            if self._session_speed_sample_count > 0
            else None
        )
        peak_speed_bps = (
            self._session_peak_speed_bps if self._session_peak_speed_bps > 0 else None
        )
        elapsed_text = "-"
        if self._session_started_ts is not None:
            current_ts = (
                float(now_ts)
                if now_ts is not None
                else float(self._effects.clock.now_ts())
            )
            elapsed_text = download.format_duration(
                max(0.0, current_ts - float(self._session_started_ts))
            )
        remaining = 0
        if self._session_total_items > 0 and self._is_downloading:
            remaining = max(0, int(self._session_total_items) - completed - failed)
        label_values = (
            (self.session_completed_value, str(completed)),
            (self.session_failed_value, str(failed)),
            (
                self.session_success_rate_value,
                self._format_session_success_rate(completed, failed),
            ),
            (self.session_remaining_value, str(remaining)),
            (self.session_speed_value, self._format_session_speed_bps(avg_speed_bps)),
            (
                self.session_peak_speed_value,
                self._format_session_speed_bps(peak_speed_bps),
            ),
            (
                self.session_downloaded_value,
                helpers.humanize_bytes(self._session_downloaded_bytes) or "0 B",
            ),
            (self.session_elapsed_value, elapsed_text),
        )
        for label, value in label_values:
            label.setText(value)
            label.updateGeometry()
        self.run_stats_grid.updateGeometry()

    def _reset_session_metrics(
        self: "QtYtDlpGui",
        *,
        total_items: int,
        started_ts: float | None = None,
    ) -> None:
        self._session_started_ts = float(started_ts) if started_ts is not None else None
        self._session_total_items = max(0, int(total_items))
        self._session_completed_items = 0
        self._session_failed_items = 0
        self._session_downloaded_bytes = 0
        self._session_speed_sample_total_bps = 0.0
        self._session_speed_sample_count = 0
        self._session_peak_speed_bps = 0.0
        self._session_progress_item_key = ""
        self._session_current_item_downloaded_bytes = 0
        self._refresh_session_metrics(now_ts=started_ts)

    def _set_session_counts(
        self: "QtYtDlpGui", *, completed: int, failed: int
    ) -> None:
        self._session_completed_items = max(0, int(completed))
        self._session_failed_items = max(0, int(failed))
        self._refresh_session_metrics()

    def _record_session_speed_sample(
        self: "QtYtDlpGui", speed_bps: float
    ) -> None:
        if speed_bps <= 0:
            return
        self._session_speed_sample_total_bps += float(speed_bps)
        self._session_speed_sample_count += 1
        self._session_peak_speed_bps = max(
            float(self._session_peak_speed_bps),
            float(speed_bps),
        )

    def _record_session_downloaded_bytes(
        self: "QtYtDlpGui", downloaded_bytes: int
    ) -> None:
        if downloaded_bytes <= 0:
            return
        self._session_current_item_downloaded_bytes = max(
            int(self._session_current_item_downloaded_bytes),
            int(downloaded_bytes),
        )

    def _finalize_session_downloaded_bytes(self: "QtYtDlpGui") -> None:
        if self._session_current_item_downloaded_bytes > 0:
            self._session_downloaded_bytes += int(
                self._session_current_item_downloaded_bytes
            )
        self._session_current_item_downloaded_bytes = 0

    def _set_metric_label_text(self: "QtYtDlpGui", label, text: str) -> None:
        label.setText(text)
        label.updateGeometry()

    def _refresh_download_result_view(self: "QtYtDlpGui") -> None:
        show_latest_output = self._latest_output_path is not None
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
        self.download_result_card.setVisible(True)

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
        self._source_summary_data = queue_presentation.normalize_source_summary(summary)
        self._refresh_queue_preview_card()

    def _set_preview_title(self: "QtYtDlpGui", title: str) -> None:
        self._preview_title_raw = str(title or "").strip()
        self._refresh_queue_preview_card()

    def _refresh_queue_preview_card(self: "QtYtDlpGui") -> None:
        workspace_index_before = self.queue_workspace_stack.currentIndex()
        title_visibility_before = self.preview_value.isVisible()
        detail_widgets = (
            self.source_preview_detail_one,
            self.source_preview_detail_two,
            self.source_preview_detail_three,
        )
        detail_visibility_before = tuple(widget.isVisible() for widget in detail_widgets)
        model = queue_presentation.build_queue_preview_model(
            queue_presentation.QueuePreviewInputs(
                url=self.url_edit.text(),
                preview_title=self._preview_title_raw,
                source_summary=self._source_summary_data,
                playlist_mode=self._playlist_mode,
                mode=self._current_mode(),
                container=self._current_container(),
                is_fetching=self._is_fetching,
                has_filtered_formats=bool(self._filtered_labels),
                selected_quality=self._ready_summary_quality(
                    self._selected_format_label()
                ),
                folder_text=self._ready_summary_folder(),
                queue_count=len(self.queue_items),
                playlist_items=self.playlist_items_edit.text(),
            )
        )
        shown, tooltip = preview_title_fields(self._preview_title_raw)
        has_title = bool(self._preview_title_raw)
        self.preview_value.setText(shown)
        self.preview_value.setToolTip(tooltip)
        self.preview_value.setVisible(has_title)
        self.source_preview_placeholder.setVisible(not has_title)
        self.source_preview_placeholder.setText(model.placeholder_text)
        self.source_preview_badge.setText(model.badge_text)
        self.preview_title_label.setText(model.heading_text)
        self.source_preview_subtitle.setText(model.subtitle_text)
        self._set_widget_property(
            self.preview_value,
            "state",
            "ready" if has_title else "empty",
        )

        detail_texts = [
            model.detail_one_text,
            model.detail_two_text,
            model.detail_three_text,
        ]
        for widget, text in zip(
            detail_widgets,
            detail_texts,
        ):
            widget.setText(text)
            widget.setVisible(bool(text))

        self.source_preview_card.hide()
        self._sync_queue_workspace_view()
        detail_visibility_after = tuple(widget.isVisible() for widget in detail_widgets)
        needs_geometry_refresh = any(
            (
                workspace_index_before != self.queue_workspace_stack.currentIndex(),
                title_visibility_before != has_title,
                detail_visibility_before != detail_visibility_after,
            )
        )
        self._stabilize_source_preview_card_sizing()
        if needs_geometry_refresh:
            self._refresh_downloads_page_geometry()
            return
        QTimer.singleShot(0, self._stabilize_source_preview_card_sizing)
        self.source_preview_card.update()

    def _record_download_output(
        self: "QtYtDlpGui",
        output_path: Path,
        source_url: str = "",
        metadata: dict[str, object] | None = None,
    ) -> None:
        details = dict(metadata or {})
        recorded = app_service.record_history_output(
            history=self.download_history,
            seen_paths=self._history_seen_paths,
            output_path=output_path,
            source_url=source_url,
            max_entries=HISTORY_MAX_ENTRIES,
            title=str(details.get("title") or ""),
            format_label=str(details.get("format_label") or ""),
            queue_settings=details.get("queue_settings")
            if isinstance(details.get("queue_settings"), dict)
            else None,
        )
        if not recorded:
            return
        self._set_last_output_path(output_path)
        self._refresh_history_panel()
        self._refresh_queue_empty_state()

    def _refresh_history_panel(self: "QtYtDlpGui") -> None:
        self.history_list.clear()
        self.history_summary_list.clear()
        for item in self.download_history:
            timestamp = item.get("timestamp", "")
            name = item.get("name", "")
            self.history_list.addItem(f"{timestamp}  {name}")
            path_text = str(item.get("path", "")).strip()
            folder_name = Path(path_text).expanduser().parent.name if path_text else ""
            meta_parts = [timestamp, folder_name]
            self._append_workspace_summary_item(
                self.history_summary_list,
                badge_text="FILE",
                title=name or "Downloaded item",
                meta=" · ".join(part for part in meta_parts if part),
                status_text="Saved",
                tone="default",
                tooltip=path_text or name,
            )
        self._refresh_history_panel_state()
        has_items = self.history_summary_list.count() > 0
        self.history_summary_list.setVisible(has_items)
        self.history_summary_empty.setVisible(not has_items)

    def _history_relative_date_text(self: "QtYtDlpGui", timestamp_text: str) -> str:
        clean = str(timestamp_text or "").strip()
        if not clean:
            return ""
        try:
            then = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return clean
        delta = self._effects.clock.now() - then
        total_seconds = max(0, int(delta.total_seconds()))
        total_days = delta.days
        if total_days >= 2:
            return f"{total_days} days ago"
        if total_days == 1:
            return "yesterday"
        if total_seconds >= 3600:
            hours = max(1, total_seconds // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        if total_seconds >= 60:
            minutes = max(1, total_seconds // 60)
            return f"{minutes} min ago"
        return "just now"

    def _history_format_summary(self: "QtYtDlpGui", item: HistoryItem) -> str:
        settings = item.get("queue_settings")
        settings_dict = dict(settings) if isinstance(settings, dict) else {}
        mode = str(settings_dict.get("mode") or "").strip().lower()
        container = str(settings_dict.get("format_filter") or "").strip().upper()
        format_label = str(item.get("format_label") or "").strip()
        parts: list[str] = []
        if container and container not in {"BEST", "BESTVIDEO*+BESTAUDIO/BEST"}:
            parts.append(container)
        if format_label and format_label not in {"-", container}:
            parts.append(format_label)
        if mode == "audio" and not format_label:
            parts.append("Audio only")
        return " · ".join(part for part in parts if part)

    def _queue_empty_recent_items(self: "QtYtDlpGui") -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for history_index, item in enumerate(self.download_history[:3]):
            path_raw = str(item.get("path", "")).strip()
            size_bytes = int(item.get("file_size_bytes", 0) or 0)
            if size_bytes <= 0 and path_raw:
                try:
                    size_bytes = max(0, int(Path(path_raw).expanduser().stat().st_size))
                except (OSError, RuntimeError, ValueError):
                    size_bytes = 0
            meta_parts = []
            format_summary = self._history_format_summary(item)
            if format_summary:
                meta_parts.append(format_summary)
            if size_bytes > 0:
                meta_parts.append(helpers.humanize_bytes(size_bytes))
            relative_date = self._history_relative_date_text(str(item.get("timestamp", "")))
            if relative_date:
                meta_parts.append(relative_date)
            settings = item.get("queue_settings")
            settings_dict = dict(settings) if isinstance(settings, dict) else {}
            items.append(
                {
                    "history_index": history_index,
                    "badge_text": "AUD"
                    if str(settings_dict.get("mode") or "").strip().lower() == "audio"
                    else "VID",
                    "title": str(item.get("title") or item.get("name") or "Downloaded item"),
                    "meta": " · ".join(part for part in meta_parts if part),
                    "can_requeue": bool(
                        str(item.get("source_url") or "").strip() and settings_dict
                    ),
                }
            )
        return items

    def _refresh_queue_empty_state(self: "QtYtDlpGui") -> None:
        items = self._queue_empty_recent_items()
        for attr_name in ("queue_empty_state", "queue_summary_empty"):
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            widget.set_recent_items(items)

    def _requeue_history_item(self: "QtYtDlpGui", history_index: int) -> None:
        row = int(history_index)
        if row < 0 or row >= len(self.download_history):
            return
        if self._run_queue_controller.on_requeue_history_item(self.download_history[row]):
            self._active_workspace_name = "queue"
            return
        self._set_status("Could not re-queue recent download")

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
        self._refresh_queue_empty_state()
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
            speed_bps = payload.get("speed_bps")
            eta = payload.get("eta")
            playlist_eta = str(payload.get("playlist_eta") or "").strip()
            downloaded_bytes = payload.get("downloaded_bytes")
            if isinstance(percent, (int, float)):
                self._animate_progress_bar_to(float(percent))
                self._set_metric_label_text(
                    self.progress_label, f"Progress: {float(percent):.1f}%"
                )
            if isinstance(speed, str):
                self._set_metric_label_text(self.speed_label, f"Speed: {speed or '-'}")
            if isinstance(speed_bps, (int, float)) and float(speed_bps) > 0:
                self._record_session_speed_sample(float(speed_bps))
            if isinstance(downloaded_bytes, (int, float)) and int(downloaded_bytes) > 0:
                self._record_session_downloaded_bytes(int(downloaded_bytes))
            eta_text = str(eta).strip() if isinstance(eta, str) else ""
            if playlist_eta:
                self._set_metric_label_text(
                    self.eta_label, f"ETA: {eta_text or '-'} / {playlist_eta}"
                )
            elif eta_text:
                self._set_metric_label_text(self.eta_label, f"ETA: {eta_text}")
            else:
                self._set_metric_label_text(self.eta_label, "ETA: -")
            self._refresh_session_metrics()
        elif status == "item":
            if not self._show_progress_item:
                return
            item = str(payload.get("item") or "").strip()
            if item:
                if item != self._session_progress_item_key:
                    self._session_progress_item_key = item
                    self._session_current_item_downloaded_bytes = 0
                self._set_current_item_from_text(item)
        elif status == "finished":
            self._finalize_session_downloaded_bytes()
            self._set_metric_label_text(self.eta_label, "ETA: Finalizing")
            self._refresh_session_metrics()
        elif status == "cancelled":
            self._session_current_item_downloaded_bytes = 0
            self._reset_progress_summary()
            self._refresh_session_metrics()
        if self.queue_active:
            self._refresh_queue_panel()
