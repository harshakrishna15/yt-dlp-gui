from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from ..common import diagnostics, settings_store
from . import panels as qt_panels
from .constants import LOG_MAX_LINES

if TYPE_CHECKING:
    from .app import QtYtDlpGui


class WindowSettingsMixin:
    def _build_settings_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_settings_panel(
            parent=self,
            register_native_combo=self._register_native_combo,
            on_update_controls_state=self._update_controls_state,
            on_export_diagnostics=self._export_diagnostics,
            on_show_about=self._show_about_dialog,
        )
        self.subtitle_languages_edit = refs.subtitle_languages_edit
        self.write_subtitles_check = refs.write_subtitles_check
        self.embed_subtitles_check = refs.embed_subtitles_check
        self.audio_language_combo = refs.audio_language_combo
        self.network_timeout_edit = refs.network_timeout_edit
        self.network_retries_edit = refs.network_retries_edit
        self.retry_backoff_edit = refs.retry_backoff_edit
        self.concurrent_fragments_edit = refs.concurrent_fragments_edit
        self.edit_friendly_encoder_combo = refs.edit_friendly_encoder_combo
        self.open_folder_after_download_check = refs.open_folder_after_download_check
        self.export_diagnostics_button = refs.export_diagnostics_button
        self.about_button = refs.about_button
        return refs.panel

    def _build_queue_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_queue_panel(
            parent=self,
            on_remove_selected=self._queue_remove_selected,
            on_move_up=self._queue_move_up,
            on_move_down=self._queue_move_down,
            on_clear=self._queue_clear,
        )
        self.queue_stack = refs.queue_stack
        self._queue_empty_index = refs.queue_empty_index
        self._queue_content_index = refs.queue_content_index
        self.queue_list = refs.queue_list
        self.queue_remove_button = refs.queue_remove_button
        self.queue_move_up_button = refs.queue_move_up_button
        self.queue_move_down_button = refs.queue_move_down_button
        self.queue_clear_button = refs.queue_clear_button
        self.queue_list.itemSelectionChanged.connect(self._refresh_queue_panel_state)
        self._set_uniform_button_width(
            [
                self.queue_remove_button,
                self.queue_move_up_button,
                self.queue_move_down_button,
                self.queue_clear_button,
            ],
            extra_px=24,
        )
        return refs.panel

    def _build_history_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_history_panel(
            parent=self,
            on_open_file=self._open_selected_history_file,
            on_open_folder=self._open_selected_history_folder,
            on_clear=self._clear_download_history,
        )
        self.history_stack = refs.history_stack
        self._history_empty_index = refs.history_empty_index
        self._history_content_index = refs.history_content_index
        self.history_list = refs.history_list
        self.history_open_file_button = refs.history_open_file_button
        self.history_open_folder_button = refs.history_open_folder_button
        self.history_clear_button = refs.history_clear_button
        self.history_list.itemSelectionChanged.connect(
            self._refresh_history_panel_state
        )
        self._set_uniform_button_width(
            [
                self.history_open_file_button,
                self.history_open_folder_button,
                self.history_clear_button,
            ],
            extra_px=24,
        )
        return refs.panel

    def _build_logs_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_logs_panel(
            parent=self,
            max_lines=LOG_MAX_LINES,
            on_clear_logs=self._clear_logs,
        )
        self.logs_stack = refs.logs_stack
        self._logs_empty_index = refs.logs_empty_index
        self._logs_content_index = refs.logs_content_index
        self.logs_view = refs.logs_view
        self.logs_clear_button = refs.logs_clear_button
        return refs.panel

    def _default_output_dir(self: "QtYtDlpGui") -> str:
        return str(Path.home() / "Downloads")

    def _set_output_dir_text(self: "QtYtDlpGui", value: str) -> None:
        self.output_dir_edit.setText(str(value or self._default_output_dir()))
        self.output_dir_edit.setCursorPosition(0)

    def _load_user_settings(self: "QtYtDlpGui") -> None:
        settings = settings_store.load_settings(
            default_output_dir=self._default_output_dir()
        )
        self._applying_user_settings = True
        try:
            self._set_output_dir_text(self._default_output_dir())
            self.subtitle_languages_edit.setText(
                str(settings.get("subtitle_languages") or "")
            )
            self.write_subtitles_check.setChecked(
                bool(settings.get("write_subtitles"))
            )
            self.network_timeout_edit.setText(str(settings.get("network_timeout") or ""))
            self.network_retries_edit.setText(str(settings.get("network_retries") or ""))
            self.retry_backoff_edit.setText(str(settings.get("retry_backoff") or ""))
            self.concurrent_fragments_edit.setText(
                str(settings.get("concurrent_fragments") or "")
            )
            edit_friendly_encoder = str(
                settings.get("edit_friendly_encoder") or "auto"
            ).strip()
            idx = self.edit_friendly_encoder_combo.findData(edit_friendly_encoder)
            if idx < 0:
                idx = self.edit_friendly_encoder_combo.findData("auto")
            if idx < 0:
                idx = 0
            self.edit_friendly_encoder_combo.setCurrentIndex(idx)
            self.open_folder_after_download_check.setChecked(
                bool(settings.get("open_folder_after_download"))
            )
        finally:
            self._applying_user_settings = False

    def _capture_user_settings(self: "QtYtDlpGui") -> dict[str, object]:
        return {
            "subtitle_languages": self.subtitle_languages_edit.text().strip(),
            "write_subtitles": bool(self.write_subtitles_check.isChecked()),
            "network_timeout": self.network_timeout_edit.text().strip(),
            "network_retries": self.network_retries_edit.text().strip(),
            "retry_backoff": self.retry_backoff_edit.text().strip(),
            "concurrent_fragments": self.concurrent_fragments_edit.text().strip(),
            "edit_friendly_encoder": str(
                self.edit_friendly_encoder_combo.currentData() or "auto"
            ).strip(),
            "open_folder_after_download": bool(
                self.open_folder_after_download_check.isChecked()
            ),
        }

    def _save_user_settings(self: "QtYtDlpGui") -> None:
        if self._applying_user_settings:
            return
        settings_store.save_settings(
            self._capture_user_settings(),
            default_output_dir=self._default_output_dir(),
        )

    def _connect_settings_autosave(self: "QtYtDlpGui") -> None:
        self.subtitle_languages_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.write_subtitles_check.stateChanged.connect(
            lambda _state: self._save_user_settings()
        )
        self.network_timeout_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.network_retries_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.retry_backoff_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.concurrent_fragments_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.edit_friendly_encoder_combo.currentIndexChanged.connect(
            lambda _idx: self._save_user_settings()
        )
        self.open_folder_after_download_check.stateChanged.connect(
            lambda _state: self._save_user_settings()
        )

    def _maybe_open_output_folder(self: "QtYtDlpGui") -> None:
        if not self.open_folder_after_download_check.isChecked():
            return
        output_dir = Path(
            self.output_dir_edit.text().strip() or self._default_output_dir()
        ).expanduser()
        if not output_dir.exists():
            return
        self._effects.desktop.open_path(output_dir)

    def _export_diagnostics(self: "QtYtDlpGui") -> None:
        timestamp = self._effects.clock.now()
        base_dir = Path(
            self.output_dir_edit.text().strip() or (Path.home() / "Downloads")
        ).expanduser()
        try:
            self._effects.filesystem.ensure_dir(base_dir)
        except OSError:
            base_dir = Path.home() / "Downloads"
            self._effects.filesystem.ensure_dir(base_dir)

        output_path = base_dir / f"yt-dlp-gui-diagnostics-{timestamp:%Y%m%d-%H%M%S}.txt"
        options = self._snapshot_download_options()
        payload = diagnostics.build_report_payload(
            generated_at=timestamp,
            status=self.status_value.text(),
            simple_state=self.status_value.text(),
            url=self.url_edit.text(),
            mode=self._current_mode(),
            container=self._current_container(),
            codec=self._current_codec(),
            format_label=self._selected_format_label(),
            queue_items=self.queue_items,
            queue_active=self.queue_active,
            is_downloading=self._is_downloading,
            preview_title=self.preview_value.text(),
            options=options,
            history_items=self.download_history,
            logs_text="\n".join(self._log_lines),
        )
        try:
            self._effects.filesystem.write_text(output_path, payload, encoding="utf-8")
        except OSError as exc:
            self._effects.dialogs.critical(
                self, "Diagnostics export failed", str(exc)
            )
            return
        self._append_log(f"[diag] exported {output_path}")
        self._set_status("Diagnostics exported")
        self._effects.dialogs.information(
            self, "Diagnostics exported", f"Saved to:\n{output_path}"
        )
