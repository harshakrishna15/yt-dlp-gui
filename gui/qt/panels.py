from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


@dataclass(frozen=True)
class SettingsPanelRefs:
    panel: QWidget
    subtitle_languages_edit: QLineEdit
    write_subtitles_check: QCheckBox
    embed_subtitles_check: QCheckBox
    audio_language_combo: _NativeComboBox
    network_timeout_edit: QLineEdit
    network_retries_edit: QLineEdit
    retry_backoff_edit: QLineEdit
    concurrent_fragments_edit: QLineEdit
    edit_friendly_encoder_combo: _NativeComboBox
    open_folder_after_download_check: QCheckBox
    export_diagnostics_button: QPushButton


@dataclass(frozen=True)
class QueuePanelRefs:
    panel: QWidget
    queue_list: QListWidget
    queue_remove_button: QPushButton
    queue_move_up_button: QPushButton
    queue_move_down_button: QPushButton
    queue_clear_button: QPushButton


@dataclass(frozen=True)
class HistoryPanelRefs:
    panel: QWidget
    history_list: QListWidget
    history_open_file_button: QPushButton
    history_open_folder_button: QPushButton
    history_clear_button: QPushButton


@dataclass(frozen=True)
class LogsPanelRefs:
    panel: QWidget
    logs_view: QPlainTextEdit
    logs_clear_button: QPushButton


def build_settings_panel(
    *,
    parent: QWidget,
    register_native_combo: Callable[[_NativeComboBox], None],
    on_update_controls_state: Callable[[], None],
    on_export_diagnostics: Callable[[], None],
) -> SettingsPanelRefs:
    panel = QWidget(parent)
    layout = QFormLayout(panel)
    layout.setHorizontalSpacing(16)
    layout.setVerticalSpacing(10)

    subtitle_languages_edit = QLineEdit(panel)
    subtitle_languages_edit.setPlaceholderText("en,es")
    subtitle_languages_edit.hide()

    subtitle_opts = QWidget(panel)
    subtitle_opts_layout = QHBoxLayout(subtitle_opts)
    subtitle_opts_layout.setContentsMargins(0, 0, 0, 0)
    write_subtitles_check = QCheckBox("Write subtitles", subtitle_opts)
    embed_subtitles_check = QCheckBox("Embed subtitles", subtitle_opts)
    write_subtitles_check.stateChanged.connect(
        lambda _v: on_update_controls_state()
    )
    embed_subtitles_check.stateChanged.connect(
        lambda _v: on_update_controls_state()
    )
    subtitle_opts_layout.addWidget(write_subtitles_check)
    subtitle_opts_layout.addWidget(embed_subtitles_check)
    subtitle_opts_layout.addStretch(1)
    subtitle_opts.hide()

    audio_language_combo = _NativeComboBox(panel)
    register_native_combo(audio_language_combo)
    audio_language_combo.addItem("Any")
    audio_language_combo.hide()

    network_row = QWidget(panel)
    network_layout = QHBoxLayout(network_row)
    network_layout.setContentsMargins(0, 0, 0, 0)
    network_timeout_edit = QLineEdit(
        str(download.YDL_SOCKET_TIMEOUT_SECONDS), network_row
    )
    network_timeout_edit.setMaximumWidth(100)
    network_retries_edit = QLineEdit(
        str(download.YDL_ATTEMPT_RETRIES), network_row
    )
    network_retries_edit.setMaximumWidth(100)
    retry_backoff_edit = QLineEdit(
        str(download.YDL_RETRY_BACKOFF_SECONDS), network_row
    )
    retry_backoff_edit.setMaximumWidth(100)
    concurrent_fragments_edit = QLineEdit(
        str(download.YDL_MAX_CONCURRENT_FRAGMENTS), network_row
    )
    concurrent_fragments_edit.setMaximumWidth(100)
    network_layout.addWidget(QLabel("Timeout", network_row))
    network_layout.addWidget(network_timeout_edit)
    network_layout.addWidget(QLabel("Retries", network_row))
    network_layout.addWidget(network_retries_edit)
    network_layout.addWidget(QLabel("Backoff", network_row))
    network_layout.addWidget(retry_backoff_edit)
    network_layout.addWidget(QLabel("Fragments", network_row))
    network_layout.addWidget(concurrent_fragments_edit)
    network_layout.addStretch(1)
    network_row.hide()

    edit_friendly_encoder_combo = _NativeComboBox(panel)
    register_native_combo(edit_friendly_encoder_combo)
    edit_friendly_encoder_combo.addItem("Auto (recommended)", "auto")
    edit_friendly_encoder_combo.addItem("Apple GPU (VideoToolbox)", "apple")
    edit_friendly_encoder_combo.addItem("NVIDIA GPU (NVENC)", "nvidia")
    edit_friendly_encoder_combo.addItem("AMD GPU (AMF)", "amd")
    edit_friendly_encoder_combo.addItem("Intel GPU (QSV)", "intel")
    edit_friendly_encoder_combo.addItem("CPU (libx264)", "cpu")
    layout.addRow("Edit-friendly encode", edit_friendly_encoder_combo)

    open_folder_after_download_check = QCheckBox(
        "Open output folder after downloads", panel
    )
    layout.addRow("Post-download", open_folder_after_download_check)

    export_diagnostics_button = QPushButton("Export diagnostics", panel)
    export_diagnostics_button.clicked.connect(on_export_diagnostics)
    layout.addRow("", export_diagnostics_button)
    return SettingsPanelRefs(
        panel=panel,
        subtitle_languages_edit=subtitle_languages_edit,
        write_subtitles_check=write_subtitles_check,
        embed_subtitles_check=embed_subtitles_check,
        audio_language_combo=audio_language_combo,
        network_timeout_edit=network_timeout_edit,
        network_retries_edit=network_retries_edit,
        retry_backoff_edit=retry_backoff_edit,
        concurrent_fragments_edit=concurrent_fragments_edit,
        edit_friendly_encoder_combo=edit_friendly_encoder_combo,
        open_folder_after_download_check=open_folder_after_download_check,
        export_diagnostics_button=export_diagnostics_button,
    )


def build_queue_panel(
    *,
    parent: QWidget,
    on_remove_selected: Callable[[], None],
    on_move_up: Callable[[], None],
    on_move_down: Callable[[], None],
    on_clear: Callable[[], None],
) -> QueuePanelRefs:
    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    queue_list = QListWidget(panel)
    queue_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    layout.addWidget(queue_list)

    actions = QWidget(panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    queue_remove_button = QPushButton("Remove", actions)
    queue_move_up_button = QPushButton("Move up", actions)
    queue_move_down_button = QPushButton("Move down", actions)
    queue_clear_button = QPushButton("Clear", actions)
    queue_remove_button.clicked.connect(on_remove_selected)
    queue_move_up_button.clicked.connect(on_move_up)
    queue_move_down_button.clicked.connect(on_move_down)
    queue_clear_button.clicked.connect(on_clear)
    actions_layout.addWidget(queue_remove_button)
    actions_layout.addWidget(queue_move_up_button)
    actions_layout.addWidget(queue_move_down_button)
    actions_layout.addWidget(queue_clear_button)
    actions_layout.addStretch(1)
    layout.addWidget(actions)
    return QueuePanelRefs(
        panel=panel,
        queue_list=queue_list,
        queue_remove_button=queue_remove_button,
        queue_move_up_button=queue_move_up_button,
        queue_move_down_button=queue_move_down_button,
        queue_clear_button=queue_clear_button,
    )


def build_history_panel(
    *,
    parent: QWidget,
    on_open_file: Callable[[], None],
    on_open_folder: Callable[[], None],
    on_clear: Callable[[], None],
) -> HistoryPanelRefs:
    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    history_list = QListWidget(panel)
    history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    layout.addWidget(history_list)

    actions = QWidget(panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    history_open_file_button = QPushButton("Open file", actions)
    history_open_folder_button = QPushButton("Open folder", actions)
    history_clear_button = QPushButton("Clear", actions)
    history_open_file_button.clicked.connect(on_open_file)
    history_open_folder_button.clicked.connect(on_open_folder)
    history_clear_button.clicked.connect(on_clear)
    actions_layout.addWidget(history_open_file_button)
    actions_layout.addWidget(history_open_folder_button)
    actions_layout.addWidget(history_clear_button)
    actions_layout.addStretch(1)
    layout.addWidget(actions)
    return HistoryPanelRefs(
        panel=panel,
        history_list=history_list,
        history_open_file_button=history_open_file_button,
        history_open_folder_button=history_open_folder_button,
        history_clear_button=history_clear_button,
    )


def build_logs_panel(
    *,
    parent: QWidget,
    max_lines: int,
    on_clear_logs: Callable[[], None],
) -> LogsPanelRefs:
    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    logs_view = QPlainTextEdit(panel)
    logs_view.setReadOnly(True)
    logs_view.setMaximumBlockCount(max_lines)
    layout.addWidget(logs_view)

    logs_clear_button = QPushButton("Clear logs", panel)
    logs_clear_button.clicked.connect(on_clear_logs)
    layout.addWidget(logs_clear_button)
    return LogsPanelRefs(
        panel=panel,
        logs_view=logs_view,
        logs_clear_button=logs_clear_button,
    )
