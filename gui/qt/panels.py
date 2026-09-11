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

    badge_label = build_label(
        card,
        spec=LabelSpec(
            text=badge,
            widget_config=WidgetConfig(
                object_name="panelEmptyBadge",
                size_policy=(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        ),
    )

    title_label = build_label(
        card,
        spec=LabelSpec(
            text=title,
            widget_config=WidgetConfig(
                object_name="panelEmptyTitle",
                size_policy=(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            word_wrap=True,
        ),
    )

    description_label = build_label(
        card,
        spec=LabelSpec(
            text=description,
            widget_config=WidgetConfig(
                object_name="panelEmptyDescription",
                size_policy=(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            word_wrap=True,
        ),
    )

    hint_label = build_label(
        card,
        spec=LabelSpec(
            text=hint,
            widget_config=WidgetConfig(
                object_name="panelEmptyHint",
                size_policy=(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            word_wrap=True,
        ),
    )

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


def build_settings_panel(
    *,
    parent: QWidget,
    register_native_combo: Callable[[_NativeComboBox], None],
    on_update_yt_dlp: Callable[[], None],
    on_export_diagnostics: Callable[[], None],
    on_view_logs: Callable[[], None],
    on_remove_app_data: Callable[[], None] = lambda: None,
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

    engine_card = _build_settings_card(
        settings_stack,
        title="Download engine",
    )
    engine_row_shell = build_hbox(
        engine_card.card,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=10),
    )
    engine_row = engine_row_shell.widget
    engine_row_layout = engine_row_shell.layout
    yt_dlp_version_label = build_label(
        engine_row,
        spec=LabelSpec(
            text="yt-dlp unavailable",
            widget_config=WidgetConfig(object_name="settingsEngineVersion"),
        ),
    )
    yt_dlp_update_button = build_button(
        engine_row,
        spec=ButtonSpec(
            text="Update yt-dlp",
            on_click=on_update_yt_dlp,
            object_name="ghostButton",
        ),
    )
    engine_row_layout.addWidget(yt_dlp_version_label)
    engine_row_layout.addStretch(1)
    engine_row_layout.addWidget(yt_dlp_update_button)
    engine_card.layout.addWidget(engine_row)
    update_status_shell = build_vbox(
        engine_card.card,
        widget_config=WidgetConfig(object_name="updateStatus", fixed_height=68, visible=False),
        layout_config=LayoutConfig(margins=(0, 4, 0, 4), spacing=4),
    )
    update_status = update_status_shell.widget
    update_status_label = build_label(
        update_status,
        spec=LabelSpec(widget_config=WidgetConfig(object_name="updateStatusLabel")),
    )
    update_detail_label = ElidedLabel(update_status)
    update_detail_label.setObjectName("updateDetailLabel")
    update_detail_label.setProperty("allowToolTip", True)
    update_heading = build_hbox(
        update_status,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=8),
    )
    update_details_button = build_button(update_heading.widget, spec=ButtonSpec(
        text="View details", object_name="feedbackActionButton", on_click=on_view_logs,
        fixed_height=24,
    ))
    update_details_button.hide()
    update_heading.layout.addWidget(update_status_label, 1)
    update_heading.layout.addWidget(update_details_button)
    update_progress_bar = QProgressBar(update_status)
    update_progress_bar.setObjectName("updateProgressBar")
    update_progress_bar.setAccessibleName("yt-dlp update progress")
    update_progress_bar.setTextVisible(False)
    update_progress_bar.setRange(0, 100)
    update_progress_bar.setValue(0)
    update_status_shell.layout.addWidget(update_heading.widget)
    update_status_shell.layout.addWidget(update_progress_bar)
    update_status_shell.layout.addWidget(update_detail_label)
    engine_card.layout.addWidget(update_status)
    settings_stack_layout.addWidget(engine_card.card)

    open_folder_after_download_check = build_checkbox(
        settings_stack,
        spec=CheckBoxSpec(text="Open output folder after downloads"),
    )
    post_download_card = _build_settings_card(
        settings_stack,
        title="Post-download",
    )
    post_download_card.layout.addWidget(open_folder_after_download_check)
    settings_stack_layout.addWidget(post_download_card.card)

    remove_app_data_button = build_button(settings_stack, spec=ButtonSpec(
        text="Remove app data and quit...", object_name="ghostButton",
        on_click=on_remove_app_data,
    ))
    settings_stack_layout.addWidget(remove_app_data_button, alignment=Qt.AlignmentFlag.AlignLeft)

    app_card = _build_settings_card(
        settings_stack,
        object_name="settingsAppCard",
        spacing=0,
    )
    app_card.card.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Fixed,
    )

    app_copy_shell = build_hbox(
        app_card.card,
        layout_config=LayoutConfig(margins=(0, 0, 0, 0), spacing=12),
    )
    app_copy = app_copy_shell.widget
    app_copy_layout = app_copy_shell.layout

    app_name_label = build_label(
        app_copy,
        spec=LabelSpec(
            text=APP_DISPLAY_NAME,
            widget_config=WidgetConfig(object_name="settingsAppName"),
        ),
    )
    version_label = build_label(
        app_copy,
        spec=LabelSpec(
            text=f"Version {APP_VERSION}",
            widget_config=WidgetConfig(object_name="settingsAppVersion"),
        ),
    )
    app_copy_layout.addWidget(app_name_label)
    app_copy_layout.addWidget(version_label)
    app_copy_layout.addStretch(1)
    view_logs_button = build_button(
        app_copy,
        spec=ButtonSpec(text="View logs", object_name="ghostButton"),
    )
    app_copy_layout.addWidget(view_logs_button)
    export_diagnostics_button = build_button(
        app_copy,
        spec=ButtonSpec(
            text="Export diagnostics",
            on_click=on_export_diagnostics,
            object_name="ghostButton",
        ),
    )
    app_copy_layout.addWidget(export_diagnostics_button)
    app_card.layout.addWidget(app_copy)

    form_card_layout.addWidget(settings_stack)
    form_card_layout.addStretch(1)
    form_card_layout.addWidget(app_card.card)
    shell.body_layout.addWidget(form_card, stretch=1)
    return SettingsPanelRefs(
        panel=shell.panel,
        edit_friendly_encoder_combo=edit_friendly_encoder_combo,
        open_folder_after_download_check=open_folder_after_download_check,
        yt_dlp_version_label=yt_dlp_version_label,
        yt_dlp_update_button=yt_dlp_update_button,
        yt_dlp_update_status=update_status,
        yt_dlp_update_progress_bar=update_progress_bar,
        yt_dlp_update_status_label=update_status_label,
        yt_dlp_update_detail_label=update_detail_label,
        yt_dlp_update_details_button=update_details_button,
        export_diagnostics_button=export_diagnostics_button,
        view_logs_button=view_logs_button,
        remove_app_data_button=remove_app_data_button,
    )


def build_queue_panel(
    *,
    parent: QWidget,
    on_clear_queue: Callable[[], None],
    on_retry_failed: Callable[[], None] = lambda: None,
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
    shell.body_layout.addWidget(clear_panel.card, alignment=Qt.AlignmentFlag.AlignRight)

    return QueuePanelRefs(
        panel=shell.panel,
        queue_stack=queue_stack,
        queue_empty_index=queue_empty_index,
        queue_content_index=queue_content_index,
        queue_empty_state=empty,
        queue_list=queue_list,
        clear_queue_button=clear_queue_button,
        retry_failed_button=clear_panel.buttons[0],
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
        title="Activity Log",
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
    shell.body_layout.addWidget(actions, alignment=Qt.AlignmentFlag.AlignRight)
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
