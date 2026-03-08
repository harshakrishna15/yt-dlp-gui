from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..app_meta import APP_VERSION
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
    about_button: QPushButton


@dataclass(frozen=True)
class QueuePanelRefs:
    panel: QWidget
    queue_stack: QStackedWidget
    queue_empty_index: int
    queue_content_index: int
    queue_list: QListWidget
    queue_remove_button: QPushButton
    queue_move_up_button: QPushButton
    queue_move_down_button: QPushButton
    queue_clear_button: QPushButton


@dataclass(frozen=True)
class HistoryPanelRefs:
    panel: QWidget
    history_stack: QStackedWidget
    history_empty_index: int
    history_content_index: int
    history_list: QListWidget
    history_open_file_button: QPushButton
    history_open_folder_button: QPushButton
    history_clear_button: QPushButton


@dataclass(frozen=True)
class LogsPanelRefs:
    panel: QWidget
    logs_stack: QStackedWidget
    logs_empty_index: int
    logs_content_index: int
    logs_view: QPlainTextEdit
    logs_clear_button: QPushButton


@dataclass(frozen=True)
class _PanelShellRefs:
    panel: QWidget
    body_layout: QVBoxLayout


@dataclass(frozen=True)
class _EmptyStateRefs:
    page: QWidget
    badge_label: QLabel
    title_label: QLabel
    description_label: QLabel
    hint_label: QLabel


def _build_panel_shell(
    *,
    parent: QWidget,
    title: str,
    subtitle: str,
) -> _PanelShellRefs:
    panel = QWidget(parent)
    panel.setObjectName("panelPage")
    root_layout = QVBoxLayout(panel)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    card = QFrame(panel)
    card.setObjectName("panelCard")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 16, 16, 16)
    card_layout.setSpacing(14)

    header = QWidget(card)
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(3)
    title_label = QLabel(title, header)
    title_label.setObjectName("panelHeaderTitle")
    subtitle_label = QLabel(subtitle, header)
    subtitle_label.setObjectName("panelHeaderSubtitle")
    subtitle_label.setWordWrap(True)
    header_layout.addWidget(title_label)
    header_layout.addWidget(subtitle_label)

    body = QWidget(card)
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 0, 0)
    body_layout.setSpacing(10)

    card_layout.addWidget(header)
    card_layout.addWidget(body, stretch=1)
    root_layout.addWidget(card, stretch=1)
    return _PanelShellRefs(panel=panel, body_layout=body_layout)


def _build_empty_state(
    parent: QWidget,
    *,
    badge: str,
    title: str,
    description: str,
    hint: str,
) -> _EmptyStateRefs:
    page = QWidget(parent)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(6)
    layout.addStretch(1)

    card = QFrame(page)
    card.setObjectName("panelEmptyCard")
    card.setMaximumWidth(460)
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(20, 20, 20, 20)
    card_layout.setSpacing(8)
    card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

    badge_label = QLabel(badge, card)
    badge_label.setObjectName("panelEmptyBadge")
    badge_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    badge_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    title_label = QLabel(title, card)
    title_label.setObjectName("panelEmptyTitle")
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    description_label = QLabel(description, card)
    description_label.setObjectName("panelEmptyDescription")
    description_label.setWordWrap(True)
    description_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    description_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    hint_label = QLabel(hint, card)
    hint_label.setObjectName("panelEmptyHint")
    hint_label.setWordWrap(True)
    hint_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    hint_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    card_layout.addWidget(badge_label)
    card_layout.addWidget(title_label)
    card_layout.addWidget(description_label)
    card_layout.addWidget(hint_label)

    layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addStretch(1)
    return _EmptyStateRefs(
        page=page,
        badge_label=badge_label,
        title_label=title_label,
        description_label=description_label,
        hint_label=hint_label,
    )


def build_settings_panel(
    *,
    parent: QWidget,
    register_native_combo: Callable[[_NativeComboBox], None],
    on_update_controls_state: Callable[[], None],
    on_export_diagnostics: Callable[[], None],
    on_show_about: Callable[[], None],
) -> SettingsPanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Preferences",
        subtitle="Performance, post-download behavior, and app diagnostics.",
    )

    form_card = QFrame(shell.panel)
    form_card.setObjectName("panelFormCard")
    form_card_layout = QVBoxLayout(form_card)
    form_card_layout.setContentsMargins(16, 16, 16, 16)
    form_card_layout.setSpacing(12)

    form_intro = QLabel(
        "These defaults apply to new downloads until you change them in the main workflow.",
        form_card,
    )
    form_intro.setObjectName("panelFormIntro")
    form_intro.setWordWrap(True)
    form_card_layout.addWidget(form_intro)

    form_host = QWidget(form_card)
    layout = QFormLayout(form_host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(18)
    layout.setVerticalSpacing(12)

    subtitle_languages_edit = QLineEdit(form_host)
    subtitle_languages_edit.setPlaceholderText("en,es")
    subtitle_languages_edit.hide()

    subtitle_opts = QWidget(form_host)
    subtitle_opts_layout = QHBoxLayout(subtitle_opts)
    subtitle_opts_layout.setContentsMargins(0, 0, 0, 0)
    subtitle_opts_layout.setSpacing(10)
    write_subtitles_check = QCheckBox("Write subtitles", subtitle_opts)
    embed_subtitles_check = QCheckBox("Embed subtitles", subtitle_opts)
    write_subtitles_check.stateChanged.connect(lambda _v: on_update_controls_state())
    embed_subtitles_check.stateChanged.connect(lambda _v: on_update_controls_state())
    subtitle_opts_layout.addWidget(write_subtitles_check)
    subtitle_opts_layout.addWidget(embed_subtitles_check)
    subtitle_opts_layout.addStretch(1)
    subtitle_opts.hide()

    audio_language_combo = _NativeComboBox(form_host)
    register_native_combo(audio_language_combo)
    audio_language_combo.addItem("Any")
    audio_language_combo.hide()

    network_row = QWidget(form_host)
    network_layout = QHBoxLayout(network_row)
    network_layout.setContentsMargins(0, 0, 0, 0)
    network_layout.setSpacing(10)
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

    edit_friendly_encoder_combo = _NativeComboBox(form_host)
    register_native_combo(edit_friendly_encoder_combo)
    edit_friendly_encoder_combo.addItem("Auto (recommended)", "auto")
    edit_friendly_encoder_combo.addItem("System media engine", "apple")
    edit_friendly_encoder_combo.addItem("Dedicated graphics engine", "nvidia")
    edit_friendly_encoder_combo.addItem("Alternate graphics engine", "amd")
    edit_friendly_encoder_combo.addItem("Integrated graphics engine", "intel")
    edit_friendly_encoder_combo.addItem("Software encode", "cpu")
    layout.addRow("Edit-friendly encode", edit_friendly_encoder_combo)

    open_folder_after_download_check = QCheckBox(
        "Open output folder after downloads", form_host
    )
    layout.addRow("Post-download", open_folder_after_download_check)

    app_row = QWidget(form_host)
    app_row_layout = QHBoxLayout(app_row)
    app_row_layout.setContentsMargins(0, 0, 0, 0)
    app_row_layout.setSpacing(10)
    version_label = QLabel(f"Version {APP_VERSION}", app_row)
    version_label.setObjectName("panelInlineMeta")
    about_button = QPushButton("About", app_row)
    about_button.setObjectName("ghostButton")
    about_button.clicked.connect(on_show_about)
    export_diagnostics_button = QPushButton("Export diagnostics", app_row)
    export_diagnostics_button.setObjectName("ghostButton")
    export_diagnostics_button.clicked.connect(on_export_diagnostics)
    app_row_layout.addWidget(version_label)
    app_row_layout.addStretch(1)
    app_row_layout.addWidget(about_button)
    app_row_layout.addWidget(export_diagnostics_button)
    layout.addRow("App", app_row)

    form_card_layout.addWidget(form_host)
    shell.body_layout.addWidget(form_card)
    shell.body_layout.addStretch(1)
    return SettingsPanelRefs(
        panel=shell.panel,
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
        about_button=about_button,
    )


def build_queue_panel(
    *,
    parent: QWidget,
    on_remove_selected: Callable[[], None],
    on_move_up: Callable[[], None],
    on_move_down: Callable[[], None],
    on_clear: Callable[[], None],
) -> QueuePanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Download queue",
        subtitle="Batch multiple URLs and keep the current run order under control.",
    )

    queue_stack = QStackedWidget(shell.panel)
    empty = _build_empty_state(
        queue_stack,
        badge="QUEUE",
        title="Queue is empty",
        description="Analyze a URL in Downloads, then add it here to build a batch run.",
        hint="Next step: open Downloads, analyze a source, and add it to the queue.",
    )
    queue_empty_index = queue_stack.addWidget(empty.page)

    content = QWidget(queue_stack)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    queue_list = QListWidget(content)
    queue_list.setObjectName("panelList")
    queue_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    content_layout.addWidget(queue_list, stretch=1)
    queue_content_index = queue_stack.addWidget(content)
    shell.body_layout.addWidget(queue_stack, stretch=1)

    actions = QWidget(shell.panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(10)
    queue_remove_button = QPushButton("Remove", actions)
    queue_move_up_button = QPushButton("Move up", actions)
    queue_move_down_button = QPushButton("Move down", actions)
    queue_clear_button = QPushButton("Clear", actions)
    queue_clear_button.setObjectName("ghostButton")
    queue_remove_button.clicked.connect(on_remove_selected)
    queue_move_up_button.clicked.connect(on_move_up)
    queue_move_down_button.clicked.connect(on_move_down)
    queue_clear_button.clicked.connect(on_clear)
    actions_layout.addWidget(queue_remove_button)
    actions_layout.addWidget(queue_move_up_button)
    actions_layout.addWidget(queue_move_down_button)
    actions_layout.addWidget(queue_clear_button)
    actions_layout.addStretch(1)
    shell.body_layout.addWidget(actions)
    return QueuePanelRefs(
        panel=shell.panel,
        queue_stack=queue_stack,
        queue_empty_index=queue_empty_index,
        queue_content_index=queue_content_index,
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
    shell = _build_panel_shell(
        parent=parent,
        title="Recent downloads",
        subtitle="Quick access to the files and folders this app downloaded most recently.",
    )

    history_stack = QStackedWidget(shell.panel)
    empty = _build_empty_state(
        history_stack,
        badge="FILES",
        title="No downloads yet",
        description="Completed downloads will appear here so you can reopen files or folders quickly.",
        hint="Downloaded files and folders will stay one click away here.",
    )
    history_empty_index = history_stack.addWidget(empty.page)

    content = QWidget(history_stack)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    history_list = QListWidget(content)
    history_list.setObjectName("panelList")
    history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    content_layout.addWidget(history_list, stretch=1)
    history_content_index = history_stack.addWidget(content)
    shell.body_layout.addWidget(history_stack, stretch=1)

    actions = QWidget(shell.panel)
    actions_layout = QHBoxLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(10)
    history_open_file_button = QPushButton("Open file", actions)
    history_open_folder_button = QPushButton("Open folder", actions)
    history_clear_button = QPushButton("Clear", actions)
    history_clear_button.setObjectName("ghostButton")
    history_open_file_button.clicked.connect(on_open_file)
    history_open_folder_button.clicked.connect(on_open_folder)
    history_clear_button.clicked.connect(on_clear)
    actions_layout.addWidget(history_open_file_button)
    actions_layout.addWidget(history_open_folder_button)
    actions_layout.addWidget(history_clear_button)
    actions_layout.addStretch(1)
    shell.body_layout.addWidget(actions)
    return HistoryPanelRefs(
        panel=shell.panel,
        history_stack=history_stack,
        history_empty_index=history_empty_index,
        history_content_index=history_content_index,
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
    shell = _build_panel_shell(
        parent=parent,
        title="Activity log",
        subtitle="Inspect activity, format fetches, and the latest errors without leaving the app.",
    )

    logs_stack = QStackedWidget(shell.panel)
    empty = _build_empty_state(
        logs_stack,
        badge="LOGS",
        title="Nothing logged yet",
        description="Analyze a URL or start a download to populate the activity log.",
        hint="Fetches, status updates, and the latest errors will appear in this panel.",
    )
    logs_empty_index = logs_stack.addWidget(empty.page)

    content = QWidget(logs_stack)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    logs_view = QPlainTextEdit(content)
    logs_view.setObjectName("logsView")
    logs_view.setReadOnly(True)
    logs_view.setMaximumBlockCount(max_lines)
    logs_view.setPlaceholderText("Activity from format fetches and downloads will appear here.")
    content_layout.addWidget(logs_view, stretch=1)
    logs_content_index = logs_stack.addWidget(content)
    shell.body_layout.addWidget(logs_stack, stretch=1)

    logs_clear_button = QPushButton("Clear logs", shell.panel)
    logs_clear_button.setObjectName("ghostButton")
    logs_clear_button.clicked.connect(on_clear_logs)
    shell.body_layout.addWidget(logs_clear_button)
    return LogsPanelRefs(
        panel=shell.panel,
        logs_stack=logs_stack,
        logs_empty_index=logs_empty_index,
        logs_content_index=logs_content_index,
        logs_view=logs_view,
        logs_clear_button=logs_clear_button,
    )
