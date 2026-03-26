from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .constants import OUTPUT_CARD_STACK_GAP
from .link_input import LinkInputRefs, build_link_input_module
from .widgets import (
    ButtonSpec,
    NativeComboBoxConfig,
    QueueEmptyStateWidget,
    SegmentedRailSpec,
    SourceToastRefs,
    _NativeComboBox,
    build_button,
    build_native_combo,
    build_segmented_rail,
    build_source_feedback_toast,
)


@dataclass(frozen=True)
class TopBarRefs:
    header: QWidget
    top_actions: QWidget
    classic_actions: QWidget
    downloads_button: QPushButton
    queue_button: QPushButton
    logs_button: QPushButton
    settings_button: QPushButton


@dataclass(frozen=True)
class MixedUrlRefs:
    overlay: QFrame
    overlay_layout: QVBoxLayout
    alert: QFrame
    alert_label: QLabel
    buttons_layout: QHBoxLayout
    use_single_video_url_button: QPushButton
    use_playlist_url_button: QPushButton


@dataclass(frozen=True)
class RunSectionRefs:
    state_host: QWidget
    activity_card: QFrame
    actions_card: QFrame
    actions_shell_layout: QVBoxLayout
    actions_layout: QGridLayout
    status_value: QLabel
    start_button: QPushButton
    add_queue_button: QPushButton
    cancel_button: QPushButton


@dataclass(frozen=True)
class DownloadsViewRefs:
    main_page: QWidget
    main_page_index: int
    workspace_layout: QHBoxLayout
    source_row: QWidget
    url_edit: QLineEdit
    paste_button: QPushButton
    analyze_button: QPushButton
    source_details_host: QWidget
    source_details_stack: QStackedWidget
    source_details_empty: QWidget
    playlist_items_panel: QWidget
    playlist_items_edit: QLineEdit
    source_details_label: QLabel
    output_section: QWidget
    output_layout: QVBoxLayout
    format_card: QGroupBox
    format_layout: QVBoxLayout
    mode_row_layout: QHBoxLayout
    video_radio: QPushButton
    audio_radio: QPushButton
    content_type_label: QLabel
    content_type_row: QWidget
    container_combo: _NativeComboBox
    convert_check: QCheckBox
    container_label: QLabel
    post_process_label: QLabel
    post_process_row: QWidget
    codec_combo: _NativeComboBox
    codec_label: QLabel
    format_combo: _NativeComboBox
    format_label: QLabel
    output_form_labels: list[QLabel]
    output_form_rows: list[QWidget]
    format_row: QWidget
    save_card: QWidget
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QVBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel
    progress_bar: QProgressBar
    metrics_card: QFrame
    metrics_strip: QFrame
    progress_label: QLabel
    speed_label: QLabel
    eta_label: QLabel
    item_label: QLabel
    run: RunSectionRefs


@dataclass(frozen=True)
class UiRefs:
    root: QWidget
    panel_stack: QStackedWidget
    top_bar: TopBarRefs
    mixed_url: MixedUrlRefs
    source_toast: SourceToastRefs
    downloads: DownloadsViewRefs


@dataclass(frozen=True)
class RunSectionCallbacks:
    on_start: Callable[[], None]
    on_add_to_queue: Callable[[], None]
    on_cancel: Callable[[], None]


@dataclass(frozen=True)
class DownloadsViewCallbacks:
    on_url_changed: Callable[[], None]
    on_fetch_formats: Callable[[], None]
    on_analyze_url: Callable[[], None]
    on_paste_url: Callable[[], None]
    on_mode_change: Callable[[], None]
    on_container_change: Callable[[], None]
    on_codec_change: Callable[[], None]
    on_update_controls_state: Callable[[], None]
    on_pick_folder: Callable[[], None]
    on_use_single_video_url: Callable[[], None]
    on_use_playlist_url: Callable[[], None]
    run: RunSectionCallbacks


@dataclass(frozen=True)
class _DownloadsStateRefs:
    state_host: QWidget
    source_details_host: QWidget
    source_details_stack: QStackedWidget
    source_details_empty: QWidget
    playlist_items_panel: QWidget
    playlist_items_edit: QLineEdit
    source_details_label: QLabel


@dataclass(frozen=True)
class _OutputSectionRefs:
    section: QGroupBox
    layout: QVBoxLayout
    link_input: LinkInputRefs
    format_card: QGroupBox
    format_layout: QVBoxLayout
    mode_row_layout: QHBoxLayout
    video_radio: QPushButton
    audio_radio: QPushButton
    content_type_label: QLabel
    content_type_row: QWidget
    container_combo: _NativeComboBox
    convert_check: QCheckBox
    container_label: QLabel
    post_process_label: QLabel
    post_process_row: QWidget
    codec_combo: _NativeComboBox
    codec_label: QLabel
    format_combo: _NativeComboBox
    format_label: QLabel
    output_form_labels: list[QLabel]
    output_form_rows: list[QWidget]
    format_row: QWidget
    save_card: QWidget
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QVBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel
    progress_bar: QProgressBar
    metrics_card: QFrame
    metrics_strip: QFrame
    progress_label: QLabel
    speed_label: QLabel
    eta_label: QLabel
    item_label: QLabel


@dataclass(frozen=True)
class _LabeledRowSpec:
    key: str
    label: QLabel
    field: QWidget
    field_spacing: int = 20
    field_alignment: Qt.Alignment | None = None
    visible: bool = True


class TopBarBuilder:
    @staticmethod
    def build(parent: QWidget) -> TopBarRefs:
        header = QWidget(parent)
        header.setObjectName("topBarShell")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        top_actions = QWidget(header)
        top_actions.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        top_actions_layout = QHBoxLayout(top_actions)
        top_actions_layout.setContentsMargins(0, 0, 4, 0)
        top_actions_layout.setSpacing(8)

        classic_actions, classic_buttons = build_segmented_rail(
            top_actions,
            spec=SegmentedRailSpec(
                object_name="topNavRail",
                layout_margins=(4, 4, 4, 4),
                layout_spacing=4,
                button_specs=(
                    ButtonSpec(
                        "Downloads",
                        object_name="topNavButton",
                        checkable=True,
                        size_policy=(
                            QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed,
                        ),
                    ),
                    ButtonSpec(
                        "Queue",
                        object_name="topNavButton",
                        checkable=True,
                        size_policy=(
                            QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed,
                        ),
                    ),
                    ButtonSpec(
                        "Logs",
                        object_name="topNavButton",
                        checkable=True,
                        size_policy=(
                            QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed,
                        ),
                    ),
                ),
            ),
        )
        downloads_button, queue_button, logs_button = classic_buttons

        settings_button = build_button(
            top_actions,
            spec=ButtonSpec(
                "",
                object_name="topIconButton",
                checkable=True,
                size_policy=(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
        )
        settings_button.setAccessibleName("Settings")

        top_actions_layout.addStretch(1)
        top_actions_layout.addWidget(
            classic_actions,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
        )
        top_actions_layout.addStretch(1)
        top_actions_layout.addWidget(
            settings_button,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        header_layout.addWidget(top_actions, stretch=1)
        return TopBarRefs(
            header=header,
            top_actions=top_actions,
            classic_actions=classic_actions,
            downloads_button=downloads_button,
            queue_button=queue_button,
            logs_button=logs_button,
            settings_button=settings_button,
        )


class RunSectionBuilder:
    @staticmethod
    def build(parent: QWidget, callbacks: RunSectionCallbacks) -> RunSectionRefs:
        run_state_host = QWidget(parent)
        run_state_host.setObjectName("runStateHost")
        run_state_host.setFixedSize(0, 0)
        run_state_host.move(-10_000, -10_000)
        run_state_host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        run_state_host.hide()

        activity_card = QFrame(run_state_host)
        activity_card.setObjectName("runActivityCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 16, 16, 16)
        activity_layout.setSpacing(12)

        status_value = QLabel("Idle", activity_card)
        status_value.setObjectName("statusLine")
        status_value.setVisible(False)

        activity_layout.addWidget(status_value)

        actions_card = QFrame(parent)
        actions_card.setObjectName("runActionCard")
        actions_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        buttons_shell_layout = QVBoxLayout(actions_card)
        buttons_shell_layout.setContentsMargins(0, 0, 0, 0)
        buttons_shell_layout.setSpacing(0)

        buttons_host = QWidget(actions_card)
        buttons_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        buttons_layout = QGridLayout(buttons_host)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setHorizontalSpacing(8)
        buttons_layout.setVerticalSpacing(0)
        buttons_shell_layout.addWidget(buttons_host, 0, Qt.AlignmentFlag.AlignTop)

        action_button_policy = (
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        start_button = build_button(
            buttons_host,
            spec=ButtonSpec(
                text="Download",
                object_name="primaryActionButton",
                size_policy=action_button_policy,
                on_click=callbacks.on_start,
            ),
        )
        add_queue_button = build_button(
            buttons_host,
            spec=ButtonSpec(
                text="Add to queue",
                object_name="secondaryActionButton",
                size_policy=action_button_policy,
                on_click=callbacks.on_add_to_queue,
            ),
        )
        cancel_button = build_button(
            buttons_host,
            spec=ButtonSpec(
                text="Cancel",
                object_name="dangerActionButton",
                size_policy=action_button_policy,
                on_click=callbacks.on_cancel,
            ),
        )

        buttons_layout.addWidget(start_button, 0, 0)
        buttons_layout.addWidget(add_queue_button, 0, 1)
        buttons_layout.addWidget(cancel_button, 0, 2)
        buttons_layout.setColumnStretch(0, 1)
        buttons_layout.setColumnStretch(1, 1)
        buttons_layout.setColumnStretch(2, 1)
        return RunSectionRefs(
            state_host=run_state_host,
            activity_card=activity_card,
            actions_card=actions_card,
            actions_shell_layout=buttons_shell_layout,
            actions_layout=buttons_layout,
            status_value=status_value,
            start_button=start_button,
            add_queue_button=add_queue_button,
            cancel_button=cancel_button,
        )


def _build_section_header(
    parent: QWidget,
    title: str,
    *,
    compact: bool,
    meta: str | None = None,
) -> QWidget:
    header = QWidget(parent)
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(10)

    title_label = QLabel(title, header)
    title_label.setObjectName("cardHeaderTitle" if compact else "sectionHeaderTitle")
    header_layout.addWidget(title_label)
    header_layout.addStretch(1)
    if meta:
        meta_label = QLabel(meta, header)
        meta_label.setObjectName("sectionMetaChip")
        header_layout.addWidget(
            meta_label,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

    return header


def _content_mode_selection_rect(button: QPushButton) -> QRect:
    rect = button.geometry()
    horizontal_inset = min(1, max(0, (rect.width() - 1) // 2))
    vertical_inset = min(1, max(0, (rect.height() - 1) // 2))
    inset_rect = rect.adjusted(
        horizontal_inset,
        vertical_inset,
        -horizontal_inset,
        -vertical_inset,
    )
    if inset_rect.width() <= 0 or inset_rect.height() <= 0:
        return rect
    return inset_rect


def _add_labeled_row(
    parent: QWidget,
    layout: QVBoxLayout,
    label: QLabel,
    field: QWidget,
    *,
    field_spacing: int = 20,
    field_alignment: Qt.Alignment | None = None,
) -> QWidget:
    block = QWidget(parent)
    block.setObjectName("outputCardBlock")
    block_layout = QVBoxLayout(block)
    block_layout.setContentsMargins(0, 0, 0, 0)
    block_layout.setSpacing(4)

    row = QWidget(block)
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(field_spacing)

    field_host = QWidget(row)
    field_host_layout = QVBoxLayout(field_host)
    field_host_layout.setContentsMargins(0, 0, 0, 0)
    field_host_layout.setSpacing(0)
    if field_alignment is None:
        field_host_layout.addWidget(field)
    else:
        field_host_layout.addWidget(field, 0, field_alignment)

    row_layout.addWidget(label)
    row_layout.addWidget(field_host, stretch=1)
    block_layout.addWidget(row)
    layout.addWidget(block)
    return block


def _build_labeled_rows(
    parent: QWidget,
    layout: QVBoxLayout,
    specs: Sequence[_LabeledRowSpec],
) -> dict[str, QWidget]:
    rows: dict[str, QWidget] = {}
    for spec in specs:
        row = _add_labeled_row(
            parent,
            layout,
            spec.label,
            spec.field,
            field_spacing=spec.field_spacing,
            field_alignment=spec.field_alignment,
        )
        row.setVisible(spec.visible)
        rows[spec.key] = row
    return rows


def _add_save_block(
    parent: QWidget,
    layout: QVBoxLayout,
    label: QLabel,
    field: QWidget,
) -> QWidget:
    block = QWidget(parent)
    block.setObjectName("outputCardBlock")
    block_layout = QVBoxLayout(block)
    block_layout.setContentsMargins(8, 5, 8, 5)
    block_layout.setSpacing(5)
    block_layout.addWidget(label)
    block_layout.addWidget(field)
    layout.addWidget(block)
    return block


class DownloadsViewBuilder:
    @staticmethod
    def _build_downloads_state(
        parent: QWidget,
        callbacks: DownloadsViewCallbacks,
    ) -> _DownloadsStateRefs:
        state_host = QWidget(parent)
        state_host.setObjectName("downloadsStateHost")
        state_host.setFixedSize(0, 0)
        state_host.move(-10_000, -10_000)
        state_host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        state_host.hide()

        source_details_block = QWidget(state_host)
        source_details_block_layout = QVBoxLayout(source_details_block)
        source_details_block_layout.setContentsMargins(0, 0, 0, 0)
        source_details_block_layout.setSpacing(4)
        source_details_label = QLabel("", source_details_block)
        source_details_label.setObjectName("sectionFormLabel")
        source_details_block_layout.addWidget(source_details_label)

        source_details_host = QWidget(source_details_block)
        source_details_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_details_layout = QVBoxLayout(source_details_host)
        source_details_layout.setContentsMargins(0, 0, 0, 0)
        source_details_layout.setSpacing(0)
        source_details_stack = QStackedWidget(source_details_host)
        source_details_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_details_layout.addWidget(source_details_stack)

        source_details_empty = QWidget(source_details_stack)
        source_details_stack.addWidget(source_details_empty)

        playlist_items_panel = QWidget(source_details_stack)
        playlist_items_layout = QHBoxLayout(playlist_items_panel)
        playlist_items_layout.setContentsMargins(0, 1, 0, 1)
        playlist_items_layout.setSpacing(0)
        playlist_items_edit = QLineEdit(playlist_items_panel)
        playlist_items_edit.setPlaceholderText("Optional: 1-5,7,10-")
        playlist_items_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        playlist_items_edit.textChanged.connect(
            lambda _text: callbacks.on_update_controls_state()
        )
        playlist_items_layout.addWidget(playlist_items_edit, stretch=1)
        source_details_stack.addWidget(playlist_items_panel)
        source_details_block_layout.addWidget(source_details_host)

        return _DownloadsStateRefs(
            state_host=state_host,
            source_details_host=source_details_host,
            source_details_stack=source_details_stack,
            source_details_empty=source_details_empty,
            playlist_items_panel=playlist_items_panel,
            playlist_items_edit=playlist_items_edit,
            source_details_label=source_details_label,
        )

    @staticmethod
    def build(
        *,
        panel_stack: QStackedWidget,
        register_native_combo: Callable[[_NativeComboBox], None],
        callbacks: DownloadsViewCallbacks,
    ) -> DownloadsViewRefs:
        main_page = QWidget(panel_stack)
        main_page.setObjectName("downloadsPage")
        main_layout = QVBoxLayout(main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(18)

        downloads_state = DownloadsViewBuilder._build_downloads_state(
            main_page, callbacks
        )
        output = DownloadsViewBuilder._build_output_section(
            main_page,
            register_native_combo=register_native_combo,
            callbacks=callbacks,
        )
        run = RunSectionBuilder.build(main_page, callbacks.run)
        output.layout.insertWidget(max(0, output.layout.count() - 1), run.actions_card)

        workspace = QWidget(main_page)
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(18)
        workspace_layout.addWidget(output.section, stretch=1)
        main_layout.addWidget(workspace, stretch=1)

        main_page_index = panel_stack.addWidget(main_page)

        return DownloadsViewRefs(
            main_page=main_page,
            main_page_index=main_page_index,
            workspace_layout=workspace_layout,
            source_row=output.link_input.row,
            url_edit=output.link_input.url_edit,
            paste_button=output.link_input.paste_button,
            analyze_button=output.link_input.analyze_button,
            source_details_host=downloads_state.source_details_host,
            source_details_stack=downloads_state.source_details_stack,
            source_details_empty=downloads_state.source_details_empty,
            playlist_items_panel=downloads_state.playlist_items_panel,
            playlist_items_edit=downloads_state.playlist_items_edit,
            source_details_label=downloads_state.source_details_label,
            output_section=output.section,
            output_layout=output.layout,
            format_card=output.format_card,
            format_layout=output.format_layout,
            mode_row_layout=output.mode_row_layout,
            video_radio=output.video_radio,
            audio_radio=output.audio_radio,
            content_type_label=output.content_type_label,
            content_type_row=output.content_type_row,
            container_combo=output.container_combo,
            convert_check=output.convert_check,
            container_label=output.container_label,
            post_process_label=output.post_process_label,
            post_process_row=output.post_process_row,
            codec_combo=output.codec_combo,
            codec_label=output.codec_label,
            format_combo=output.format_combo,
            format_label=output.format_label,
            output_form_labels=output.output_form_labels,
            output_form_rows=output.output_form_rows,
            format_row=output.format_row,
            save_card=output.save_card,
            save_layout=output.save_layout,
            filename_edit=output.filename_edit,
            file_name_label=output.file_name_label,
            folder_row_layout=output.folder_row_layout,
            output_dir_edit=output.output_dir_edit,
            browse_button=output.browse_button,
            output_folder_label=output.output_folder_label,
            progress_bar=output.progress_bar,
            metrics_card=output.metrics_card,
            metrics_strip=output.metrics_strip,
            progress_label=output.progress_label,
            speed_label=output.speed_label,
            eta_label=output.eta_label,
            item_label=output.item_label,
            run=run,
        )

    @staticmethod
    def _build_output_section(
        parent: QWidget,
        *,
        register_native_combo: Callable[[_NativeComboBox], None],
        callbacks: DownloadsViewCallbacks,
    ) -> _OutputSectionRefs:
        output_section = QWidget(parent)
        output_section.setObjectName("outputSection")
        output_shell_layout = QVBoxLayout(output_section)
        output_shell_layout.setContentsMargins(0, 0, 0, 0)
        output_shell_layout.setSpacing(10)

        output_content = QWidget(output_section)
        output_shell_layout.addWidget(output_content, stretch=1)
        output_layout = QVBoxLayout(output_content)
        # Keep a one-pixel safety inset so right-edge button borders do not clip
        # against the output section boundary at compact widths.
        output_layout.setContentsMargins(0, 0, 1, 0)
        output_layout.setSpacing(OUTPUT_CARD_STACK_GAP)

        link_input = build_link_input_module(
            output_content,
            on_url_changed=callbacks.on_url_changed,
            on_fetch_formats=callbacks.on_fetch_formats,
            on_paste_url=callbacks.on_paste_url,
            on_analyze_url=callbacks.on_analyze_url,
        )
        output_layout.addWidget(link_input.row)

        format_card = QGroupBox("", output_section)
        format_card.setObjectName("formatSection")
        format_card.setMinimumWidth(0)
        format_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        format_layout = QVBoxLayout(format_card)
        format_layout.setContentsMargins(18, 18, 18, 14)
        format_layout.setSpacing(14)
        format_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        format_layout.addWidget(
            _build_section_header(format_card, "OUTPUT", compact=True)
        )

        def _handle_mode_toggle(checked: bool) -> None:
            if checked:
                callbacks.on_mode_change()

        mode_row, mode_buttons = build_segmented_rail(
            format_card,
            spec=SegmentedRailSpec(
                object_name="contentModeSegment",
                selection_frame_object_name="contentModeSelection",
                selection_rect_getter=_content_mode_selection_rect,
                size_policy=(
                    QSizePolicy.Policy.Maximum,
                    QSizePolicy.Policy.Fixed,
                ),
                layout_margins=(3, 3, 3, 3),
                layout_spacing=6,
                button_specs=(
                    ButtonSpec(
                        "Video and Audio",
                        object_name="contentModeButton",
                        checkable=True,
                        auto_exclusive=True,
                        on_toggled=_handle_mode_toggle,
                        size_policy=(
                            QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed,
                        ),
                    ),
                    ButtonSpec(
                        "Audio only",
                        object_name="contentModeButton",
                        checkable=True,
                        auto_exclusive=True,
                        on_toggled=_handle_mode_toggle,
                        size_policy=(
                            QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed,
                        ),
                    ),
                ),
            ),
        )
        mode_row_layout = mode_row.layout()
        if not isinstance(mode_row_layout, QHBoxLayout):
            raise TypeError("content mode rail must use a horizontal layout")
        video_radio, audio_radio = mode_buttons
        content_type_label = QLabel("Content type", format_card)

        container_combo = build_native_combo(
            format_card,
            register_native_combo=register_native_combo,
            config=NativeComboBoxConfig(minimum_width=190),
        )
        container_combo.currentIndexChanged.connect(callbacks.on_container_change)
        convert_check = QCheckBox("Convert WebM to MP4", format_card)
        convert_check.stateChanged.connect(
            lambda _state: callbacks.on_update_controls_state()
        )
        container_label = QLabel("Container", format_card)
        post_process_label = QLabel("Post-process", format_card)

        codec_combo = build_native_combo(
            format_card,
            register_native_combo=register_native_combo,
            config=NativeComboBoxConfig(
                minimum_width=190,
                items=(
                    ("Select codec", ""),
                    ("avc1 (H.264)", "avc1"),
                    ("av01 (AV1)", "av01"),
                ),
            ),
        )
        codec_combo.currentIndexChanged.connect(callbacks.on_codec_change)
        codec_label = QLabel("Codec", format_card)

        format_combo = build_native_combo(
            format_card,
            register_native_combo=register_native_combo,
            config=NativeComboBoxConfig(
                minimum_width=260,
                hint_text="Analyze a URL to load quality.",
            ),
        )
        format_combo.currentIndexChanged.connect(
            lambda _idx: callbacks.on_update_controls_state()
        )
        format_label = QLabel("Quality", format_card)

        output_form_labels = [
            content_type_label,
            container_label,
            codec_label,
            format_label,
        ]
        for label in output_form_labels:
            label.setObjectName("outputFormLabel")

        output_row_specs = (
            _LabeledRowSpec(
                key="content_type",
                label=content_type_label,
                field=mode_row,
                field_alignment=Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter,
            ),
            _LabeledRowSpec(
                key="container",
                label=container_label,
                field=container_combo,
            ),
            _LabeledRowSpec(
                key="post_process",
                label=post_process_label,
                field=convert_check,
                visible=False,
            ),
            _LabeledRowSpec(
                key="codec",
                label=codec_label,
                field=codec_combo,
            ),
            _LabeledRowSpec(
                key="format",
                label=format_label,
                field=format_combo,
            ),
        )
        output_row_map = _build_labeled_rows(
            format_card,
            format_layout,
            output_row_specs,
        )
        content_type_row = output_row_map["content_type"]
        post_process_row = output_row_map["post_process"]
        format_row = output_row_map["format"]
        output_form_rows = [output_row_map[spec.key] for spec in output_row_specs]

        save_card = QWidget(format_card)
        save_card.setObjectName("saveSection")
        save_card.setMinimumWidth(0)
        save_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        save_layout = QVBoxLayout(save_card)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.setSpacing(format_layout.spacing())
        save_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        filename_edit = QLineEdit(save_card)
        filename_edit.setPlaceholderText("Optional...")
        file_name_label = QLabel("File name", save_card)
        file_name_label.setObjectName("outputFormLabel")

        folder_row = QWidget(save_card)
        folder_row.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        folder_row_layout = QVBoxLayout(folder_row)
        folder_row_layout.setContentsMargins(0, 0, 0, 0)
        folder_row_layout.setSpacing(12)
        folder_row_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        output_dir_edit = QLineEdit(str(Path.home() / "Downloads"), folder_row)
        output_dir_edit.setReadOnly(True)
        output_dir_edit.setMinimumWidth(0)
        browse_button = QPushButton("Browse...", folder_row)
        browse_button.setObjectName("compactButton")
        browse_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        browse_button.clicked.connect(callbacks.on_pick_folder)
        folder_row_layout.addWidget(output_dir_edit)
        folder_row_layout.addWidget(browse_button)
        output_folder_label = QLabel("Folder", save_card)
        output_folder_label.setObjectName("outputFormLabel")

        output_form_labels.extend([file_name_label, output_folder_label])
        save_row_specs = (
            _LabeledRowSpec(
                key="file_name",
                label=file_name_label,
                field=filename_edit,
            ),
            _LabeledRowSpec(
                key="output_folder",
                label=output_folder_label,
                field=folder_row,
            ),
        )
        save_row_map = _build_labeled_rows(
            save_card,
            save_layout,
            save_row_specs,
        )
        output_form_rows.extend(save_row_map[spec.key] for spec in save_row_specs)

        format_layout.addWidget(save_card)

        metrics_card = QFrame(output_content)
        metrics_card.setObjectName("progressCard")
        metrics_card_layout = QVBoxLayout(metrics_card)
        metrics_card_layout.setContentsMargins(16, 14, 16, 16)
        metrics_card_layout.setSpacing(12)

        progress_bar = QProgressBar(metrics_card)
        progress_bar.setRange(0, 1000)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)

        metrics_details = QWidget(metrics_card)
        metrics_details_layout = QHBoxLayout(metrics_details)
        metrics_details_layout.setContentsMargins(0, 0, 0, 0)
        metrics_details_layout.setSpacing(20)

        metrics_strip = QFrame(metrics_details)
        metrics_strip.setObjectName("metricsStrip")
        metrics_layout = QHBoxLayout(metrics_strip)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(18)
        progress_label = QLabel("Progress: -", metrics_strip)
        progress_label.setObjectName("metricInline")
        progress_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        speed_label = QLabel("Speed: -", metrics_strip)
        speed_label.setObjectName("metricInline")
        speed_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        eta_label = QLabel("ETA: -", metrics_strip)
        eta_label.setObjectName("metricInline")
        eta_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        item_label = QLabel("Item: -", metrics_strip)
        item_label.setObjectName("metricInlineItem")
        item_label.setMinimumWidth(0)
        item_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        metrics_layout.addWidget(progress_label)
        metrics_layout.addWidget(speed_label)
        metrics_layout.addWidget(eta_label)
        metrics_layout.addWidget(item_label, stretch=1)
        metrics_details_layout.addWidget(metrics_strip, stretch=1)
        metrics_card_layout.addWidget(progress_bar)
        metrics_card_layout.addWidget(metrics_details)
        output_layout.addWidget(format_card)
        output_layout.addWidget(metrics_card)
        output_layout.addStretch(1)
        return _OutputSectionRefs(
            section=output_section,
            layout=output_layout,
            link_input=link_input,
            format_card=format_card,
            format_layout=format_layout,
            mode_row_layout=mode_row_layout,
            video_radio=video_radio,
            audio_radio=audio_radio,
            content_type_label=content_type_label,
            content_type_row=content_type_row,
            container_combo=container_combo,
            convert_check=convert_check,
            container_label=container_label,
            post_process_label=post_process_label,
            post_process_row=post_process_row,
            codec_combo=codec_combo,
            codec_label=codec_label,
            format_combo=format_combo,
            format_label=format_label,
            output_form_labels=output_form_labels,
            output_form_rows=output_form_rows,
            format_row=format_row,
            save_card=save_card,
            save_layout=save_layout,
            filename_edit=filename_edit,
            file_name_label=file_name_label,
            folder_row_layout=folder_row_layout,
            output_dir_edit=output_dir_edit,
            browse_button=browse_button,
            output_folder_label=output_folder_label,
            progress_bar=progress_bar,
            metrics_card=metrics_card,
            metrics_strip=metrics_strip,
            progress_label=progress_label,
            speed_label=speed_label,
            eta_label=eta_label,
            item_label=item_label,
        )


class MainUiBuilder:
    @staticmethod
    def build(
        *,
        window: QWidget,
        register_native_combo: Callable[[_NativeComboBox], None],
        callbacks: DownloadsViewCallbacks,
    ) -> UiRefs:
        root = QWidget(window)
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 18, 22, 18)
        root_layout.setSpacing(14)

        top_bar = TopBarBuilder.build(root)
        root_layout.addWidget(top_bar.header)

        panel_stack = QStackedWidget(window)
        panel_stack.setObjectName("panelStack")
        root_layout.addWidget(panel_stack, stretch=1)

        mixed_url_overlay = QFrame(root)
        mixed_url_overlay.setObjectName("mixedUrlOverlay")
        mixed_url_overlay_layout = QVBoxLayout(mixed_url_overlay)
        mixed_url_overlay_layout.setContentsMargins(18, 16, 18, 16)
        mixed_url_overlay_layout.setSpacing(0)
        mixed_url_overlay_layout.addStretch(1)

        mixed_url_alert = QFrame(mixed_url_overlay)
        mixed_url_alert.setObjectName("mixedUrlAlert")
        mixed_shadow = QGraphicsDropShadowEffect(mixed_url_alert)
        mixed_shadow.setBlurRadius(24)
        mixed_shadow.setOffset(0, 6)
        mixed_shadow.setColor(QColor(15, 91, 81, 68))
        mixed_url_alert.setGraphicsEffect(mixed_shadow)
        mixed_alert_layout = QVBoxLayout(mixed_url_alert)
        mixed_alert_layout.setContentsMargins(12, 10, 12, 14)
        mixed_alert_layout.setSpacing(8)
        mixed_url_alert_label = QLabel(
            "Download this URL as a single video or as a playlist?",
            mixed_url_alert,
        )
        mixed_url_alert_label.setObjectName("mixedUrlAlertTitle")
        mixed_url_alert_label.setWordWrap(True)
        mixed_alert_layout.addWidget(mixed_url_alert_label)
        mixed_buttons = QWidget(mixed_url_alert)
        mixed_buttons_layout = QHBoxLayout(mixed_buttons)
        mixed_buttons_layout.setContentsMargins(0, 0, 0, 2)
        mixed_buttons_layout.setSpacing(4)
        use_single_video_url_button = build_button(
            mixed_buttons,
            spec=ButtonSpec(
                text="Single video",
                on_click=callbacks.on_use_single_video_url,
            ),
        )
        use_playlist_url_button = build_button(
            mixed_buttons,
            spec=ButtonSpec(
                text="Playlist",
                on_click=callbacks.on_use_playlist_url,
            ),
        )
        mixed_buttons_layout.addWidget(use_single_video_url_button)
        mixed_buttons_layout.addWidget(use_playlist_url_button)
        mixed_buttons_layout.addStretch(1)
        mixed_alert_layout.addWidget(mixed_buttons)
        mixed_url_overlay_layout.addWidget(
            mixed_url_alert,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        mixed_url_overlay_layout.addStretch(1)
        mixed_url_overlay.hide()

        source_toast = build_source_feedback_toast(root)

        downloads = DownloadsViewBuilder.build(
            panel_stack=panel_stack,
            register_native_combo=register_native_combo,
            callbacks=callbacks,
        )

        return UiRefs(
            root=root,
            panel_stack=panel_stack,
            top_bar=top_bar,
            mixed_url=MixedUrlRefs(
                overlay=mixed_url_overlay,
                overlay_layout=mixed_url_overlay_layout,
                alert=mixed_url_alert,
                alert_label=mixed_url_alert_label,
                buttons_layout=mixed_buttons_layout,
                use_single_video_url_button=use_single_video_url_button,
                use_playlist_url_button=use_playlist_url_button,
            ),
            source_toast=source_toast,
            downloads=downloads,
        )
