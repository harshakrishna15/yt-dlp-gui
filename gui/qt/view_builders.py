from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
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
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..app_meta import APP_DISPLAY_NAME, APP_WINDOW_SUBTITLE
from .widgets import _NativeComboBox


@dataclass(frozen=True)
class TopBarRefs:
    header: QWidget
    top_actions: QWidget
    classic_actions: QWidget
    downloads_button: QPushButton
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
class RunSectionRefs:
    section: QGroupBox
    stage_hint_label: QLabel
    status_value: QLabel
    progress_bar: QProgressBar
    start_button: QPushButton
    add_queue_button: QPushButton
    start_queue_button: QPushButton
    cancel_button: QPushButton
    ready_summary_label: QLabel
    metrics_card: QFrame
    metrics_strip: QFrame
    progress_label: QLabel
    speed_label: QLabel
    eta_label: QLabel
    item_label: QLabel
    download_result_card: QFrame
    download_result_title: QLabel
    download_result_path: QLabel
    open_last_output_folder_button: QPushButton
    copy_output_path_button: QPushButton


@dataclass(frozen=True)
class DownloadsViewRefs:
    main_page: QWidget
    main_page_index: int
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
    output_section: QGroupBox
    output_stage_hint_label: QLabel
    output_layout: QGridLayout
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
    save_card: QGroupBox
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QHBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel
    run: RunSectionRefs


@dataclass(frozen=True)
class UiRefs:
    root: QWidget
    panel_stack: QStackedWidget
    top_bar: TopBarRefs
    mixed_url: MixedUrlRefs
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


@dataclass(frozen=True)
class _OutputSectionRefs:
    section: QGroupBox
    stage_hint_label: QLabel
    layout: QGridLayout
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
    save_card: QGroupBox
    save_layout: QVBoxLayout
    filename_edit: QLineEdit
    file_name_label: QLabel
    folder_row_layout: QHBoxLayout
    output_dir_edit: QLineEdit
    browse_button: QPushButton
    output_folder_label: QLabel


class TopBarBuilder:
    @staticmethod
    def build(parent: QWidget) -> TopBarRefs:
        header = QWidget(parent)
        header.setObjectName("topBarShell")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(18)

        brand_col = QWidget(header)
        brand_col.setObjectName("topBarBrand")
        brand_layout = QVBoxLayout(brand_col)
        brand_layout.setContentsMargins(10, 7, 12, 7)
        brand_layout.setSpacing(2)
        title = QLabel(APP_DISPLAY_NAME, brand_col)
        title.setObjectName("titleLabel")
        subtitle = QLabel(APP_WINDOW_SUBTITLE, brand_col)
        subtitle.setObjectName("subtleLabel")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)

        top_actions = QWidget(header)
        top_actions_layout = QHBoxLayout(top_actions)
        top_actions_layout.setContentsMargins(0, 0, 0, 0)
        top_actions_layout.setSpacing(6)

        classic_actions = QWidget(top_actions)
        classic_actions.setObjectName("topNavRail")
        classic_layout = QHBoxLayout(classic_actions)
        classic_layout.setContentsMargins(6, 6, 6, 6)
        classic_layout.setSpacing(6)
        downloads_button = QPushButton("Downloads", classic_actions)
        queue_button = QPushButton("Queue", classic_actions)
        history_button = QPushButton("History", classic_actions)
        logs_button = QPushButton("Logs", classic_actions)
        settings_button = QPushButton("Settings", classic_actions)
        for button in (
            downloads_button,
            queue_button,
            history_button,
            logs_button,
            settings_button,
        ):
            button.setCheckable(True)
            button.setObjectName("topNavButton")
            classic_layout.addWidget(button)

        top_actions_layout.addWidget(classic_actions)
        header_layout.addWidget(brand_col, stretch=1)
        header_layout.addWidget(top_actions)
        return TopBarRefs(
            header=header,
            top_actions=top_actions,
            classic_actions=classic_actions,
            downloads_button=downloads_button,
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
        run_layout = QVBoxLayout(run)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(8)
        run_layout.addWidget(
            _build_section_header(
                run,
                "Start Download",
                compact=False,
                meta="Step 3",
            )
        )
        status_value = QLabel("Idle", run)
        status_value.setObjectName("statusLine")
        status_value.setVisible(False)
        run_layout.addWidget(status_value)

        stage_hint_label = QLabel(
            "Analyze a URL and choose a format to enable download actions.",
            run,
        )
        stage_hint_label.setObjectName("sectionStageHint")
        stage_hint_label.setWordWrap(True)
        stage_hint_label.hide()

        progress_bar = QProgressBar(run)
        progress_bar.setRange(0, 1000)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)
        run_layout.addWidget(progress_bar)

        buttons_row = QWidget(run)
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        start_button = QPushButton("Download", buttons_row)
        start_button.setObjectName("primaryActionButton")
        start_button.clicked.connect(callbacks.on_start)
        add_queue_button = QPushButton("Add to queue", buttons_row)
        add_queue_button.clicked.connect(callbacks.on_add_to_queue)
        start_queue_button = QPushButton("Download queue", buttons_row)
        start_queue_button.clicked.connect(callbacks.on_start_queue)
        cancel_button = QPushButton("Cancel", buttons_row)
        cancel_button.clicked.connect(callbacks.on_cancel)

        buttons_layout.addWidget(start_button)
        buttons_layout.addWidget(add_queue_button)
        buttons_layout.addWidget(start_queue_button)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addStretch(1)
        run_layout.addWidget(buttons_row)

        ready_summary_label = QLabel("", run)
        ready_summary_label.setObjectName("readySummaryLine")
        ready_summary_label.setToolTip(
            "Current output summary based on selected format and save folder."
        )
        run_layout.addWidget(ready_summary_label)

        feedback_row = QWidget(run)
        feedback_row_layout = QHBoxLayout(feedback_row)
        feedback_row_layout.setContentsMargins(0, 0, 0, 0)
        feedback_row_layout.setSpacing(10)

        metrics_card = QFrame(feedback_row)
        metrics_card.setObjectName("progressCard")
        metrics_card_layout = QHBoxLayout(metrics_card)
        metrics_card_layout.setContentsMargins(10, 10, 10, 10)
        metrics_card_layout.setSpacing(0)

        metrics_strip = QFrame(metrics_card)
        metrics_strip.setObjectName("metricsStrip")
        metrics_layout = QHBoxLayout(metrics_strip)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(10)
        progress_label = QLabel("Progress: -", metrics_strip)
        progress_label.setObjectName("metricInline")
        speed_label = QLabel("Speed: -", metrics_strip)
        speed_label.setObjectName("metricInline")
        eta_label = QLabel("ETA: -", metrics_strip)
        eta_label.setObjectName("metricInline")
        item_label = QLabel("Item: -", metrics_strip)
        item_label.setObjectName("metricInlineItem")
        item_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        metrics_layout.addWidget(progress_label)
        metrics_layout.addWidget(speed_label)
        metrics_layout.addWidget(eta_label)
        metrics_layout.addWidget(item_label, stretch=1)
        metrics_card_layout.addWidget(metrics_strip)
        feedback_row_layout.addWidget(metrics_card, stretch=3)

        download_result_card = QFrame(feedback_row)
        download_result_card.setObjectName("downloadResultCard")
        download_result_card.setProperty("state", "empty")
        result_layout = QHBoxLayout(download_result_card)
        result_layout.setContentsMargins(10, 10, 10, 10)
        result_layout.setSpacing(10)

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
        download_result_card.setVisible(True)
        feedback_row_layout.addWidget(download_result_card, stretch=2)
        run_layout.addWidget(feedback_row)

        return RunSectionRefs(
            section=run,
            stage_hint_label=stage_hint_label,
            status_value=status_value,
            progress_bar=progress_bar,
            start_button=start_button,
            add_queue_button=add_queue_button,
            start_queue_button=start_queue_button,
            cancel_button=cancel_button,
            ready_summary_label=ready_summary_label,
            metrics_card=metrics_card,
            metrics_strip=metrics_strip,
            progress_label=progress_label,
            speed_label=speed_label,
            eta_label=eta_label,
            item_label=item_label,
            download_result_card=download_result_card,
            download_result_title=download_result_title,
            download_result_path=download_result_path,
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


def _add_labeled_row(
    parent: QWidget,
    layout: QVBoxLayout,
    label: QLabel,
    field: QWidget,
) -> QWidget:
    row = QWidget(parent)
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)
    row_layout.addWidget(label)
    row_layout.addWidget(field, stretch=1)
    layout.addWidget(row)
    return row


def _add_save_block(
    parent: QWidget,
    layout: QVBoxLayout,
    label: QLabel,
    field: QWidget,
) -> None:
    block = QWidget(parent)
    block_layout = QVBoxLayout(block)
    block_layout.setContentsMargins(0, 0, 0, 0)
    block_layout.setSpacing(5)
    block_layout.addWidget(label)
    block_layout.addWidget(field)
    layout.addWidget(block)


class DownloadsViewBuilder:
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
        main_layout.setSpacing(10)

        source = DownloadsViewBuilder._build_source_section(main_page, callbacks)
        main_layout.addWidget(source.section)

        output = DownloadsViewBuilder._build_output_section(
            main_page,
            register_native_combo=register_native_combo,
            callbacks=callbacks,
        )
        main_layout.addWidget(output.section)

        run = RunSectionBuilder.build(main_page, callbacks.run)
        main_layout.addWidget(run.section)
        main_layout.addStretch(1)

        main_page_index = panel_stack.addWidget(main_page)

        return DownloadsViewRefs(
            main_page=main_page,
            main_page_index=main_page_index,
            source_row=source.source_row,
            url_edit=source.url_edit,
            paste_button=source.paste_button,
            analyze_button=source.analyze_button,
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
        source_shell_layout.setSpacing(10)
        source_shell_layout.addWidget(
            _build_section_header(
                source,
                "Video Source",
                compact=False,
                meta="Step 1",
            )
        )

        source_content = QWidget(source)
        source_shell_layout.addWidget(source_content)
        source_layout = QFormLayout(source_content)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        source_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        source_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        source_layout.setHorizontalSpacing(14)
        source_layout.setVerticalSpacing(4)

        url_row = QWidget(source)
        url_row.setObjectName("sourceHeroRow")
        url_row_layout = QHBoxLayout(url_row)
        url_row_layout.setContentsMargins(8, 8, 8, 8)
        url_row_layout.setSpacing(12)
        url_edit = QLineEdit(source)
        url_edit.setPlaceholderText("Paste a video or playlist URL")
        url_edit.textChanged.connect(callbacks.on_url_changed)
        url_edit.returnPressed.connect(callbacks.on_fetch_formats)
        paste_button = QPushButton("Paste", source)
        paste_button.clicked.connect(callbacks.on_paste_url)
        analyze_button = QPushButton("Analyze URL", source)
        analyze_button.setObjectName("analyzeUrlButton")
        analyze_button.clicked.connect(callbacks.on_analyze_url)
        url_row_layout.addWidget(url_edit, stretch=1)
        url_row_layout.addWidget(paste_button)
        url_row_layout.addWidget(analyze_button)
        source_layout.addRow("Video URL", url_row)
        source_url_label = source_layout.labelForField(url_row)
        if isinstance(source_url_label, QLabel):
            source_url_label.setObjectName("sectionFormLabel")

        source_feedback_label = QLabel(
            "Paste a video or playlist URL, then analyze it to load formats.",
            source,
        )
        source_feedback_label.setObjectName("sourceFeedbackLabel")
        source_feedback_label.setWordWrap(True)
        source_feedback_label.setProperty("tone", "neutral")
        source_layout.addRow("", source_feedback_label)

        source_preview_card = QFrame(source)
        source_preview_card.setObjectName("sourcePreviewCard")
        source_preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_preview_layout = QHBoxLayout(source_preview_card)
        source_preview_layout.setContentsMargins(12, 12, 12, 12)
        source_preview_layout.setSpacing(12)
        source_preview_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        source_preview_badge = QLabel("URL", source_preview_card)
        source_preview_badge.setObjectName("sourcePreviewBadge")
        source_preview_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        source_preview_badge.setFixedSize(56, 56)
        source_preview_layout.addWidget(
            source_preview_badge,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        source_preview_copy = QWidget(source_preview_card)
        source_preview_copy.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        source_preview_copy_layout = QVBoxLayout(source_preview_copy)
        source_preview_copy_layout.setContentsMargins(0, 0, 0, 0)
        source_preview_copy_layout.setSpacing(6)
        source_preview_copy_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        preview_title_label = QLabel("Source preview", source_preview_copy)
        preview_title_label.setObjectName("sourcePreviewEyebrow")
        preview_title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        preview_value = QLabel("-", source_preview_copy)
        preview_value.setObjectName("sourcePreviewTitle")
        preview_value.setWordWrap(False)
        preview_value.setMargin(0)
        preview_value.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        source_preview_placeholder = QLabel(
            "Analyze a URL to load source details.",
            source_preview_copy,
        )
        source_preview_placeholder.setObjectName("sourcePreviewPlaceholder")
        source_preview_placeholder.setWordWrap(False)
        source_preview_placeholder.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        source_preview_subtitle = QLabel(
            "Title, creator, and duration will appear here.",
            source_preview_copy,
        )
        source_preview_subtitle.setObjectName("sourcePreviewSubtitle")
        source_preview_subtitle.setWordWrap(False)
        source_preview_subtitle.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        source_preview_details = QWidget(source_preview_copy)
        source_preview_details.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        source_preview_details_layout = QHBoxLayout(source_preview_details)
        source_preview_details_layout.setContentsMargins(0, 2, 0, 0)
        source_preview_details_layout.setSpacing(6)
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
            chip.setVisible(bool(chip.text()))
            source_preview_details_layout.addWidget(chip)
        source_preview_details_layout.addStretch(1)

        source_preview_copy_layout.addWidget(preview_title_label)
        source_preview_copy_layout.addWidget(preview_value)
        source_preview_copy_layout.addWidget(source_preview_placeholder)
        source_preview_copy_layout.addWidget(source_preview_subtitle)
        source_preview_copy_layout.addWidget(source_preview_details)
        source_preview_layout.addWidget(source_preview_copy, stretch=1)
        source_layout.addRow("", source_preview_card)

        source_details_host = QWidget(source)
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
        playlist_items_layout.addWidget(playlist_items_edit, stretch=1)
        source_details_stack.addWidget(playlist_items_panel)

        source_details_label = QLabel("", source)
        source_details_label.setObjectName("sectionFormLabel")
        source_layout.addRow(source_details_label, source_details_host)
        return _SourceSectionRefs(
            section=source,
            source_row=url_row,
            url_edit=url_edit,
            paste_button=paste_button,
            analyze_button=analyze_button,
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
        output_section = QGroupBox("", parent)
        output_section.setObjectName("outputSection")
        output_shell_layout = QVBoxLayout(output_section)
        output_shell_layout.setContentsMargins(0, 0, 0, 0)
        output_shell_layout.setSpacing(10)
        output_shell_layout.addWidget(
            _build_section_header(
                output_section,
                "Export Settings",
                compact=False,
                meta="Step 2",
            )
        )

        stage_hint_label = QLabel(
            "Analyze a URL to unlock container, codec, and quality controls.",
            output_section,
        )
        stage_hint_label.setObjectName("sectionStageHint")
        stage_hint_label.setWordWrap(True)
        output_shell_layout.addWidget(stage_hint_label)

        output_content = QWidget(output_section)
        output_shell_layout.addWidget(output_content)
        output_layout = QGridLayout(output_content)
        output_layout.setContentsMargins(0, 0, 2, 0)
        output_layout.setHorizontalSpacing(18)
        output_layout.setVerticalSpacing(8)
        output_layout.setColumnStretch(0, 5)
        output_layout.setColumnStretch(1, 4)

        format_card = QGroupBox("", output_section)
        format_card.setObjectName("formatSection")
        format_layout = QVBoxLayout(format_card)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(4)
        format_layout.addWidget(
            _build_section_header(format_card, "Format & quality", compact=True)
        )

        mode_row = QWidget(format_card)
        mode_row_layout = QHBoxLayout(mode_row)
        mode_row_layout.setContentsMargins(0, 0, 0, 0)
        mode_row_layout.setSpacing(10)
        video_radio = QRadioButton("Video and Audio", mode_row)
        audio_radio = QRadioButton("Audio only", mode_row)
        video_radio.toggled.connect(callbacks.on_mode_change)
        audio_radio.toggled.connect(callbacks.on_mode_change)
        mode_row_layout.addWidget(video_radio)
        mode_row_layout.addWidget(audio_radio)
        mode_row_layout.addStretch(1)
        content_type_label = QLabel("Content type", format_card)

        container_row = QWidget(format_card)
        container_row_layout = QHBoxLayout(container_row)
        container_row_layout.setContentsMargins(0, 0, 0, 0)
        container_row_layout.setSpacing(0)
        container_combo = _NativeComboBox(container_row)
        register_native_combo(container_combo)
        container_combo.setMinimumWidth(190)
        container_combo.currentIndexChanged.connect(callbacks.on_container_change)
        convert_check = QCheckBox("Convert WebM to MP4", format_card)
        convert_check.stateChanged.connect(
            lambda _state: callbacks.on_update_controls_state()
        )
        container_row_layout.addWidget(container_combo)
        container_label = QLabel("Container", format_card)
        post_process_label = QLabel("Post-process", format_card)

        codec_combo = _NativeComboBox(format_card)
        register_native_combo(codec_combo)
        codec_combo.setMinimumWidth(190)
        codec_combo.addItem("Select codec", "")
        codec_combo.addItem("avc1 (H.264)", "avc1")
        codec_combo.addItem("av01 (AV1)", "av01")
        codec_combo.currentIndexChanged.connect(callbacks.on_codec_change)
        codec_label = QLabel("Codec", format_card)

        format_combo = _NativeComboBox(format_card)
        register_native_combo(format_combo)
        format_combo.setMinimumWidth(260)
        format_combo.currentIndexChanged.connect(
            lambda _idx: callbacks.on_update_controls_state()
        )
        format_label = QLabel("Format", format_card)

        output_form_labels = [
            content_type_label,
            container_label,
            post_process_label,
            codec_label,
            format_label,
        ]
        for label in output_form_labels:
            label.setObjectName("outputFormLabel")

        output_form_rows = [
            _add_labeled_row(format_card, format_layout, content_type_label, mode_row),
            _add_labeled_row(format_card, format_layout, container_label, container_row),
            _add_labeled_row(format_card, format_layout, post_process_label, convert_check),
            _add_labeled_row(format_card, format_layout, codec_label, codec_combo),
        ]
        format_layout.addSpacing(4)
        output_form_rows.append(
            _add_labeled_row(format_card, format_layout, format_label, format_combo)
        )

        save_card = QGroupBox("", output_section)
        save_card.setObjectName("saveSection")
        save_layout = QVBoxLayout(save_card)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.setSpacing(8)
        save_layout.addWidget(
            _build_section_header(save_card, "Save & naming", compact=True)
        )
        filename_edit = QLineEdit(save_card)
        filename_edit.setPlaceholderText("Optional single-video filename")
        file_name_label = QLabel("File name", save_card)
        file_name_label.setObjectName("saveBlockLabel")

        folder_row = QWidget(save_card)
        folder_row_layout = QHBoxLayout(folder_row)
        folder_row_layout.setContentsMargins(0, 0, 0, 0)
        folder_row_layout.setSpacing(10)
        output_dir_edit = QLineEdit(str(Path.home() / "Downloads"), save_card)
        output_dir_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...", save_card)
        browse_button.clicked.connect(callbacks.on_pick_folder)
        folder_row_layout.addWidget(output_dir_edit, stretch=1)
        folder_row_layout.addWidget(browse_button)
        output_folder_label = QLabel("Output folder", save_card)
        output_folder_label.setObjectName("saveBlockLabel")

        _add_save_block(save_card, save_layout, file_name_label, filename_edit)
        _add_save_block(save_card, save_layout, output_folder_label, folder_row)
        save_layout.addStretch(1)

        output_layout.addWidget(format_card, 0, 0)
        output_layout.addWidget(save_card, 0, 1)
        return _OutputSectionRefs(
            section=output_section,
            stage_hint_label=stage_hint_label,
            layout=output_layout,
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
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

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
            downloads=downloads,
        )
