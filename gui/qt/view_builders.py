from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRect, Qt
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
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .constants import OUTPUT_CARD_STACK_GAP, RUN_SECTION_CARD_GAP
from .link_input import LinkInputRefs, build_link_input_module
from .widgets import (
    AnimatedSegmentedRail,
    QueueEmptyStateWidget,
    StableStackedWidget,
    _NativeComboBox,
)


@dataclass(frozen=True)
class TopBarRefs:
    header: QWidget
    top_actions: QWidget
    classic_actions: QWidget
    downloads_button: QPushButton
    session_button: QPushButton
    queue_button: QPushButton
    history_button: QPushButton
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
class SourceToastRefs:
    card: QFrame
    title_label: QLabel
    message_label: QLabel
    dismiss_button: QPushButton


@dataclass(frozen=True)
class RunSectionRefs:
    section: QGroupBox
    activity_card: QFrame
    actions_card: QFrame
    actions_shell_layout: QVBoxLayout
    actions_layout: QGridLayout
    stage_hint_label: QLabel
    session_title_label: QLabel
    stats_grid: QWidget
    status_value: QLabel
    start_button: QPushButton
    add_queue_button: QPushButton
    start_queue_button: QPushButton
    cancel_button: QPushButton
    download_result_card: QFrame
    download_result_title: QLabel
    download_result_path: QLabel
    session_completed_value: QLabel
    session_failed_value: QLabel
    session_success_rate_value: QLabel
    session_remaining_value: QLabel
    session_speed_value: QLabel
    session_peak_speed_value: QLabel
    session_downloaded_value: QLabel
    session_elapsed_value: QLabel
    open_last_output_folder_button: QPushButton
    copy_output_path_button: QPushButton


@dataclass(frozen=True)
class DownloadsViewRefs:
    main_page: QWidget
    main_page_index: int
    workspace_layout: QHBoxLayout
    source_view_stack: QStackedWidget
    queue_view_index: int
    history_view_index: int
    queue_view_button: QPushButton
    history_view_button: QPushButton
    queue_workspace_stack: QStackedWidget
    queue_workspace_preview_index: int
    queue_workspace_summary_index: int
    queue_summary_list: QListWidget
    queue_summary_empty: QueueEmptyStateWidget
    history_summary_list: QListWidget
    history_summary_empty: QLabel
    source_row: QWidget
    url_edit: QLineEdit
    paste_button: QPushButton
    analyze_button: QPushButton
    source_details_host: QWidget
    source_details_stack: QStackedWidget
    source_details_empty: QWidget
    playlist_items_panel: QWidget
    playlist_items_edit: QLineEdit
    source_preview_card: QFrame
    source_preview_badge: QLabel
    preview_value: QLabel
    preview_title_label: QLabel
    source_preview_placeholder: QLabel
    source_preview_subtitle: QLabel
    source_preview_detail_one: QLabel
    source_preview_detail_two: QLabel
    source_preview_detail_three: QLabel
    source_details_label: QLabel
    source_feedback_label: QLabel
    output_section: QWidget
    output_stage_hint_label: QLabel
    output_layout: QVBoxLayout
    format_card: QGroupBox
    format_layout: QVBoxLayout
    mode_row_layout: QHBoxLayout
    video_radio: QRadioButton
    audio_radio: QRadioButton
    content_type_label: QLabel
    container_combo: _NativeComboBox
    convert_check: QCheckBox
    container_label: QLabel
    post_process_label: QLabel
    codec_combo: _NativeComboBox
    codec_label: QLabel
    format_combo: _NativeComboBox
    format_label: QLabel
    output_form_labels: list[QLabel]
    output_form_rows: list[QWidget]
    save_card: QWidget
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QVBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel
    progress_bar: QProgressBar
    ready_summary_label: QLabel
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
    on_start_queue: Callable[[], None]
    on_cancel: Callable[[], None]
    on_open_last_output_folder: Callable[[], None]
    on_copy_output_path: Callable[[], None]


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
class _SourceSectionRefs:
    section: QGroupBox
    source_view_stack: QStackedWidget
    queue_view_index: int
    history_view_index: int
    queue_view_button: QPushButton
    history_view_button: QPushButton
    queue_workspace_stack: QStackedWidget
    queue_workspace_preview_index: int
    queue_workspace_summary_index: int
    queue_summary_list: QListWidget
    queue_summary_empty: QueueEmptyStateWidget
    history_summary_list: QListWidget
    history_summary_empty: QLabel
    source_details_host: QWidget
    source_details_stack: QStackedWidget
    source_details_empty: QWidget
    playlist_items_panel: QWidget
    playlist_items_edit: QLineEdit
    source_preview_card: QFrame
    source_preview_badge: QLabel
    preview_value: QLabel
    preview_title_label: QLabel
    source_preview_placeholder: QLabel
    source_preview_subtitle: QLabel
    source_preview_detail_one: QLabel
    source_preview_detail_two: QLabel
    source_preview_detail_three: QLabel
    source_details_label: QLabel
    source_feedback_label: QLabel


@dataclass(frozen=True)
class _OutputSectionRefs:
    section: QGroupBox
    stage_hint_label: QLabel
    layout: QVBoxLayout
    link_input: LinkInputRefs
    format_card: QGroupBox
    format_layout: QVBoxLayout
    mode_row_layout: QHBoxLayout
    video_radio: QRadioButton
    audio_radio: QRadioButton
    content_type_label: QLabel
    container_combo: _NativeComboBox
    convert_check: QCheckBox
    container_label: QLabel
    post_process_label: QLabel
    codec_combo: _NativeComboBox
    codec_label: QLabel
    format_combo: _NativeComboBox
    format_label: QLabel
    output_form_labels: list[QLabel]
    output_form_rows: list[QWidget]
    save_card: QWidget
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QVBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel
    progress_bar: QProgressBar
    ready_summary_label: QLabel
    metrics_card: QFrame
    metrics_strip: QFrame
    progress_label: QLabel
    speed_label: QLabel
    eta_label: QLabel
    item_label: QLabel


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
        top_actions_layout.setContentsMargins(0, 0, 0, 0)
        top_actions_layout.setSpacing(8)

        classic_actions = AnimatedSegmentedRail(top_actions)
        classic_actions.setObjectName("topNavRail")
        classic_actions.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        classic_layout = classic_actions.layout()
        if isinstance(classic_layout, QHBoxLayout):
            classic_layout.setContentsMargins(4, 4, 4, 4)
            classic_layout.setSpacing(4)
        downloads_button = QPushButton("Downloads", classic_actions)
        session_button = QPushButton("Session", classic_actions)
        queue_button = QPushButton("Queue", classic_actions)
        history_button = QPushButton("History", classic_actions)
        logs_button = QPushButton("Logs", classic_actions)
        settings_button = QPushButton("Settings", classic_actions)
        for button in (
            downloads_button,
            session_button,
            queue_button,
            history_button,
            logs_button,
            settings_button,
        ):
            button.setCheckable(True)
            button.setObjectName("topNavButton")
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            classic_actions.add_button(button)

        top_actions_layout.addWidget(
            classic_actions,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        header_layout.addWidget(top_actions, stretch=1)
        return TopBarRefs(
            header=header,
            top_actions=top_actions,
            classic_actions=classic_actions,
            downloads_button=downloads_button,
            session_button=session_button,
            queue_button=queue_button,
            history_button=history_button,
            logs_button=logs_button,
            settings_button=settings_button,
        )


class RunSectionBuilder:
    @staticmethod
    def build(parent: QWidget, callbacks: RunSectionCallbacks) -> RunSectionRefs:
        run = QGroupBox("", parent)
        run.setObjectName("runSection")
        run_layout = QHBoxLayout(run)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(RUN_SECTION_CARD_GAP)

        activity_card = QFrame(run)
        activity_card.setObjectName("runActivityCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 16, 16, 16)
        activity_layout.setSpacing(12)

        status_value = QLabel("Idle", activity_card)
        status_value.setObjectName("statusLine")
        status_value.setVisible(False)

        stage_hint_label = QLabel(
            "Analyze a URL and choose a format to enable download actions.",
            activity_card,
        )
        stage_hint_label.setObjectName("sectionStageHint")
        stage_hint_label.setWordWrap(True)
        stage_hint_label.hide()
        activity_layout.addWidget(stage_hint_label)
        activity_layout.addWidget(status_value)
        session_title_label = QLabel("SESSION", activity_card)
        session_title_label.setObjectName("runSectionLabel")
        activity_layout.addWidget(session_title_label)

        stats_grid = QWidget(activity_card)
        stats_grid.setObjectName("runStatsGrid")
        stats_layout = QGridLayout(stats_grid)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setHorizontalSpacing(10)
        stats_layout.setVerticalSpacing(10)
        stats_layout.setColumnStretch(0, 1)
        stats_layout.setColumnStretch(1, 1)

        def build_stat_card(title: str, value: str) -> tuple[QFrame, QLabel]:
            card = QFrame(stats_grid)
            card.setObjectName("sessionMetricCard")
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(4)
            card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            value_label = QLabel(value, card)
            value_label.setObjectName("sessionMetricValue")
            value_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            title_label = QLabel(title, card)
            title_label.setObjectName("sessionMetricLabel")
            title_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            card_layout.addWidget(value_label)
            card_layout.addWidget(title_label)
            return card, value_label

        completed_card, session_completed_value = build_stat_card("Completed", "0")
        failed_card, session_failed_value = build_stat_card("Failed", "0")
        success_rate_card, session_success_rate_value = build_stat_card(
            "Success rate", "-"
        )
        remaining_card, session_remaining_value = build_stat_card("Remaining", "0")
        speed_card, session_speed_value = build_stat_card("Avg speed", "-")
        peak_speed_card, session_peak_speed_value = build_stat_card("Peak speed", "-")
        downloaded_card, session_downloaded_value = build_stat_card(
            "Downloaded", "0 B"
        )
        elapsed_card, session_elapsed_value = build_stat_card("Elapsed", "-")
        stats_layout.addWidget(completed_card, 0, 0)
        stats_layout.addWidget(failed_card, 0, 1)
        stats_layout.addWidget(success_rate_card, 1, 0)
        stats_layout.addWidget(remaining_card, 1, 1)
        stats_layout.addWidget(speed_card, 2, 0)
        stats_layout.addWidget(peak_speed_card, 2, 1)
        stats_layout.addWidget(downloaded_card, 3, 0)
        stats_layout.addWidget(elapsed_card, 3, 1)
        activity_layout.addWidget(stats_grid)

        download_result_card = QFrame(activity_card)
        download_result_card.setObjectName("downloadResultCard")
        download_result_card.setProperty("state", "empty")
        download_result_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        result_layout = QHBoxLayout(download_result_card)
        result_layout.setContentsMargins(14, 12, 14, 12)
        result_layout.setSpacing(8)

        latest_copy = QWidget(download_result_card)
        latest_copy_layout = QVBoxLayout(latest_copy)
        latest_copy_layout.setContentsMargins(0, 0, 0, 0)
        latest_copy_layout.setSpacing(4)
        download_result_title = QLabel("No completed download yet.", latest_copy)
        download_result_title.setObjectName("downloadResultTitle")
        download_result_path = QLabel(
            "Files will appear here after a download finishes.",
            latest_copy,
        )
        download_result_path.setObjectName("downloadResultPath")
        download_result_path.setWordWrap(False)
        download_result_path.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        download_result_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        latest_copy_layout.addWidget(download_result_title)
        latest_copy_layout.addWidget(download_result_path)

        result_actions = QWidget(download_result_card)
        result_actions.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        result_actions_layout = QHBoxLayout(result_actions)
        result_actions_layout.setContentsMargins(0, 0, 0, 0)
        result_actions_layout.setSpacing(8)
        open_last_output_folder_button = QPushButton("Open folder", result_actions)
        open_last_output_folder_button.clicked.connect(
            callbacks.on_open_last_output_folder
        )
        copy_output_path_button = QPushButton("Copy path", result_actions)
        copy_output_path_button.clicked.connect(callbacks.on_copy_output_path)
        result_actions_layout.addWidget(open_last_output_folder_button)
        result_actions_layout.addWidget(copy_output_path_button)
        result_layout.addWidget(latest_copy, stretch=1)
        result_layout.addWidget(result_actions)
        activity_layout.addWidget(download_result_card)

        actions_card = QFrame(run)
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

        start_button = QPushButton("Download", buttons_host)
        start_button.setObjectName("primaryActionButton")
        start_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        start_button.clicked.connect(callbacks.on_start)
        add_queue_button = QPushButton("Add to queue", buttons_host)
        add_queue_button.setObjectName("secondaryActionButton")
        add_queue_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        add_queue_button.clicked.connect(callbacks.on_add_to_queue)
        start_queue_button = QPushButton("Download queue", buttons_host)
        start_queue_button.setObjectName("secondaryActionButton")
        start_queue_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        start_queue_button.clicked.connect(callbacks.on_start_queue)
        start_queue_button.hide()
        cancel_button = QPushButton("Cancel", buttons_host)
        cancel_button.setObjectName("dangerActionButton")
        cancel_button.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        cancel_button.clicked.connect(callbacks.on_cancel)

        buttons_layout.addWidget(start_button, 0, 0)
        buttons_layout.addWidget(add_queue_button, 0, 1)
        buttons_layout.addWidget(cancel_button, 0, 2)
        buttons_layout.setColumnStretch(0, 1)
        buttons_layout.setColumnStretch(1, 1)
        buttons_layout.setColumnStretch(2, 1)
        run_layout.addWidget(activity_card, stretch=13)
        run_layout.addWidget(actions_card, stretch=7)

        return RunSectionRefs(
            section=run,
            activity_card=activity_card,
            actions_card=actions_card,
            actions_shell_layout=buttons_shell_layout,
            actions_layout=buttons_layout,
            stage_hint_label=stage_hint_label,
            session_title_label=session_title_label,
            stats_grid=stats_grid,
            status_value=status_value,
            start_button=start_button,
            add_queue_button=add_queue_button,
            start_queue_button=start_queue_button,
            cancel_button=cancel_button,
            download_result_card=download_result_card,
            download_result_title=download_result_title,
            download_result_path=download_result_path,
            session_completed_value=session_completed_value,
            session_failed_value=session_failed_value,
            session_success_rate_value=session_success_rate_value,
            session_remaining_value=session_remaining_value,
            session_speed_value=session_speed_value,
            session_peak_speed_value=session_peak_speed_value,
            session_downloaded_value=session_downloaded_value,
            session_elapsed_value=session_elapsed_value,
            open_last_output_folder_button=open_last_output_folder_button,
            copy_output_path_button=copy_output_path_button,
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


def _workspace_tab_selection_rect(button: QPushButton) -> QRect:
    rect = button.geometry()
    underline_height = 3
    return QRect(
        rect.x(),
        rect.y() + max(0, rect.height() - underline_height),
        rect.width(),
        underline_height,
    )


def _add_labeled_row(
    parent: QWidget,
    layout: QVBoxLayout,
    label: QLabel,
    field: QWidget,
    *,
    field_spacing: int = 20,
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
    field_host_layout.addWidget(field)

    row_layout.addWidget(label)
    row_layout.addWidget(field_host, stretch=1)
    block_layout.addWidget(row)
    layout.addWidget(block)
    return block


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
    def _build_hidden_source_state(
        parent: QWidget,
        callbacks: DownloadsViewCallbacks,
    ) -> _SourceSectionRefs:
        hidden_host = QWidget(parent)
        hidden_host.setObjectName("legacySourceStateHost")
        hidden_host.hide()

        source = DownloadsViewBuilder._build_source_section(hidden_host, callbacks)
        source.section.hide()
        return source

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

        source = DownloadsViewBuilder._build_hidden_source_state(main_page, callbacks)
        output = DownloadsViewBuilder._build_output_section(
            main_page,
            register_native_combo=register_native_combo,
            callbacks=callbacks,
        )
        run = RunSectionBuilder.build(main_page, callbacks.run)
        run_layout = run.section.layout()
        if isinstance(run_layout, QLayout):
            run_layout.removeWidget(run.actions_card)
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
            source_view_stack=source.source_view_stack,
            queue_view_index=source.queue_view_index,
            history_view_index=source.history_view_index,
            queue_view_button=source.queue_view_button,
            history_view_button=source.history_view_button,
            queue_workspace_stack=source.queue_workspace_stack,
            queue_workspace_preview_index=source.queue_workspace_preview_index,
            queue_workspace_summary_index=source.queue_workspace_summary_index,
            queue_summary_list=source.queue_summary_list,
            queue_summary_empty=source.queue_summary_empty,
            history_summary_list=source.history_summary_list,
            history_summary_empty=source.history_summary_empty,
            source_row=output.link_input.row,
            url_edit=output.link_input.url_edit,
            paste_button=output.link_input.paste_button,
            analyze_button=output.link_input.analyze_button,
            source_details_host=source.source_details_host,
            source_details_stack=source.source_details_stack,
            source_details_empty=source.source_details_empty,
            playlist_items_panel=source.playlist_items_panel,
            playlist_items_edit=source.playlist_items_edit,
            source_preview_card=source.source_preview_card,
            source_preview_badge=source.source_preview_badge,
            preview_value=source.preview_value,
            preview_title_label=source.preview_title_label,
            source_preview_placeholder=source.source_preview_placeholder,
            source_preview_subtitle=source.source_preview_subtitle,
            source_preview_detail_one=source.source_preview_detail_one,
            source_preview_detail_two=source.source_preview_detail_two,
            source_preview_detail_three=source.source_preview_detail_three,
            source_details_label=source.source_details_label,
            source_feedback_label=source.source_feedback_label,
            output_section=output.section,
            output_stage_hint_label=output.stage_hint_label,
            output_layout=output.layout,
            format_card=output.format_card,
            format_layout=output.format_layout,
            mode_row_layout=output.mode_row_layout,
            video_radio=output.video_radio,
            audio_radio=output.audio_radio,
            content_type_label=output.content_type_label,
            container_combo=output.container_combo,
            convert_check=output.convert_check,
            container_label=output.container_label,
            post_process_label=output.post_process_label,
            codec_combo=output.codec_combo,
            codec_label=output.codec_label,
            format_combo=output.format_combo,
            format_label=output.format_label,
            output_form_labels=output.output_form_labels,
            output_form_rows=output.output_form_rows,
            save_card=output.save_card,
            save_layout=output.save_layout,
            filename_edit=output.filename_edit,
            file_name_label=output.file_name_label,
            folder_row_layout=output.folder_row_layout,
            output_dir_edit=output.output_dir_edit,
            browse_button=output.browse_button,
            output_folder_label=output.output_folder_label,
            progress_bar=output.progress_bar,
            ready_summary_label=output.ready_summary_label,
            metrics_card=output.metrics_card,
            metrics_strip=output.metrics_strip,
            progress_label=output.progress_label,
            speed_label=output.speed_label,
            eta_label=output.eta_label,
            item_label=output.item_label,
            run=run,
        )

    @staticmethod
    def _build_source_section(
        parent: QWidget,
        callbacks: DownloadsViewCallbacks,
    ) -> _SourceSectionRefs:
        source = QGroupBox("", parent)
        source.setObjectName("sourceSection")
        source_shell_layout = QVBoxLayout(source)
        source_shell_layout.setContentsMargins(0, 0, 0, 0)
        source_shell_layout.setSpacing(0)

        source_content = QFrame(source)
        source_content.setObjectName("sourceContentPanel")
        source_shell_layout.addWidget(source_content, stretch=1)
        source_layout = QVBoxLayout(source_content)
        source_layout.setContentsMargins(16, 16, 16, 16)
        source_layout.setSpacing(12)

        source_feedback_label = QLabel(
            "Paste a video or playlist URL, then analyze it to load formats.",
            source_content,
        )
        source_feedback_label.setObjectName("sourceFeedbackLabel")
        source_feedback_label.setWordWrap(True)
        source_feedback_label.setProperty("tone", "neutral")
        source_layout.addWidget(source_feedback_label)

        divider = QFrame(source_content)
        divider.setObjectName("sectionDivider")
        divider.setFixedHeight(1)
        source_layout.addWidget(divider)

        tab_bar = AnimatedSegmentedRail(
            source_content,
            selection_frame_object_name="workspaceTabUnderline",
            selection_rect_getter=_workspace_tab_selection_rect,
        )
        tab_bar.setObjectName("workspaceTabBar")
        tab_bar_layout = tab_bar.layout()
        if isinstance(tab_bar_layout, QHBoxLayout):
            tab_bar_layout.setContentsMargins(0, 0, 0, 0)
            tab_bar_layout.setSpacing(18)
        queue_view_button = QPushButton("Queue", tab_bar)
        history_view_button = QPushButton("History", tab_bar)
        for button in (
            queue_view_button,
            history_view_button,
        ):
            button.setCheckable(True)
            button.setObjectName("workspaceTabButton")
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            tab_bar.add_button(button)
        if isinstance(tab_bar_layout, QHBoxLayout):
            tab_bar_layout.addStretch(1)
        source_layout.addWidget(tab_bar)
        tab_bar.hide()

        source_view_stack = StableStackedWidget(source_content)
        source_view_stack.setObjectName("sourceViewStack")
        source_layout.addWidget(source_view_stack, stretch=1)

        queue_page = QWidget(source_view_stack)
        queue_page_layout = QVBoxLayout(queue_page)
        queue_page_layout.setContentsMargins(0, 0, 0, 0)
        queue_page_layout.setSpacing(10)
        queue_workspace_stack = QStackedWidget(queue_page)
        queue_workspace_stack.setObjectName("queueWorkspaceStack")
        queue_page_layout.addWidget(queue_workspace_stack, stretch=1)

        preview_page = QWidget(queue_workspace_stack)
        current_layout = QVBoxLayout(preview_page)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.setSpacing(10)

        source_preview_card = QFrame(preview_page)
        source_preview_card.setObjectName("sourcePreviewCard")
        source_preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_layout = QHBoxLayout(source_preview_card)
        source_preview_layout.setContentsMargins(7, 10, 7, 10)
        source_preview_layout.setSpacing(10)

        source_preview_badge = QLabel("URL", source_preview_card)
        source_preview_badge.setObjectName("sourcePreviewBadge")
        source_preview_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_preview_badge.setFixedSize(54, 54)
        source_preview_badge.setVisible(False)
        source_preview_layout.addWidget(
            source_preview_badge,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        source_preview_copy = QWidget(source_preview_card)
        source_preview_copy.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_copy.setMinimumWidth(0)
        source_preview_copy_layout = QVBoxLayout(source_preview_copy)
        source_preview_copy_layout.setContentsMargins(0, 0, 0, 0)
        source_preview_copy_layout.setSpacing(4)

        preview_title_label = QLabel("Source preview", source_preview_copy)
        preview_title_label.setObjectName("sourcePreviewEyebrow")
        preview_title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        preview_title_label.setMinimumWidth(0)
        preview_value = QLabel("-", source_preview_copy)
        preview_value.setObjectName("sourcePreviewTitle")
        preview_value.setWordWrap(False)
        preview_value.setMargin(0)
        preview_value.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        preview_value.setMinimumWidth(0)

        source_preview_placeholder = QLabel(
            "Analyze a URL to load source details.",
            source_preview_copy,
        )
        source_preview_placeholder.setObjectName("sourcePreviewPlaceholder")
        source_preview_placeholder.setWordWrap(False)
        source_preview_placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_placeholder.setMinimumWidth(0)

        source_preview_subtitle = QLabel(
            "Title, creator, and duration will appear here.",
            source_preview_copy,
        )
        source_preview_subtitle.setObjectName("sourcePreviewSubtitle")
        source_preview_subtitle.setWordWrap(False)
        source_preview_subtitle.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_subtitle.setMinimumWidth(0)

        source_preview_details = QWidget(source_preview_copy)
        source_preview_details.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_details.setMinimumWidth(0)
        source_preview_details_layout = QHBoxLayout(source_preview_details)
        source_preview_details_layout.setContentsMargins(0, 1, 0, 0)
        source_preview_details_layout.setSpacing(4)
        source_preview_detail_one = QLabel("", source_preview_details)
        source_preview_detail_one.setObjectName("sourcePreviewDetailChip")
        source_preview_detail_two = QLabel("", source_preview_details)
        source_preview_detail_two.setObjectName("sourcePreviewDetailChip")
        source_preview_detail_three = QLabel("", source_preview_details)
        source_preview_detail_three.setObjectName("sourcePreviewDetailChip")
        for chip in (
            source_preview_detail_one,
            source_preview_detail_two,
            source_preview_detail_three,
        ):
            chip.setMinimumWidth(0)
            chip.setVisible(bool(chip.text()))
            source_preview_details_layout.addWidget(chip)
        source_preview_details_layout.addStretch(1)

        source_preview_copy_layout.addWidget(preview_title_label)
        source_preview_copy_layout.addWidget(preview_value)
        source_preview_copy_layout.addWidget(source_preview_placeholder)
        source_preview_copy_layout.addWidget(source_preview_subtitle)
        source_preview_copy_layout.addWidget(source_preview_details)
        source_preview_layout.addWidget(source_preview_copy, stretch=1)
        source_preview_card.hide()

        source_details_block = QWidget(preview_page)
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
        current_layout.addWidget(source_details_block)
        current_layout.addStretch(1)
        queue_workspace_preview_index = queue_workspace_stack.addWidget(preview_page)

        queue_summary_page = QWidget(queue_workspace_stack)
        queue_summary_page_layout = QVBoxLayout(queue_summary_page)
        queue_summary_page_layout.setContentsMargins(0, 0, 0, 0)
        queue_summary_page_layout.setSpacing(10)
        queue_summary_empty = QueueEmptyStateWidget(queue_summary_page)
        queue_summary_list = QListWidget(queue_summary_page)
        queue_summary_list.setObjectName("workspaceList")
        queue_summary_list.setSpacing(10)
        queue_summary_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        queue_summary_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        queue_summary_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        queue_summary_list.setWrapping(False)
        queue_summary_list.setVisible(False)
        queue_summary_page_layout.addWidget(queue_summary_empty, stretch=1)
        queue_summary_page_layout.addWidget(queue_summary_list, stretch=1)
        queue_workspace_summary_index = queue_workspace_stack.addWidget(
            queue_summary_page
        )
        queue_workspace_stack.setCurrentIndex(queue_workspace_summary_index)
        queue_view_index = source_view_stack.addWidget(queue_page)

        history_page = QWidget(source_view_stack)
        history_page_layout = QVBoxLayout(history_page)
        history_page_layout.setContentsMargins(0, 0, 0, 0)
        history_page_layout.setSpacing(10)
        history_summary_empty = QLabel(
            "History will appear here after downloads finish.",
            history_page,
        )
        history_summary_empty.setObjectName("workspaceEmptyLabel")
        history_summary_empty.setWordWrap(True)
        history_summary_list = QListWidget(history_page)
        history_summary_list.setObjectName("workspaceList")
        history_summary_list.setSpacing(10)
        history_summary_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        history_summary_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        history_summary_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        history_summary_list.setWrapping(False)
        history_page_layout.addWidget(history_summary_empty)
        history_page_layout.addWidget(history_summary_list, stretch=1)
        history_view_index = source_view_stack.addWidget(history_page)
        return _SourceSectionRefs(
            section=source,
            source_view_stack=source_view_stack,
            queue_view_index=queue_view_index,
            history_view_index=history_view_index,
            queue_view_button=queue_view_button,
            history_view_button=history_view_button,
            queue_workspace_stack=queue_workspace_stack,
            queue_workspace_preview_index=queue_workspace_preview_index,
            queue_workspace_summary_index=queue_workspace_summary_index,
            queue_summary_list=queue_summary_list,
            queue_summary_empty=queue_summary_empty,
            history_summary_list=history_summary_list,
            history_summary_empty=history_summary_empty,
            source_details_host=source_details_host,
            source_details_stack=source_details_stack,
            source_details_empty=source_details_empty,
            playlist_items_panel=playlist_items_panel,
            playlist_items_edit=playlist_items_edit,
            source_preview_card=source_preview_card,
            source_preview_badge=source_preview_badge,
            preview_value=preview_value,
            preview_title_label=preview_title_label,
            source_preview_placeholder=source_preview_placeholder,
            source_preview_subtitle=source_preview_subtitle,
            source_preview_detail_one=source_preview_detail_one,
            source_preview_detail_two=source_preview_detail_two,
            source_preview_detail_three=source_preview_detail_three,
            source_details_label=source_details_label,
            source_feedback_label=source_feedback_label,
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

        stage_hint_label = QLabel(
            "Analyze a URL to unlock container, codec, and quality controls.",
            output_section,
        )
        stage_hint_label.setObjectName("sectionStageHint")
        stage_hint_label.setWordWrap(True)
        output_shell_layout.addWidget(stage_hint_label)

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
        format_layout.setContentsMargins(18, 18, 18, 18)
        format_layout.setSpacing(14)
        format_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        format_layout.addWidget(
            _build_section_header(format_card, "OUTPUT", compact=True)
        )

        mode_row = AnimatedSegmentedRail(
            format_card,
            selection_frame_object_name="contentModeSelection",
        )
        mode_row.setObjectName("contentModeSegment")
        mode_row.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        mode_row_layout = mode_row.layout()
        if isinstance(mode_row_layout, QHBoxLayout):
            mode_row_layout.setContentsMargins(6, 6, 6, 6)
            mode_row_layout.setSpacing(6)
        video_radio = QRadioButton("Video and Audio", mode_row)
        audio_radio = QRadioButton("Audio only", mode_row)
        video_radio.setObjectName("contentModeButton")
        audio_radio.setObjectName("contentModeButton")
        video_radio.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        audio_radio.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        def _handle_mode_toggle(checked: bool) -> None:
            if checked:
                callbacks.on_mode_change()

        video_radio.toggled.connect(_handle_mode_toggle)
        audio_radio.toggled.connect(_handle_mode_toggle)
        mode_row.add_button(video_radio, stretch=1)
        mode_row.add_button(audio_radio, stretch=1)
        content_type_label = QLabel("Content type", format_card)

        container_row = QWidget(format_card)
        container_row_layout = QVBoxLayout(container_row)
        container_row_layout.setContentsMargins(0, 0, 0, 0)
        container_row_layout.setSpacing(8)
        container_combo = _NativeComboBox(container_row)
        register_native_combo(container_combo)
        container_combo.setMinimumWidth(190)
        container_combo.currentIndexChanged.connect(callbacks.on_container_change)
        convert_check = QCheckBox("Convert WebM to MP4", container_row)
        convert_check.stateChanged.connect(
            lambda _state: callbacks.on_update_controls_state()
        )
        container_row_layout.addWidget(container_combo)
        container_row_layout.addWidget(convert_check)
        container_label = QLabel("Container", format_card)
        post_process_label = QLabel("Post-process", format_card)
        post_process_label.hide()

        codec_combo = _NativeComboBox(format_card)
        register_native_combo(codec_combo)
        codec_combo.setMinimumWidth(190)
        codec_combo.addItem("Select codec", "")
        codec_combo.addItem("avc1 (H.264)", "avc1")
        codec_combo.addItem("av01 (AV1)", "av01")
        codec_combo.currentIndexChanged.connect(callbacks.on_codec_change)
        codec_label = QLabel("Codec & quality", format_card)

        format_combo = _NativeComboBox(format_card)
        register_native_combo(format_combo)
        format_combo.setMinimumWidth(260)
        format_combo.setPlaceholderText("Analyze a URL to load quality.")
        format_combo.currentIndexChanged.connect(
            lambda _idx: callbacks.on_update_controls_state()
        )
        format_label = QLabel("Format", format_card)
        format_label.hide()

        quality_row = QWidget(format_card)
        quality_row_layout = QVBoxLayout(quality_row)
        quality_row_layout.setContentsMargins(0, 0, 0, 0)
        quality_row_layout.setSpacing(8)
        quality_row_layout.addWidget(codec_combo)
        quality_row_layout.addWidget(format_combo)

        output_form_labels = [
            content_type_label,
            container_label,
            codec_label,
        ]
        for label in output_form_labels:
            label.setObjectName("outputFormLabel")

        output_form_rows = [
            _add_labeled_row(
                format_card,
                format_layout,
                content_type_label,
                mode_row,
            ),
        ]
        output_form_rows.append(
            _add_labeled_row(
                format_card,
                format_layout,
                container_label,
                container_row,
            )
        )
        output_form_rows.append(
            _add_labeled_row(
                format_card,
                format_layout,
                codec_label,
                quality_row,
            )
        )

        format_layout.addSpacing(8)
        save_card = QWidget(format_card)
        save_card.setObjectName("saveSection")
        save_card.setMinimumWidth(0)
        save_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        save_layout = QVBoxLayout(save_card)
        save_layout.setContentsMargins(0, 6, 0, 0)
        save_layout.setSpacing(12)
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
        output_form_rows.append(
            _add_labeled_row(
                save_card,
                save_layout,
                file_name_label,
                filename_edit,
            )
        )
        output_form_rows.append(
            _add_labeled_row(
                save_card,
                save_layout,
                output_folder_label,
                folder_row,
            )
        )

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

        ready_summary_label = QLabel("", metrics_details)
        ready_summary_label.setObjectName("readySummaryLine")
        ready_summary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        ready_summary_label.setMaximumWidth(240)
        ready_summary_label.setToolTip(
            "Current output summary based on selected format and save folder."
        )
        metrics_details_layout.addWidget(
            ready_summary_label,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        metrics_card_layout.addWidget(progress_bar)
        metrics_card_layout.addWidget(metrics_details)
        output_layout.addWidget(format_card)
        output_layout.addWidget(metrics_card)
        output_layout.addStretch(1)
        return _OutputSectionRefs(
            section=output_section,
            stage_hint_label=stage_hint_label,
            layout=output_layout,
            link_input=link_input,
            format_card=format_card,
            format_layout=format_layout,
            mode_row_layout=mode_row_layout,
            video_radio=video_radio,
            audio_radio=audio_radio,
            content_type_label=content_type_label,
            container_combo=container_combo,
            convert_check=convert_check,
            container_label=container_label,
            post_process_label=post_process_label,
            codec_combo=codec_combo,
            codec_label=codec_label,
            format_combo=format_combo,
            format_label=format_label,
            output_form_labels=output_form_labels,
            output_form_rows=output_form_rows,
            save_card=save_card,
            save_layout=save_layout,
            filename_edit=filename_edit,
            file_name_label=file_name_label,
            folder_row_layout=folder_row_layout,
            output_dir_edit=output_dir_edit,
            browse_button=browse_button,
            output_folder_label=output_folder_label,
            progress_bar=progress_bar,
            ready_summary_label=ready_summary_label,
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
        use_single_video_url_button = QPushButton("Single video", mixed_buttons)
        use_playlist_url_button = QPushButton("Playlist", mixed_buttons)
        use_single_video_url_button.clicked.connect(callbacks.on_use_single_video_url)
        use_playlist_url_button.clicked.connect(callbacks.on_use_playlist_url)
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

        source_toast = QFrame(root)
        source_toast.setObjectName("sourceToastCard")
        source_toast.setProperty("tone", "success")
        source_toast.setMinimumWidth(260)
        source_toast.setMaximumWidth(340)
        source_toast_shadow = QGraphicsDropShadowEffect(source_toast)
        source_toast_shadow.setBlurRadius(28)
        source_toast_shadow.setOffset(0, 10)
        source_toast_shadow.setColor(QColor(15, 33, 45, 48))
        source_toast.setGraphicsEffect(source_toast_shadow)
        source_toast_layout = QVBoxLayout(source_toast)
        source_toast_layout.setContentsMargins(16, 12, 16, 14)
        source_toast_layout.setSpacing(4)
        source_toast_header = QWidget(source_toast)
        source_toast_header_layout = QHBoxLayout(source_toast_header)
        source_toast_header_layout.setContentsMargins(0, 0, 0, 0)
        source_toast_header_layout.setSpacing(8)
        source_toast_title = QLabel("Formats ready", source_toast_header)
        source_toast_title.setObjectName("sourceToastTitle")
        source_toast_dismiss_button = QPushButton("×", source_toast_header)
        source_toast_dismiss_button.setObjectName("sourceToastDismissButton")
        source_toast_dismiss_button.setToolTip("Dismiss notification")
        source_toast_dismiss_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        source_toast_dismiss_button.setCursor(Qt.CursorShape.PointingHandCursor)
        source_toast_dismiss_button.setFixedSize(24, 24)
        source_toast_message = QLabel("", source_toast)
        source_toast_message.setObjectName("sourceToastMessage")
        source_toast_message.setWordWrap(True)
        source_toast_header_layout.addWidget(source_toast_title)
        source_toast_header_layout.addStretch(1)
        source_toast_header_layout.addWidget(source_toast_dismiss_button)
        source_toast_layout.addWidget(source_toast_header)
        source_toast_layout.addWidget(source_toast_message)
        source_toast.hide()

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
            source_toast=SourceToastRefs(
                card=source_toast,
                title_label=source_toast_title,
                message_label=source_toast_message,
                dismiss_button=source_toast_dismiss_button,
            ),
            downloads=downloads,
        )
