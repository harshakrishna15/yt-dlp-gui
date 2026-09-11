from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtWidgets import QWidget

from ..common import diagnostics, settings_store, tooling, yt_dlp_binary, yt_dlp_release
from ..common.yt_dlp_helpers import humanize_bytes
from . import panels as qt_panels
from .constants import LOG_MAX_LINES
from .platform_paths import system_downloads_path

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
            on_update_yt_dlp=self._update_yt_dlp,
            on_export_diagnostics=self._export_diagnostics,
        )
        self.edit_friendly_encoder_combo = refs.edit_friendly_encoder_combo
        self.open_folder_after_download_check = refs.open_folder_after_download_check
        self.yt_dlp_version_label = refs.yt_dlp_version_label
        self.yt_dlp_update_button = refs.yt_dlp_update_button
        self.yt_dlp_update_status = refs.yt_dlp_update_status
        self.yt_dlp_update_progress_bar = refs.yt_dlp_update_progress_bar
        self.yt_dlp_update_status_label = refs.yt_dlp_update_status_label
        self.yt_dlp_update_detail_label = refs.yt_dlp_update_detail_label
        self.export_diagnostics_button = refs.export_diagnostics_button
        self._refresh_yt_dlp_version()
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
        return str(system_downloads_path())

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
        settings = settings_store.load_settings()
        self._applying_user_settings = True
        try:
            self._set_output_dir_text(self._default_output_dir())
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
        settings_store.save_settings(self._capture_user_settings())

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

    def _refresh_yt_dlp_version(
        self: "QtYtDlpGui", *, force: bool = False
    ) -> None:
        if self._yt_dlp_binary_source and not force:
            self._sync_yt_dlp_update_button()
            return
        resolved = yt_dlp_binary.resolve_yt_dlp_binary()
        if resolved is None:
            self._yt_dlp_binary_source = "missing"
            self.yt_dlp_version_label.setText("yt-dlp unavailable")
            self.yt_dlp_update_button.setEnabled(False)
            return
        self._yt_dlp_binary_source = resolved.source
        self.yt_dlp_version_label.setText(f"yt-dlp {resolved.version}")
        self._sync_yt_dlp_update_button()

    def _sync_yt_dlp_update_button(self: "QtYtDlpGui") -> None:
        self.yt_dlp_update_button.setEnabled(
            self._yt_dlp_binary_source == "managed"
            and not self._yt_dlp_update_in_progress
            and not self._is_downloading
            and not self._is_fetching
        )

    def _update_yt_dlp(self: "QtYtDlpGui") -> None:
        if (
            self._yt_dlp_update_in_progress
            or self._is_downloading
            or self._is_fetching
        ):
            return
        resolved = yt_dlp_binary.resolve_yt_dlp_binary()
        if resolved is None or resolved.source != "managed":
            self._effects.dialogs.critical(
                self,
                "yt-dlp update unavailable",
                "The managed yt-dlp executable is not available in this build.",
            )
            return
        self._yt_dlp_update_in_progress = True
        self.yt_dlp_update_button.setText("Updating...")
        self.yt_dlp_update_button.setEnabled(False)
        self._on_yt_dlp_update_progress(yt_dlp_release.YtDlpUpdateProgress("checking"))
        self._set_status("Updating yt-dlp...")
        self._update_controls_state()
        try:
            self._effects.worker_executor.submit(self._update_yt_dlp_worker)
        except Exception as exc:
            self._on_yt_dlp_update_done(yt_dlp_binary.YtDlpUpdateResult(
                success=False, changed=False, version=resolved.version,
                message=f"Could not start the yt-dlp update: {exc}",
            ))

    def _update_yt_dlp_worker(self: "QtYtDlpGui") -> None:
        try:
            result = yt_dlp_binary.update_managed_yt_dlp(
                on_progress=self._signals.yt_dlp_update_progress.emit,
            )
        except Exception as exc:
            result = yt_dlp_binary.YtDlpUpdateResult(
                success=False,
                changed=False,
                version="unknown",
                message=f"yt-dlp update failed: {exc}",
            )
        self._signals.yt_dlp_update_done.emit(result)

    def _on_yt_dlp_update_progress(self: "QtYtDlpGui", progress: object) -> None:
        if not self._yt_dlp_update_in_progress or not isinstance(
            progress, yt_dlp_release.YtDlpUpdateProgress
        ):
            return
        titles = {
            "checking": "Checking for yt-dlp updates...",
            "downloading": "Downloading yt-dlp...",
            "verifying": "Verifying checksum and executable...",
            "licenses": "Fetching release notices...",
            "installing": "Installing yt-dlp...",
        }
        self.yt_dlp_update_status.show()
        self.yt_dlp_update_status_label.setText(titles[progress.stage])
        bar = self.yt_dlp_update_progress_bar
        if progress.stage != "downloading":
            bar.setRange(0, 0)
            self.yt_dlp_update_detail_label.setText("Please keep the app open.")
            return
        details = []
        received = humanize_bytes(progress.downloaded_bytes) or "0 B"
        if progress.total_bytes:
            percent = min(100, int(progress.downloaded_bytes * 100 / progress.total_bytes))
            bar.setRange(0, 100)
            bar.setValue(percent)
            details.append(f"{percent}% downloaded")
            details.append(f"{received} of {humanize_bytes(progress.total_bytes)}")
        else:
            bar.setRange(0, 0)
            details.append(f"{received} downloaded")
        if progress.bytes_per_second is not None:
            details.append(f"{humanize_bytes(int(progress.bytes_per_second))}/s")
        if progress.eta_seconds is not None:
            seconds = max(1, ceil(progress.eta_seconds))
            estimate = f"{seconds}s" if seconds < 60 else f"{ceil(seconds / 60)} min"
            details.append(f"About {estimate} left in download")
        elif progress.downloaded_bytes == 0:
            details.append("Waiting for data...")
        self.yt_dlp_update_detail_label.setText(" | ".join(details))

    def _on_yt_dlp_update_done(
        self: "QtYtDlpGui", result: object
    ) -> None:
        self._yt_dlp_update_in_progress = False
        self.yt_dlp_update_button.setText("Update yt-dlp")
        if not isinstance(result, yt_dlp_binary.YtDlpUpdateResult):
            result = yt_dlp_binary.YtDlpUpdateResult(
                success=False,
                changed=False,
                version="unknown",
                message="yt-dlp update returned an invalid result.",
            )
        self._yt_dlp_binary_source = ""
        self._refresh_yt_dlp_version(force=True)
        self.yt_dlp_update_status.show()
        self.yt_dlp_update_progress_bar.setRange(0, 100)
        self.yt_dlp_update_progress_bar.setValue(100 if result.success else 0)
        self.yt_dlp_update_status_label.setText(
            "Update complete" if result.success and result.changed
            else "Already up to date" if result.success else "Update failed"
        )
        self.yt_dlp_update_detail_label.setText(
            f"yt-dlp {result.version} is ready." if result.success
            else "You can retry the update. See the error message for details."
        )
        self._append_log(f"[update] {result.message}")
        self._set_status("yt-dlp updated" if result.success else "yt-dlp update failed")
        self._update_controls_state()
        if result.success:
            self._effects.dialogs.information(
                self,
                "yt-dlp update",
                result.message,
            )
        else:
            self._effects.dialogs.critical(
                self,
                "yt-dlp update failed",
                result.message,
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
