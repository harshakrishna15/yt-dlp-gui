from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..common import download
from .widgets import _NativeComboBox

if TYPE_CHECKING:
    from .app import QtYtDlpGui


def build_settings_panel(window: "QtYtDlpGui") -> QWidget:
    panel = QWidget(window)
    layout = QFormLayout(panel)
    layout.setHorizontalSpacing(16)
    layout.setVerticalSpacing(10)

    window.subtitle_languages_edit = QLineEdit(panel)
    window.subtitle_languages_edit.setPlaceholderText("en,es")
    window.subtitle_languages_edit.hide()

    subtitle_opts = QWidget(panel)
    subtitle_opts_layout = QHBoxLayout(subtitle_opts)
    subtitle_opts_layout.setContentsMargins(0, 0, 0, 0)
    window.write_subtitles_check = QCheckBox("Write subtitles", subtitle_opts)
    window.embed_subtitles_check = QCheckBox("Embed subtitles", subtitle_opts)
    window.write_subtitles_check.stateChanged.connect(
        lambda _v: window._update_controls_state()
    )
    window.embed_subtitles_check.stateChanged.connect(
        lambda _v: window._update_controls_state()
    )
    subtitle_opts_layout.addWidget(window.write_subtitles_check)
    subtitle_opts_layout.addWidget(window.embed_subtitles_check)
    subtitle_opts_layout.addStretch(1)
    subtitle_opts.hide()

    window.audio_language_combo = _NativeComboBox(panel)
    window._register_native_combo(window.audio_language_combo)
    window.audio_language_combo.addItem("Any")
    window.audio_language_combo.hide()

    network_row = QWidget(panel)
    network_layout = QHBoxLayout(network_row)
    network_layout.setContentsMargins(0, 0, 0, 0)
    window.network_timeout_edit = QLineEdit(
        str(download.YDL_SOCKET_TIMEOUT_SECONDS), network_row
    )
    window.network_timeout_edit.setMaximumWidth(100)
    window.network_retries_edit = QLineEdit(
        str(download.YDL_ATTEMPT_RETRIES), network_row
    )
    window.network_retries_edit.setMaximumWidth(100)
    window.retry_backoff_edit = QLineEdit(
        str(download.YDL_RETRY_BACKOFF_SECONDS), network_row
    )
    window.retry_backoff_edit.setMaximumWidth(100)
    window.concurrent_fragments_edit = QLineEdit(
        str(download.YDL_MAX_CONCURRENT_FRAGMENTS), network_row
    )
    window.concurrent_fragments_edit.setMaximumWidth(100)
    network_layout.addWidget(QLabel("Timeout", network_row))
    network_layout.addWidget(window.network_timeout_edit)
    network_layout.addWidget(QLabel("Retries", network_row))
    network_layout.addWidget(window.network_retries_edit)
    network_layout.addWidget(QLabel("Backoff", network_row))
    network_layout.addWidget(window.retry_backoff_edit)
    network_layout.addWidget(QLabel("Fragments", network_row))
    network_layout.addWidget(window.concurrent_fragments_edit)
    network_layout.addStretch(1)
    network_row.hide()

    window.edit_friendly_encoder_combo = _NativeComboBox(panel)
    window._register_native_combo(window.edit_friendly_encoder_combo)
    window.edit_friendly_encoder_combo.addItem("Auto (recommended)", "auto")
    window.edit_friendly_encoder_combo.addItem("Apple GPU (VideoToolbox)", "apple")
    window.edit_friendly_encoder_combo.addItem("NVIDIA GPU (NVENC)", "nvidia")
    window.edit_friendly_encoder_combo.addItem("AMD GPU (AMF)", "amd")
    window.edit_friendly_encoder_combo.addItem("Intel GPU (QSV)", "intel")
    window.edit_friendly_encoder_combo.addItem("CPU (libx264)", "cpu")
    layout.addRow("Edit-friendly encode", window.edit_friendly_encoder_combo)

    window.open_folder_after_download_check = QCheckBox(
        "Open output folder after downloads", panel
    )
    layout.addRow("Post-download", window.open_folder_after_download_check)

    window.export_diagnostics_button = QPushButton("Export diagnostics", panel)
    window.export_diagnostics_button.clicked.connect(window._export_diagnostics)
    layout.addRow("", window.export_diagnostics_button)
    return panel


def build_queue_panel(window: "QtYtDlpGui") -> QWidget:
    panel = QWidget(window)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    window.queue_list = QListWidget(panel)
    window.queue_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    layout.addWidget(window.queue_list)

    actions = QWidget(panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    window.queue_remove_button = QPushButton("Remove", actions)
    window.queue_move_up_button = QPushButton("Move up", actions)
    window.queue_move_down_button = QPushButton("Move down", actions)
    window.queue_clear_button = QPushButton("Clear", actions)
    window.queue_remove_button.clicked.connect(window._queue_remove_selected)
    window.queue_move_up_button.clicked.connect(window._queue_move_up)
    window.queue_move_down_button.clicked.connect(window._queue_move_down)
    window.queue_clear_button.clicked.connect(window._queue_clear)
    actions_layout.addWidget(window.queue_remove_button)
    actions_layout.addWidget(window.queue_move_up_button)
    actions_layout.addWidget(window.queue_move_down_button)
    actions_layout.addWidget(window.queue_clear_button)
    actions_layout.addStretch(1)
    layout.addWidget(actions)
    window._set_uniform_button_width(
        [
            window.queue_remove_button,
            window.queue_move_up_button,
            window.queue_move_down_button,
            window.queue_clear_button,
        ],
        extra_px=24,
    )
    return panel


def build_history_panel(window: "QtYtDlpGui") -> QWidget:
    panel = QWidget(window)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    window.history_list = QListWidget(panel)
    window.history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    layout.addWidget(window.history_list)

    actions = QWidget(panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    window.history_open_file_button = QPushButton("Open file", actions)
    window.history_open_folder_button = QPushButton("Open folder", actions)
    window.history_clear_button = QPushButton("Clear", actions)
    window.history_open_file_button.clicked.connect(window._open_selected_history_file)
    window.history_open_folder_button.clicked.connect(window._open_selected_history_folder)
    window.history_clear_button.clicked.connect(window._clear_download_history)
    actions_layout.addWidget(window.history_open_file_button)
    actions_layout.addWidget(window.history_open_folder_button)
    actions_layout.addWidget(window.history_clear_button)
    actions_layout.addStretch(1)
    layout.addWidget(actions)
    window._set_uniform_button_width(
        [
            window.history_open_file_button,
            window.history_open_folder_button,
            window.history_clear_button,
        ],
        extra_px=24,
    )
    return panel


def build_logs_panel(window: "QtYtDlpGui", *, max_lines: int) -> QWidget:
    panel = QWidget(window)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    window.logs_view = QPlainTextEdit(panel)
    window.logs_view.setReadOnly(True)
    window.logs_view.setMaximumBlockCount(max_lines)
    layout.addWidget(window.logs_view)

    window.logs_clear_button = QPushButton("Clear logs", panel)
    window.logs_clear_button.clicked.connect(window._clear_logs)
    layout.addWidget(window.logs_clear_button)
    return panel
