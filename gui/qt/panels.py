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
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..app_meta import (
    APP_DISPLAY_NAME,
    APP_VERSION,
)
from .widgets import (
    ButtonSpec,
    CheckBoxSpec,
    ElidedLabel,
    LabelSpec,
    LayoutConfig,
    NativeComboBoxConfig,
    QueueEmptyStateWidget,
    EmptyStateWidget,
    build_divider,
    build_labeled_fields,
    LabeledFieldSpec,
    QueueListWidget,
    WidgetConfig,
    _NativeComboBox,
    build_button,
    build_button_panel,
    build_checkbox,
    build_hbox,
    build_label,
    build_native_combo,
    build_vbox,
)


@dataclass(frozen=True)
class SettingsPanelRefs:
    panel: QWidget
    edit_friendly_encoder_combo: _NativeComboBox
    open_folder_after_download_check: QCheckBox
    yt_dlp_version_label: QLabel
    yt_dlp_update_button: QPushButton
    yt_dlp_update_status: QWidget
    yt_dlp_update_progress_bar: QProgressBar
    yt_dlp_update_status_label: QLabel
    yt_dlp_update_detail_label: QLabel
    yt_dlp_update_details_button: QPushButton
    export_diagnostics_button: QPushButton
    view_logs_button: QPushButton
    remove_app_data_button: QPushButton


@dataclass(frozen=True)
class QueuePanelRefs:
    panel: QWidget
    queue_stack: QStackedWidget
    queue_empty_index: int
    queue_content_index: int
    queue_empty_state: QueueEmptyStateWidget
    queue_list: QueueListWidget
    clear_queue_button: QPushButton
    retry_failed_button: QPushButton
    start_queue_button: QPushButton
    undo_button: QPushButton
    undo_row: QWidget


@dataclass(frozen=True)
class LogsPanelRefs:
    panel: QWidget
    logs_stack: QStackedWidget
    logs_empty_index: int
    logs_content_index: int
    logs_view: QPlainTextEdit
    export_logs_button: QPushButton
    logs_clear_button: QPushButton
    back_button: QToolButton


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
            spacing=24 if not framed else 0,
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
    title_label = build_label(
        header,
        spec=LabelSpec(
            text=title,
            widget_config=WidgetConfig(object_name="panelHeaderTitle"),
        ),
    )
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


def _build_empty_state(parent: QWidget, *, badge: str, title: str,
                       description: str, hint: str) -> _EmptyStateRefs:
    page = EmptyStateWidget(parent, title=title, description=description or hint,
                            icon="logs.svg" if badge == "LOGS" else "queue-active.svg")
    empty = QLabel(page)
    empty.hide()
    return _EmptyStateRefs(page, page.placeholder_icon, page.placeholder_title,
                           page.placeholder_description, empty)


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
        title_label = build_label(
            card,
            spec=LabelSpec(
                text=title,
                widget_config=WidgetConfig(object_name="settingsRowTitle"),
            ),
        )
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


def _build_preference_row(parent: QWidget, *, title: str, control: QWidget,
                          detail: str = "", detail_widget: QWidget | None = None) -> QWidget:
    row = build_hbox(parent, widget_config=WidgetConfig(object_name="preferenceRow", minimum_height=48),
                     layout_config=LayoutConfig(spacing=24))
    copy = build_vbox(row.widget, layout_config=LayoutConfig(spacing=4))
    copy.widget.setMinimumWidth(0)
    copy.layout.addWidget(build_label(copy.widget, spec=LabelSpec(
        text=title, widget_config=WidgetConfig(object_name="preferenceRowTitle"), word_wrap=True)))
    if detail_widget is not None:
        copy.layout.addWidget(detail_widget)
    elif detail:
        copy.layout.addWidget(build_label(copy.widget, spec=LabelSpec(
            text=detail, widget_config=WidgetConfig(object_name="preferenceRowDetail"), word_wrap=True)))
    row.layout.addWidget(copy.widget, 1)
    row.layout.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return row.widget


def build_settings_panel(
    *,
    parent: QWidget,
    register_native_combo: Callable[[_NativeComboBox], None],
    on_update_yt_dlp: Callable[[], None],
    on_export_diagnostics: Callable[[], None],
    on_view_logs: Callable[[], None],
    on_remove_app_data: Callable[[], None] = lambda: None,
) -> SettingsPanelRefs:
    shell = _build_panel_shell(parent=parent, title="Preferences", framed=False)
    form = build_vbox(shell.panel, widget_cls=QFrame,
        widget_config=WidgetConfig(object_name="panelFormCard"),
        layout_config=LayoutConfig(spacing=24))
    downloads = _build_settings_card(form.widget, title="Downloads", spacing=12)
    encoder = build_native_combo(downloads.card, register_native_combo=register_native_combo,
        config=NativeComboBoxConfig(minimum_width=260, maximum_width=320, items=(
            ("Automatic (recommended)", "auto"), ("Apple hardware encoder", "apple"),
            ("NVIDIA hardware encoder", "nvidia"), ("AMD hardware encoder", "amd"),
            ("Intel hardware encoder", "intel"), ("CPU software encoder", "cpu"))))
    encoder.setAccessibleName("Edit-friendly encoder")
    downloads.layout.addWidget(_build_preference_row(downloads.card,
        title="Edit-friendly encoder", detail="Used when converting videos for editing.", control=encoder))
    open_folder = build_checkbox(downloads.card, spec=CheckBoxSpec(text="Open output folder"))
    open_folder.setAccessibleName("Open output folder after downloads")
    downloads.layout.addWidget(_build_preference_row(downloads.card,
        title="After downloading", control=open_folder))
    form.layout.addWidget(downloads.card)

    app = _build_settings_card(form.widget, title="App", object_name="settingsAppCard", spacing=12)
    engine = _build_settings_card(app.card, spacing=8)
    version = build_label(engine.card, spec=LabelSpec(text="yt-dlp unavailable",
        widget_config=WidgetConfig(object_name="settingsEngineVersion")))
    update = build_button(engine.card, spec=ButtonSpec("Update yt-dlp", object_name="ghostButton",
        role="secondary", compact=True, on_click=on_update_yt_dlp))
    engine.layout.addWidget(_build_preference_row(engine.card, title="Download engine",
        detail_widget=version, control=update))

    status = build_vbox(engine.card,
        widget_config=WidgetConfig(object_name="updateStatus", minimum_height=68, visible=False),
        layout_config=LayoutConfig(margins=(0, 0, 0, 4), spacing=4))
    heading = build_hbox(status.widget, widget_config=WidgetConfig(minimum_height=32),
                         layout_config=LayoutConfig(spacing=8))
    status_label = build_label(heading.widget,
        spec=LabelSpec(widget_config=WidgetConfig(object_name="updateStatusLabel")))
    details = build_button(heading.widget, spec=ButtonSpec("View details",
        object_name="feedbackActionButton", compact=True, on_click=on_view_logs))
    details.hide()
    heading.layout.addWidget(status_label, 1)
    heading.layout.addWidget(details)
    progress = QProgressBar(status.widget)
    progress.setObjectName("updateProgressBar")
    progress.setAccessibleName("yt-dlp update progress")
    progress.setTextVisible(False)
    progress.setRange(0, 100)
    progress.setValue(0)
    detail_label = ElidedLabel(status.widget)
    detail_label.setObjectName("updateDetailLabel")
    detail_label.setProperty("allowToolTip", True)
    status.layout.addWidget(heading.widget)
    status.layout.addWidget(progress)
    status.layout.addWidget(detail_label)
    engine.layout.addWidget(status.widget)
    app.layout.addWidget(engine.card)

    support = build_hbox(app.card, layout_config=LayoutConfig(spacing=8))
    logs = build_button(support.widget, spec=ButtonSpec("View logs", object_name="ghostButton",
                                                       role="secondary", compact=True))
    diagnostics = build_button(support.widget, spec=ButtonSpec("Export diagnostics",
        object_name="ghostButton", role="secondary", compact=True, on_click=on_export_diagnostics))
    support.layout.addWidget(logs)
    support.layout.addWidget(diagnostics)
    app.layout.addWidget(_build_preference_row(app.card, title="Troubleshooting", control=support.widget))
    form.layout.addWidget(app.card)

    build_divider(form.widget, form.layout)
    remove = build_button(form.widget, spec=ButtonSpec("Remove app data and quit...",
        object_name="ghostButton", role="destructive", compact=True, on_click=on_remove_app_data))
    form.layout.addWidget(remove, alignment=Qt.AlignmentFlag.AlignLeft)
    form.layout.addStretch(1)
    footer = build_hbox(form.widget, layout_config=LayoutConfig(spacing=8))
    footer.layout.addWidget(build_label(footer.widget, spec=LabelSpec(text=APP_DISPLAY_NAME,
        widget_config=WidgetConfig(object_name="settingsAppName"))))
    footer.layout.addWidget(build_label(footer.widget, spec=LabelSpec(text=f"Version {APP_VERSION}",
        widget_config=WidgetConfig(object_name="settingsAppVersion"))))
    footer.layout.addStretch(1)
    form.layout.addWidget(footer.widget)
    shell.body_layout.addWidget(form.widget, stretch=1)
    return SettingsPanelRefs(panel=shell.panel, edit_friendly_encoder_combo=encoder,
        open_folder_after_download_check=open_folder, yt_dlp_version_label=version,
        yt_dlp_update_button=update, yt_dlp_update_status=status.widget,
        yt_dlp_update_progress_bar=progress, yt_dlp_update_status_label=status_label,
        yt_dlp_update_detail_label=detail_label, yt_dlp_update_details_button=details,
        export_diagnostics_button=diagnostics, view_logs_button=logs, remove_app_data_button=remove)


def build_queue_panel(
    *,
    parent: QWidget,
    on_clear_queue: Callable[[], None],
    on_retry_failed: Callable[[], None] = lambda: None,
    on_start_queue: Callable[[], None] = lambda: None,
    on_downloads: Callable[[], None] = lambda: None,
    on_undo: Callable[[], None] = lambda: None,
) -> QueuePanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Queue",
        framed=False,
    )

    queue_stack = QStackedWidget(shell.panel)
    empty = QueueEmptyStateWidget(queue_stack)
    go_button = build_button(empty, spec=ButtonSpec("Go to Downloads", role="secondary", on_click=on_downloads))
    empty.content_layout.addWidget(go_button, alignment=Qt.AlignmentFlag.AlignHCenter)
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
    undo_shell = build_hbox(shell.panel, layout_config=LayoutConfig(spacing=12))
    undo_shell.layout.addWidget(QLabel("Queue cleared", undo_shell.widget))
    undo_button = build_button(undo_shell.widget, spec=ButtonSpec("Undo", role="quiet", compact=True, on_click=on_undo))
    undo_shell.layout.addWidget(undo_button)
    undo_shell.layout.addStretch(1)
    undo_shell.widget.hide()
    shell.body_layout.addWidget(undo_shell.widget)

    clear_panel = build_button_panel(
        shell.panel,
        card_config=WidgetConfig(
            object_name="runActionCard",
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
        host_config=WidgetConfig(
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
        buttons_layout_config=LayoutConfig(
            margins=(0, 0, 0, 0),
            horizontal_spacing=12,
            vertical_spacing=0,
        ),
        button_specs=(
            ButtonSpec(text="Retry failed", object_name="ghostButton",
                       size_policy=(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed),
                       on_click=on_retry_failed),
            ButtonSpec(
                text="Clear all",
                role="destructive",
                object_name="ghostButton",
                size_policy=(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed,
                ),
                on_click=on_clear_queue,
            ),
        ),
    )
    clear_queue_button = clear_panel.buttons[1]
    start_queue_button = build_button(shell.panel, spec=ButtonSpec(
        "Start queue", role="primary", object_name="primaryActionButton", on_click=on_start_queue))
    queue_actions = build_hbox(shell.panel, layout_config=LayoutConfig(spacing=12))
    clear_panel.buttons_layout.removeWidget(clear_queue_button)
    clear_panel.buttons_layout.removeWidget(clear_panel.buttons[0])
    clear_panel.card.hide()
    queue_actions.layout.addWidget(clear_queue_button)
    queue_actions.layout.addStretch(1)
    queue_actions.layout.addWidget(clear_panel.buttons[0])
    queue_actions.layout.addWidget(start_queue_button)
    build_divider(shell.panel, shell.body_layout)
    shell.body_layout.addWidget(queue_actions.widget)

    return QueuePanelRefs(
        panel=shell.panel,
        queue_stack=queue_stack,
        queue_empty_index=queue_empty_index,
        queue_content_index=queue_content_index,
        queue_empty_state=empty,
        queue_list=queue_list,
        clear_queue_button=clear_queue_button,
        retry_failed_button=clear_panel.buttons[0],
        start_queue_button=start_queue_button,
        undo_button=undo_button,
        undo_row=undo_shell.widget,
    )


def build_logs_panel(
    *,
    parent: QWidget,
    max_lines: int,
    on_export_logs: Callable[[], None],
    on_clear_logs: Callable[[], None],
    on_back: Callable[[], None],
) -> LogsPanelRefs:
    shell = _build_panel_shell(
        parent=parent,
        title="Logs",
        framed=False,
    )
    back_button = QToolButton(shell.panel)
    back_button.setObjectName("panelBackButton")
    back_button.setText("Preferences")
    back_button.setArrowType(Qt.ArrowType.LeftArrow)
    back_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    back_button.clicked.connect(on_back)
    back_button.setAccessibleName("Back to Preferences")
    shell.panel.layout().insertWidget(0, back_button, alignment=Qt.AlignmentFlag.AlignLeft)

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

    action_panel = build_button_panel(
        shell.panel,
        card_config=WidgetConfig(
            object_name="runActionCard",
            size_policy=(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            ),
        ),
        buttons_layout_config=LayoutConfig(
            margins=(0, 0, 0, 0),
            horizontal_spacing=8,
            vertical_spacing=0,
        ),
        button_specs=(
            ButtonSpec(
                text="Export logs",
                on_click=on_export_logs,
                object_name="secondaryActionButton",
                size_policy=(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            ButtonSpec(
                text="Clear logs",
                on_click=on_clear_logs,
                object_name="dangerActionButton",
                size_policy=(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
        ),
    )
    actions = action_panel.card
    export_logs_button, logs_clear_button = action_panel.buttons
    grid = action_panel.buttons_layout
    grid.removeWidget(export_logs_button)
    grid.removeWidget(logs_clear_button)
    grid.addWidget(logs_clear_button, 0, 0)
    grid.addWidget(export_logs_button, 0, 2)
    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 0)
    build_divider(shell.panel, shell.body_layout)
    shell.body_layout.addWidget(actions)
    return LogsPanelRefs(
        panel=shell.panel,
        logs_stack=logs_stack,
        logs_empty_index=logs_empty_index,
        logs_content_index=logs_content_index,
        logs_view=logs_view,
        export_logs_button=export_logs_button,
        logs_clear_button=logs_clear_button,
        back_button=back_button,
    )
