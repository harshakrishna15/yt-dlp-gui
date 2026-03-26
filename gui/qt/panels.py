from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..app_meta import (
    APP_DISPLAY_NAME,
    APP_VERSION,
)
from .widgets import (
    ButtonSpec,
    NativeComboBoxConfig,
    QueueEmptyStateWidget,
    QueueListWidget,
    _NativeComboBox,
    build_button,
    build_native_combo,
)


@dataclass(frozen=True)
class SettingsPanelRefs:
    panel: QWidget
    edit_friendly_encoder_combo: _NativeComboBox
    open_folder_after_download_check: QCheckBox
    export_diagnostics_button: QPushButton


@dataclass(frozen=True)
class QueuePanelRefs:
    panel: QWidget
    queue_stack: QStackedWidget
    queue_empty_index: int
    queue_content_index: int
    queue_empty_state: QueueEmptyStateWidget
    queue_list: QueueListWidget


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


@dataclass(frozen=True)
class _SettingsCardRefs:
    card: QFrame
    layout: QVBoxLayout
    title_label: QLabel | None = None


def _build_panel_shell(
    *,
    parent: QWidget,
    title: str,
    framed: bool = True,
) -> _PanelShellRefs:
    panel = QWidget(parent)
    panel.setObjectName("panelPage")
    root_layout = QVBoxLayout(panel)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(14 if not framed else 0)

    container: QWidget = panel
    container_layout: QVBoxLayout = root_layout
    if framed:
        card = QFrame(panel)
        card.setObjectName("panelCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(14)
        root_layout.addWidget(card, stretch=1)
        container = card
        container_layout = card_layout

    header = QWidget(container)
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(3)
    title_label = QLabel(title, header)
    title_label.setObjectName("panelHeaderTitle")
    header_layout.addWidget(title_label)

    body = QWidget(container)
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 0, 0)
    body_layout.setSpacing(10)

    container_layout.addWidget(header)
    container_layout.addWidget(body, stretch=1)
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
    layout.setContentsMargins(28, 12, 28, 12)
    layout.setSpacing(0)
    layout.addStretch(1)

    card = QFrame(page)
    card.setObjectName("panelEmptyCard")
    card.setMaximumWidth(520)
    card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(24, 24, 24, 24)
    card_layout.setSpacing(10)
    card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

    badge_label = QLabel(badge, card)
    badge_label.setObjectName("panelEmptyBadge")
    badge_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    badge_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    title_label = QLabel(title, card)
    title_label.setObjectName("panelEmptyTitle")
    title_label.setWordWrap(True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    description_label = QLabel(description, card)
    description_label.setObjectName("panelEmptyDescription")
    description_label.setWordWrap(True)
    description_label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    )
    description_label.setSizePolicy(
        QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
    )

    hint_label = QLabel(hint, card)
    hint_label.setObjectName("panelEmptyHint")
    hint_label.setWordWrap(True)
    hint_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    hint_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    card_layout.addWidget(badge_label, alignment=Qt.AlignmentFlag.AlignLeft)
    card_layout.addWidget(title_label)
    card_layout.addWidget(description_label)
    card_layout.addWidget(hint_label)

    layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addStretch(1)
    return _EmptyStateRefs(
        page=page,
        badge_label=badge_label,
        title_label=title_label,
        description_label=description_label,
        hint_label=hint_label,
    )


def _build_settings_card(
    parent: QWidget,
    *,
    object_name: str = "settingsRowCard",
    spacing: int = 8,
    title: str = "",
) -> _SettingsCardRefs:
    card = QFrame(parent)
    card.setObjectName(object_name)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)

    title_label: QLabel | None = None
    if title.strip():
        title_label = QLabel(title, card)
        title_label.setObjectName("settingsRowTitle")
        layout.addWidget(title_label)

    return _SettingsCardRefs(card=card, layout=layout, title_label=title_label)


def _build_panel_actions(
    parent: QWidget,
    *,
    button_specs: Sequence[ButtonSpec],
) -> tuple[QWidget, tuple[QPushButton, ...]]:
    actions = QWidget(parent)
    layout = QHBoxLayout(actions)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    buttons: list[QPushButton] = []
    for spec in button_specs:
        button = build_button(actions, spec=spec)
        layout.addWidget(button)
        buttons.append(button)

    layout.addStretch(1)
    return actions, tuple(buttons)


def build_settings_panel(
    *,
    parent: QWidget,
    register_native_combo: Callable[[_NativeComboBox], None],
    on_export_diagnostics: Callable[[], None],
) -> SettingsPanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Preferences",
        framed=False,
    )

    form_card = QFrame(shell.panel)
    form_card.setObjectName("panelFormCard")
    form_card_layout = QVBoxLayout(form_card)
    form_card_layout.setContentsMargins(0, 0, 0, 0)
    form_card_layout.setSpacing(12)

    settings_stack = QWidget(form_card)
    settings_stack_layout = QVBoxLayout(settings_stack)
    settings_stack_layout.setContentsMargins(0, 0, 0, 0)
    settings_stack_layout.setSpacing(12)

    encode_card = _build_settings_card(
        settings_stack,
        title="Edit-friendly encode",
    )
    edit_friendly_encoder_combo = build_native_combo(
        encode_card.card,
        register_native_combo=register_native_combo,
        config=NativeComboBoxConfig(
            minimum_width=340,
            maximum_width=560,
            items=(
                ("Automatic (recommended)", "auto"),
                ("Apple hardware encoder", "apple"),
                ("NVIDIA hardware encoder", "nvidia"),
                ("AMD hardware encoder", "amd"),
                ("Intel hardware encoder", "intel"),
                ("CPU software encoder", "cpu"),
            ),
        ),
    )
    encode_card.layout.addWidget(
        edit_friendly_encoder_combo, alignment=Qt.AlignmentFlag.AlignLeft
    )
    settings_stack_layout.addWidget(encode_card.card)

    open_folder_after_download_check = QCheckBox(
        "Open output folder after downloads", settings_stack
    )
    post_download_card = _build_settings_card(
        settings_stack,
        title="Post-download",
    )
    post_download_card.layout.addWidget(open_folder_after_download_check)
    settings_stack_layout.addWidget(post_download_card.card)

    app_card = _build_settings_card(
        settings_stack,
        object_name="settingsAppCard",
        spacing=14,
    )
    app_card.card.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Fixed,
    )

    app_copy = QWidget(app_card.card)
    app_copy_layout = QVBoxLayout(app_copy)
    app_copy_layout.setContentsMargins(0, 0, 0, 0)
    app_copy_layout.setSpacing(2)

    app_name_label = QLabel(APP_DISPLAY_NAME, app_copy)
    app_name_label.setObjectName("settingsAppName")
    app_name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    version_label = QLabel(f"Version {APP_VERSION}", app_copy)
    version_label.setObjectName("settingsAppVersion")
    version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    app_copy_layout.addWidget(app_name_label)
    app_copy_layout.addWidget(version_label)

    app_actions = QWidget(app_card.card)
    app_actions_layout = QHBoxLayout(app_actions)
    app_actions_layout.setContentsMargins(0, 0, 0, 0)
    app_actions_layout.setSpacing(0)
    export_diagnostics_button = build_button(
        app_actions,
        spec=ButtonSpec(
            text="Export diagnostics",
            on_click=on_export_diagnostics,
            object_name="ghostButton",
        ),
    )
    app_actions_layout.addStretch(1)
    app_actions_layout.addWidget(export_diagnostics_button)
    app_actions_layout.addStretch(1)
    app_card.layout.addWidget(app_copy)
    app_card.layout.addWidget(app_actions)

    form_card_layout.addWidget(settings_stack)
    form_card_layout.addStretch(1)
    form_card_layout.addWidget(
        app_card.card,
        0,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
    )
    shell.body_layout.addWidget(form_card, stretch=1)
    return SettingsPanelRefs(
        panel=shell.panel,
        edit_friendly_encoder_combo=edit_friendly_encoder_combo,
        open_folder_after_download_check=open_folder_after_download_check,
        export_diagnostics_button=export_diagnostics_button,
    )


def build_queue_panel(
    *,
    parent: QWidget,
) -> QueuePanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Download Queue",
        framed=False,
    )

    queue_stack = QStackedWidget(shell.panel)
    empty = QueueEmptyStateWidget(queue_stack)
    queue_empty_index = queue_stack.addWidget(empty)

    content = QWidget(queue_stack)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(10)
    queue_list = QueueListWidget(content)
    queue_list.setObjectName("panelList")
    queue_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    content_layout.addWidget(queue_list, stretch=1)
    queue_content_index = queue_stack.addWidget(content)
    shell.body_layout.addWidget(queue_stack, stretch=1)
    return QueuePanelRefs(
        panel=shell.panel,
        queue_stack=queue_stack,
        queue_empty_index=queue_empty_index,
        queue_content_index=queue_content_index,
        queue_empty_state=empty,
        queue_list=queue_list,
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
        framed=False,
    )

    logs_stack = QStackedWidget(shell.panel)
    empty = _build_empty_state(
        logs_stack,
        badge="LOGS",
        title="Nothing logged yet",
        description="",
        hint="",
    )
    logs_empty_index = logs_stack.addWidget(empty.page)

    content = QWidget(logs_stack)
    content.setObjectName("logsContentPage")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(12)

    console_card = QFrame(content)
    console_card.setObjectName("logsConsoleCard")
    console_layout = QVBoxLayout(console_card)
    console_layout.setContentsMargins(0, 0, 0, 0)
    console_layout.setSpacing(0)

    logs_view = QPlainTextEdit(console_card)
    logs_view.setObjectName("logsView")
    logs_view.setReadOnly(True)
    logs_view.setMaximumBlockCount(max_lines)
    logs_view.setPlaceholderText(
        "Activity from format fetches and downloads will appear here."
    )
    console_layout.addWidget(logs_view, stretch=1)
    content_layout.addWidget(console_card, stretch=1)
    logs_content_index = logs_stack.addWidget(content)
    shell.body_layout.addWidget(logs_stack, stretch=1)

    actions = QFrame(shell.panel)
    actions.setObjectName("runActionCard")
    actions.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed,
    )
    actions_layout = QGridLayout(actions)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setHorizontalSpacing(8)
    actions_layout.setVerticalSpacing(0)

    logs_clear_button = build_button(
        actions,
        spec=ButtonSpec(
            text="Clear logs",
            on_click=on_clear_logs,
            object_name="dangerActionButton",
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
    )
    logs_clear_button.setProperty("pill", True)
    actions_layout.addWidget(logs_clear_button, 0, 0)
    shell.body_layout.addWidget(actions)
    return LogsPanelRefs(
        panel=shell.panel,
        logs_stack=logs_stack,
        logs_empty_index=logs_empty_index,
        logs_content_index=logs_content_index,
        logs_view=logs_view,
        logs_clear_button=logs_clear_button,
    )
