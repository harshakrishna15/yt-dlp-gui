from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtWidgets import QWidget

from ..common import diagnostics, settings_store, tooling
from . import panels as qt_panels
from .constants import LOG_MAX_LINES

if TYPE_CHECKING:
    from .app import QtYtDlpGui


_EDIT_FRIENDLY_ENCODER_CODECS = {
    "apple": "h264_videotoolbox",
    "nvidia": "h264_nvenc",
    "amd": "h264_amf",
    "intel": "h264_qsv",
    "cpu": "libx264",
}
_EDIT_FRIENDLY_ENCODER_DISABLED_TOOLTIP = (
    "Unavailable from the installed ffmpeg on this computer."
)


@dataclass(frozen=True)
class _SettingBinding:
    key: str
    apply: Callable[[object], None]
    capture: Callable[[], object]
    connect: Callable[[Callable[[], None]], None]


class WindowSettingsMixin:
    def _display_output_dir(self: "QtYtDlpGui", value: str) -> str:
        raw = str(value or self._default_output_dir()).strip() or self._default_output_dir()
        try:
            path = Path(raw).expanduser()
        except (TypeError, ValueError, OSError):
            return raw
        return str(path)

    def _build_settings_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_settings_panel(
            parent=self,
            register_native_combo=self._register_native_combo,
            on_export_diagnostics=self._export_diagnostics,
        )
        self.edit_friendly_encoder_combo = refs.edit_friendly_encoder_combo
        self.open_folder_after_download_check = refs.open_folder_after_download_check
        self.export_diagnostics_button = refs.export_diagnostics_button
        self._refresh_edit_friendly_encoder_availability()
        return refs.panel

    def _build_queue_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_queue_panel(
            parent=self,
            on_clear_queue=self._run_queue_controller.on_queue_clear,
        )
        self.queue_stack = refs.queue_stack
        self._queue_empty_index = refs.queue_empty_index
        self._queue_content_index = refs.queue_content_index
        self.queue_empty_state = refs.queue_empty_state
        self.queue_list = refs.queue_list
        self.queue_clear_button = refs.clear_queue_button
        self.queue_list.itemSelectionChanged.connect(self._refresh_queue_panel_state)
        self.queue_list.edit_requested.connect(self._queue_edit_row)
        self.queue_list.remove_requested.connect(self._queue_remove_row)
        self.queue_list.items_reordered.connect(self._queue_reorder_items)
        return refs.panel

    def _build_logs_panel(self: "QtYtDlpGui") -> QWidget:
        refs = qt_panels.build_logs_panel(
            parent=self,
            max_lines=LOG_MAX_LINES,
            on_export_logs=self._export_logs,
            on_clear_logs=self._clear_logs,
        )
        self.logs_stack = refs.logs_stack
        self._logs_empty_index = refs.logs_empty_index
        self._logs_content_index = refs.logs_content_index
        self.logs_view = refs.logs_view
        self.logs_export_button = refs.export_logs_button
        self.logs_clear_button = refs.logs_clear_button
        return refs.panel

    def _default_output_dir(self: "QtYtDlpGui") -> str:
        return str(Path.home() / "Downloads")

    def _set_output_dir_text(self: "QtYtDlpGui", value: str) -> None:
        raw = str(value or self._default_output_dir()).strip() or self._default_output_dir()
        display = self._display_output_dir(raw)
        self.output_dir_edit.setText(display)
        self.output_dir_edit.setToolTip(str(Path(raw).expanduser()))
        self.output_dir_edit.setCursorPosition(0)
        self._refresh_queue_preview_card()

    def _set_edit_friendly_encoder_preference(
        self: "QtYtDlpGui", value: object
    ) -> None:
        preference = str(value or "auto").strip() or "auto"
        index = self.edit_friendly_encoder_combo.findData(preference)
        if index < 0:
            index = self.edit_friendly_encoder_combo.findData("auto")
        if index < 0:
            index = 0
        self.edit_friendly_encoder_combo.setCurrentIndex(index)

    def _settings_bindings(self: "QtYtDlpGui") -> tuple[_SettingBinding, ...]:
        return (
            _SettingBinding(
                key="output_dir",
                apply=lambda value: self._set_output_dir_text(
                    str(value or self._default_output_dir())
                ),
                capture=lambda: self.output_dir_edit.text().strip(),
                connect=lambda callback: self.output_dir_edit.textChanged.connect(
                    lambda _text: callback()
                ),
            ),
            _SettingBinding(
                key="edit_friendly_encoder",
                apply=self._set_edit_friendly_encoder_preference,
                capture=lambda: str(
                    self.edit_friendly_encoder_combo.currentData() or "auto"
                ).strip(),
                connect=lambda callback: self.edit_friendly_encoder_combo.currentIndexChanged.connect(
                    lambda _idx: callback()
                ),
            ),
            _SettingBinding(
                key="open_folder_after_download",
                apply=lambda value: self.open_folder_after_download_check.setChecked(
                    bool(value)
                ),
                capture=lambda: bool(
                    self.open_folder_after_download_check.isChecked()
                ),
                connect=lambda callback: self.open_folder_after_download_check.stateChanged.connect(
                    lambda _state: callback()
                ),
            ),
        )

    def _load_user_settings(self: "QtYtDlpGui") -> None:
        settings = settings_store.load_settings(
            default_output_dir=self._default_output_dir()
        )
        self._applying_user_settings = True
        try:
            for binding in self._settings_bindings():
                binding.apply(settings.get(binding.key))
        finally:
            self._applying_user_settings = False

    def _capture_user_settings(self: "QtYtDlpGui") -> dict[str, object]:
        return {
            binding.key: binding.capture()
            for binding in self._settings_bindings()
        }

    def _save_user_settings(self: "QtYtDlpGui") -> None:
        if self._applying_user_settings:
            return
        settings_store.save_settings(
            self._capture_user_settings(),
            default_output_dir=self._default_output_dir(),
        )

    def _connect_settings_autosave(self: "QtYtDlpGui") -> None:
        for binding in self._settings_bindings():
            binding.connect(self._save_user_settings)

    def _refresh_edit_friendly_encoder_availability(self: "QtYtDlpGui") -> None:
        ffmpeg_path, _ffmpeg_source = tooling.resolve_binary("ffmpeg")
        available_codecs: set[str] = set()
        if ffmpeg_path is not None:
            available_codecs = tooling.available_ffmpeg_encoders(
                ffmpeg_path,
                candidates=_EDIT_FRIENDLY_ENCODER_CODECS.values(),
            )
        for preference, codec in _EDIT_FRIENDLY_ENCODER_CODECS.items():
            self.edit_friendly_encoder_combo.set_item_enabled(
                preference,
                codec in available_codecs,
                disabled_tooltip=_EDIT_FRIENDLY_ENCODER_DISABLED_TOOLTIP,
            )

    def _maybe_open_output_folder(self: "QtYtDlpGui") -> None:
        if not self.open_folder_after_download_check.isChecked():
            return
        if self._post_download_output_dir is not None:
            output_dir = self._post_download_output_dir
        else:
            output_dir = Path(
                self.output_dir_edit.text().strip() or self._default_output_dir()
            ).expanduser()
        if not output_dir.exists():
            return
        self._effects.desktop.open_path(output_dir)

    def _prepare_export_path(
        self: "QtYtDlpGui",
        *,
        failure_title: str,
        filename_prefix: str,
    ) -> tuple[object, Path] | None:
        timestamp = self._effects.clock.now()
        try:
            base_dir = settings_store.prepare_output_dir_path(
                self.output_dir_edit.text(),
                ensure_dir=self._effects.filesystem.ensure_dir,
                default_output_dir=self._default_output_dir(),
            )
        except OSError as exc:
            self._effects.dialogs.critical(
                self,
                failure_title,
                str(exc),
            )
            return None
        return (
            timestamp,
            base_dir / f"{filename_prefix}-{timestamp:%Y%m%d-%H%M%S}.txt",
        )

    def _complete_export(
        self: "QtYtDlpGui",
        *,
        output_path: Path,
        payload: str,
        failure_title: str,
        success_status: str,
        success_log_prefix: str,
        success_dialog_title: str,
    ) -> None:
        try:
            self._effects.filesystem.write_text(output_path, payload, encoding="utf-8")
        except OSError as exc:
            self._effects.dialogs.critical(self, failure_title, str(exc))
            return
        self._append_log(f"[{success_log_prefix}] exported {output_path}")
        self._set_status(success_status)
        self._effects.dialogs.information(
            self, success_dialog_title, f"Saved to:\n{output_path}"
        )

    def _export_logs(self: "QtYtDlpGui") -> None:
        if not self._log_lines:
            return
        export = self._prepare_export_path(
            failure_title="Logs export failed",
            filename_prefix="yt-dlp-gui-logs",
        )
        if export is None:
            return
        _timestamp, output_path = export
        payload = "\n".join(self._log_lines).rstrip("\n")
        if payload:
            payload += "\n"
        self._complete_export(
            output_path=output_path,
            payload=payload,
            failure_title="Logs export failed",
            success_status="Logs exported",
            success_log_prefix="logs",
            success_dialog_title="Logs exported",
        )

    def _export_diagnostics(self: "QtYtDlpGui") -> None:
        export = self._prepare_export_path(
            failure_title="Diagnostics export failed",
            filename_prefix="yt-dlp-gui-diagnostics",
        )
        if export is None:
            return
        timestamp, output_path = export
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
            preview_title=self._preview_title_raw,
            options=options,
            logs_text="\n".join(self._log_lines),
        )
        self._complete_export(
            output_path=output_path,
            payload=payload,
            failure_title="Diagnostics export failed",
            success_status="Diagnostics exported",
            success_log_prefix="diag",
            success_dialog_title="Diagnostics exported",
        )
