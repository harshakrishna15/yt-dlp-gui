from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
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
    LayoutConfig,
    NativeComboBoxConfig,
    QueueEmptyStateWidget,
    QueueListWidget,
    WidgetConfig,
    _NativeComboBox,
    build_button,
    build_grid,
    build_hbox,
    build_native_combo,
    build_vbox,
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
    export_logs_button: QPushButton
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
    panel_shell = build_vbox(
        parent,
        widget_config=WidgetConfig(object_name="panelPage"),
        layout_config=LayoutConfig(
            margins=(0, 0, 0, 0),
            spacing=14 if not framed else 0,
        ),
    )
    panel = panel_shell.widget
    root_layout = panel_shell.layout

    container: QWidget = panel
    container_layout: QVBoxLayout = root_layout
    if framed:
        card_shell = build_vbox(
            panel,
            widget_cls=QFrame,
            widget_config=WidgetConfig(object_name="panelCard"),
            layout_config=LayoutConfig(margins=(16, 16, 16, 16), spacing=14),
        )
        card = card_shell.widget
        card_layout = card_shell.layout
        root_layout.addWidget(card, stretch=1)
        container = card
        container_layout = card_layout

    header_shell = build_vbox(
        container,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=3),
    )
    header = header_shell.widget
    header_layout = header_shell.layout
    title_label = QLabel(title, header)
    title_label.setObjectName("panelHeaderTitle")
    header_layout.addWidget(title_label)

    body_shell = build_vbox(
        container,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=10),
    )
    body = body_shell.widget
    body_layout = body_shell.layout

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
    page_shell = build_vbox(
        parent,
        layout_config=LayoutConfig(margins=(28, 12, 28, 12), spacing=0),
    )
    page = page_shell.widget
    layout = page_shell.layout
    layout.addStretch(1)

    card_shell = build_vbox(
        page,
        widget_cls=QFrame,
        widget_config=WidgetConfig(
            object_name="panelEmptyCard",
            maximum_width=520,
            size_policy=(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            ),
        ),
        layout_config=LayoutConfig(
            margins=(24, 24, 24, 24),
            spacing=10,
            size_constraint=QLayout.SizeConstraint.SetMinimumSize,
        ),
    )
    card = card_shell.widget
    card_layout = card_shell.layout

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
    card_shell = build_vbox(
        parent,
        widget_cls=QFrame,
        widget_config=WidgetConfig(object_name=object_name),
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=spacing),
    )
    card = card_shell.widget
    layout = card_shell.layout

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
    actions_shell = build_hbox(
        parent,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=10),
    )
    actions = actions_shell.widget
    layout = actions_shell.layout

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

    form_card_shell = build_vbox(
        shell.panel,
        widget_cls=QFrame,
        widget_config=WidgetConfig(object_name="panelFormCard"),
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=12),
    )
    form_card = form_card_shell.widget
    form_card_layout = form_card_shell.layout

    settings_stack_shell = build_vbox(
        form_card,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=12),
    )
    settings_stack = settings_stack_shell.widget
    settings_stack_layout = settings_stack_shell.layout

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

    app_copy_shell = build_vbox(
        app_card.card,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=2),
    )
    app_copy = app_copy_shell.widget
    app_copy_layout = app_copy_shell.layout

    app_name_label = QLabel(APP_DISPLAY_NAME, app_copy)
    app_name_label.setObjectName("settingsAppName")
    app_name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    version_label = QLabel(f"Version {APP_VERSION}", app_copy)
    version_label.setObjectName("settingsAppVersion")
    version_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    app_copy_layout.addWidget(app_name_label)
    app_copy_layout.addWidget(version_label)

    app_actions_shell = build_hbox(
        app_card.card,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=0),
    )
    app_actions = app_actions_shell.widget
    app_actions_layout = app_actions_shell.layout
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

    content_shell = build_vbox(
        queue_stack,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=10),
    )
    content = content_shell.widget
    content_layout = content_shell.layout
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
    on_export_logs: Callable[[], None],
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

    content_shell = build_vbox(
        logs_stack,
        widget_config=WidgetConfig(object_name="logsContentPage"),
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=12),
    )
    content = content_shell.widget
    content_layout = content_shell.layout

    console_card_shell = build_vbox(
        content,
        widget_cls=QFrame,
        widget_config=WidgetConfig(object_name="logsConsoleCard"),
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=0),
    )
    console_card = console_card_shell.widget
    console_layout = console_card_shell.layout

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

    actions_shell = build_grid(
        shell.panel,
        widget_cls=QFrame,
        widget_config=WidgetConfig(
            object_name="runActionCard",
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
        layout_config=LayoutConfig(
            margins=(0, 0, 0, 0),
            horizontal_spacing=8,
            vertical_spacing=0,
        ),
    )
    actions = actions_shell.widget
    actions_layout = actions_shell.layout

    export_logs_button = build_button(
        actions,
        spec=ButtonSpec(
            text="Export logs",
            on_click=on_export_logs,
            object_name="secondaryActionButton",
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
    )
    actions_layout.addWidget(export_logs_button, 0, 0)

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
    actions_layout.addWidget(logs_clear_button, 0, 1)
    actions_layout.setColumnStretch(0, 1)
    actions_layout.setColumnStretch(1, 1)
    shell.body_layout.addWidget(actions)
    return LogsPanelRefs(
        panel=shell.panel,
        logs_stack=logs_stack,
        logs_empty_index=logs_empty_index,
        logs_content_index=logs_content_index,
        logs_view=logs_view,
        export_logs_button=export_logs_button,
        logs_clear_button=logs_clear_button,
    )
