from __future__ import annotations

import signal
import threading
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QColor, QDesktopServices, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..common import (
    diagnostics,
    download,
    format_pipeline,
    formats as formats_mod,
    settings_store,
    yt_dlp_helpers as helpers,
)
from . import panels as qt_panels
from . import style as qt_style
from ..core import format_selection as core_format_selection
from ..core import queue_logic as core_queue_logic
from ..core import urls as core_urls
from ..core import ui_state as core_ui_state
from ..core import workflow as core_workflow
from ..services import app_service
from .state import PREVIEW_TITLE_TOOLTIP_DEFAULT, preview_title_fields
from .widgets import _NativeComboBox, _QtSignals
from ..common.types import DownloadOptions, DownloadRequest, HistoryItem, QueueItem, QueueSettings

VIDEO_CONTAINERS = ("mp4", "webm")
AUDIO_CONTAINERS = ("m4a", "mp3", "opus", "wav", "flac")
CODECS = ("avc1", "av01")

FETCH_DEBOUNCE_MS = 600
HISTORY_MAX_ENTRIES = 250
LOG_MAX_LINES = 1000
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 760
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 760
SOURCE_DETAILS_NONE_INDEX = 0
SOURCE_DETAILS_PROMPT_INDEX = 1
SOURCE_DETAILS_PLAYLIST_INDEX = 2
SAMPLE_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
TOP_ACTION_ICON_PX = 16


class QtYtDlpGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("yt-dlp-gui (Qt)")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self._native_combos: list[QComboBox] = []
        self._active_animations: list[QPropertyAnimation] = []
        self._progress_anim: QPropertyAnimation | None = None
        self._logs_alert_active = False
        self._header_icons_enabled = True
        self._legacy_log_alert_icon = self._build_alert_dot_icon()
        self._top_action_icons: dict[str, dict[str, QIcon]] = {}
        self._output_layout_mode: str | None = None

        self._signals = _QtSignals()
        self._signals.formats_loaded.connect(self._on_formats_loaded)
        self._signals.progress.connect(self._on_progress_update)
        self._signals.log.connect(self._append_log)
        self._signals.download_done.connect(self._on_download_done)
        self._signals.queue_item_done.connect(self._on_queue_item_done)
        self._signals.record_output.connect(self._on_record_output)

        self._fetch_timer = QTimer(self)
        self._fetch_timer.setInterval(FETCH_DEBOUNCE_MS)
        self._fetch_timer.setSingleShot(True)
        self._fetch_timer.timeout.connect(self._start_fetch_formats)

        self._fetch_request_seq = 0
        self._active_fetch_request_id = 0
        self._is_fetching = False

        self._is_downloading = False
        self._cancel_requested = False
        self._cancel_event: threading.Event | None = None
        self._show_progress_item = False
        self._close_after_cancel = False
        self._pending_mixed_url = ""

        self._playlist_mode = False

        self._video_labels: list[str] = []
        self._video_lookup: dict[str, dict] = {}
        self._audio_labels: list[str] = []
        self._audio_lookup: dict[str, dict] = {}
        self._audio_languages: list[str] = []
        self._filtered_labels: list[str] = []
        self._filtered_lookup: dict[str, dict] = {}

        self.queue_items: list[QueueItem] = []
        self.queue_active = False
        self.queue_index: int | None = None
        self._queue_failed_items = 0

        self.download_history: list[HistoryItem] = []
        self._history_seen_paths: set[str] = set()

        self._log_lines: list[str] = []
        self._active_panel_name: str | None = None
        self._applying_user_settings = False
        self._latest_output_path: Path | None = None

        self._build_ui()
        self._update_source_details_visibility()
        self._set_preview_title("")
        self._set_audio_language_values([])
        self._set_mode_unselected()
        self._load_user_settings()
        self._connect_settings_autosave()
        self._apply_header_layout()
        self._update_controls_state()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(12)

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        brand_col = QWidget(header)
        brand_layout = QVBoxLayout(brand_col)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)
        title = QLabel("yt-dlp-gui", brand_col)
        title.setObjectName("titleLabel")
        subtitle = QLabel("Paste a video URL to get started.", brand_col)
        subtitle.setObjectName("subtleLabel")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)

        self.top_actions = QWidget(header)
        top_actions_layout = QHBoxLayout(self.top_actions)
        top_actions_layout.setContentsMargins(0, 0, 0, 0)
        top_actions_layout.setSpacing(6)

        self.classic_actions = QWidget(self.top_actions)
        classic_layout = QHBoxLayout(self.classic_actions)
        classic_layout.setContentsMargins(0, 0, 0, 0)
        classic_layout.setSpacing(6)
        self.downloads_button = QPushButton("Downloads", self.classic_actions)
        self.queue_button = QPushButton("Queue", self.classic_actions)
        self.history_button = QPushButton("History", self.classic_actions)
        self.logs_button = QPushButton("Logs", self.classic_actions)
        self.settings_button = QPushButton("Settings", self.classic_actions)
        for button in (
            self.downloads_button,
            self.queue_button,
            self.history_button,
            self.logs_button,
            self.settings_button,
        ):
            button.setCheckable(True)
            classic_layout.addWidget(button)

        top_actions_layout.addWidget(self.classic_actions)

        header_layout.addWidget(brand_col, stretch=1)
        header_layout.addWidget(self.top_actions)
        root_layout.addWidget(header)

        self.panel_stack = QStackedWidget(self)
        root_layout.addWidget(self.panel_stack, stretch=1)

        self.mixed_url_overlay = QFrame(root)
        self.mixed_url_overlay.setObjectName("mixedUrlOverlay")
        self.mixed_url_overlay_layout = QVBoxLayout(self.mixed_url_overlay)
        self.mixed_url_overlay_layout.setContentsMargins(18, 16, 18, 16)
        self.mixed_url_overlay_layout.setSpacing(0)
        self.mixed_url_overlay_layout.addStretch(1)

        self.mixed_url_alert = QFrame(self.mixed_url_overlay)
        self.mixed_url_alert.setObjectName("mixedUrlAlert")
        mixed_shadow = QGraphicsDropShadowEffect(self.mixed_url_alert)
        mixed_shadow.setBlurRadius(24)
        mixed_shadow.setOffset(0, 6)
        mixed_shadow.setColor(QColor(19, 30, 46, 80))
        self.mixed_url_alert.setGraphicsEffect(mixed_shadow)
        mixed_alert_layout = QVBoxLayout(self.mixed_url_alert)
        mixed_alert_layout.setContentsMargins(12, 10, 12, 14)
        mixed_alert_layout.setSpacing(8)
        self.mixed_url_alert_label = QLabel(
            "Download this URL as a single video or as a playlist?",
            self.mixed_url_alert,
        )
        self.mixed_url_alert_label.setObjectName("mixedUrlAlertTitle")
        self.mixed_url_alert_label.setWordWrap(True)
        mixed_alert_layout.addWidget(self.mixed_url_alert_label)
        mixed_buttons = QWidget(self.mixed_url_alert)
        self.mixed_buttons_layout = QHBoxLayout(mixed_buttons)
        self.mixed_buttons_layout.setContentsMargins(0, 0, 0, 2)
        self.mixed_buttons_layout.setSpacing(4)
        self.use_single_video_url_button = QPushButton("Single video", mixed_buttons)
        self.use_playlist_url_button = QPushButton("Playlist", mixed_buttons)
        self.use_single_video_url_button.clicked.connect(
            lambda _checked: self._apply_mixed_url_choice(use_playlist=False)
        )
        self.use_playlist_url_button.clicked.connect(
            lambda _checked: self._apply_mixed_url_choice(use_playlist=True)
        )
        self.mixed_buttons_layout.addWidget(self.use_single_video_url_button)
        self.mixed_buttons_layout.addWidget(self.use_playlist_url_button)
        self.mixed_buttons_layout.addStretch(1)
        mixed_alert_layout.addWidget(mixed_buttons)
        self.mixed_url_overlay_layout.addWidget(
            self.mixed_url_alert, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.mixed_url_overlay_layout.addStretch(1)
        self.mixed_url_overlay.hide()

        self.main_page = QWidget(self.panel_stack)
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        source = QGroupBox("1. Source", self.main_page)
        source.setObjectName("sourceSection")
        source_layout = QFormLayout(source)
        source_layout.setContentsMargins(10, 12, 10, 8)
        source_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        source_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        source_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        source_layout.setHorizontalSpacing(14)
        source_layout.setVerticalSpacing(8)

        url_row = QWidget(source)
        url_row_layout = QHBoxLayout(url_row)
        url_row_layout.setContentsMargins(0, 0, 0, 0)
        url_row_layout.setSpacing(8)
        self.url_edit = QLineEdit(source)
        self.url_edit.setPlaceholderText("Paste video or playlist URL (YouTube, Vimeo, etc.)")
        self.url_edit.textChanged.connect(self._on_url_changed)
        self.url_edit.returnPressed.connect(self._start_fetch_formats)
        self.paste_button = QPushButton("Paste", source)
        self.paste_button.clicked.connect(self._paste_url)
        url_row_layout.addWidget(self.url_edit, stretch=1)
        url_row_layout.addWidget(self.paste_button)
        source_layout.addRow("Video URL", url_row)

        sample_row = QWidget(source)
        sample_row_layout = QHBoxLayout(sample_row)
        sample_row_layout.setContentsMargins(0, 0, 0, 0)
        sample_row_layout.setSpacing(8)
        sample_hint = QLabel("Need a quick test link?", sample_row)
        sample_hint.setObjectName("sourceHelperHint")
        self.sample_url_button = QPushButton("Use sample URL", sample_row)
        self.sample_url_button.setObjectName("ghostButton")
        self.sample_url_button.clicked.connect(self._populate_sample_url)
        sample_row_layout.addWidget(sample_hint)
        sample_row_layout.addWidget(self.sample_url_button)
        sample_row_layout.addStretch(1)
        source_layout.addRow("", sample_row)

        self.source_feedback_label = QLabel(source)
        self.source_feedback_label.setObjectName("sourceFeedback")
        self.source_feedback_label.setWordWrap(True)
        source_layout.addRow("", self.source_feedback_label)

        self.source_details_host = QWidget(source)
        self.source_details_host.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_details_layout = QVBoxLayout(self.source_details_host)
        source_details_layout.setContentsMargins(0, 0, 0, 0)
        source_details_layout.setSpacing(0)
        self.source_details_stack = QStackedWidget(self.source_details_host)
        self.source_details_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        source_details_layout.addWidget(self.source_details_stack)

        self.source_details_empty = QWidget(self.source_details_stack)
        self.source_details_stack.addWidget(self.source_details_empty)
        self.source_details_prompt_placeholder = QWidget(self.source_details_stack)
        self.source_details_stack.addWidget(self.source_details_prompt_placeholder)

        self.playlist_items_panel = QWidget(self.source_details_stack)
        playlist_items_layout = QVBoxLayout(self.playlist_items_panel)
        playlist_items_layout.setContentsMargins(0, 0, 0, 0)
        playlist_items_layout.setSpacing(6)
        self.playlist_items_label = QLabel("Playlist items", self.playlist_items_panel)
        self.playlist_items_edit = QLineEdit(self.playlist_items_panel)
        self.playlist_items_edit.setPlaceholderText("Optional: 1-5,7,10-")
        playlist_items_layout.addWidget(self.playlist_items_label)
        playlist_items_layout.addWidget(self.playlist_items_edit)
        self.source_details_stack.addWidget(self.playlist_items_panel)
        self._sync_source_details_height()

        self.preview_value = QLabel("-", source)
        self.preview_value.setWordWrap(False)
        self.preview_value.setMinimumHeight(30)
        self.preview_title_label = QLabel("Preview title", source)
        source_layout.addRow(self.preview_title_label, self.preview_value)
        source_layout.addRow("", self.source_details_host)
        main_layout.addWidget(source)

        self.output_section = QGroupBox("2. Output", self.main_page)
        self.output_section.setObjectName("outputSection")
        self.output_layout = QGridLayout(self.output_section)
        self.output_layout.setContentsMargins(8, 8, 8, 6)
        self.output_layout.setHorizontalSpacing(12)
        self.output_layout.setVerticalSpacing(8)
        self.output_layout.setColumnStretch(0, 1)
        self.output_layout.setColumnStretch(1, 1)

        self.format_card = QGroupBox("Format setup", self.output_section)
        self.format_card.setObjectName("formatSection")
        self.format_layout = QVBoxLayout(self.format_card)
        self.format_layout.setContentsMargins(8, 8, 8, 6)
        self.format_layout.setSpacing(7)

        mode_row = QWidget(self.format_card)
        self.mode_row_layout = QHBoxLayout(mode_row)
        self.mode_row_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_row_layout.setSpacing(8)
        self.video_radio = QRadioButton("Video and Audio", mode_row)
        self.audio_radio = QRadioButton("Audio only", mode_row)
        self.video_radio.toggled.connect(self._on_mode_change)
        self.audio_radio.toggled.connect(self._on_mode_change)
        self.mode_row_layout.addWidget(self.video_radio)
        self.mode_row_layout.addWidget(self.audio_radio)
        self.mode_row_layout.addStretch(1)
        self.content_type_label = QLabel("Content type", self.format_card)

        container_row = QWidget(self.format_card)
        container_row_layout = QHBoxLayout(container_row)
        container_row_layout.setContentsMargins(0, 0, 0, 0)
        container_row_layout.setSpacing(0)
        self.container_combo = _NativeComboBox(container_row)
        self._register_native_combo(self.container_combo)
        self.container_combo.setMinimumWidth(190)
        self.container_combo.currentIndexChanged.connect(self._on_container_change)
        self.convert_check = QCheckBox("Convert WebM to MP4", self.format_card)
        self.convert_check.stateChanged.connect(
            lambda _state: self._update_controls_state()
        )
        container_row_layout.addWidget(self.container_combo)
        self.container_label = QLabel("Container", self.format_card)
        self.post_process_label = QLabel("Post-process", self.format_card)

        self.codec_combo = _NativeComboBox(self.format_card)
        self._register_native_combo(self.codec_combo)
        self.codec_combo.setMinimumWidth(190)
        self.codec_combo.addItem("Select codec", "")
        self.codec_combo.addItem("avc1 (H.264)", "avc1")
        self.codec_combo.addItem("av01 (AV1)", "av01")
        self.codec_combo.currentIndexChanged.connect(self._on_codec_change)
        self.codec_label = QLabel("Codec", self.format_card)

        self.format_combo = _NativeComboBox(self.format_card)
        self._register_native_combo(self.format_combo)
        self.format_combo.setMinimumWidth(260)
        self.format_combo.currentIndexChanged.connect(
            lambda _idx: self._update_controls_state()
        )
        self.format_label = QLabel("Format", self.format_card)

        self._output_form_labels = [
            self.content_type_label,
            self.container_label,
            self.post_process_label,
            self.codec_label,
            self.format_label,
        ]
        self._output_form_rows: list[QWidget] = []

        def _add_output_row(
            card: QWidget,
            layout: QVBoxLayout,
            label: QLabel,
            field: QWidget,
        ) -> None:
            row = QWidget(card)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(label)
            row_layout.addWidget(field, stretch=1)
            layout.addWidget(row)
            self._output_form_rows.append(row)

        _add_output_row(self.format_card, self.format_layout, self.content_type_label, mode_row)
        _add_output_row(self.format_card, self.format_layout, self.container_label, container_row)
        _add_output_row(self.format_card, self.format_layout, self.post_process_label, self.convert_check)
        _add_output_row(self.format_card, self.format_layout, self.codec_label, self.codec_combo)
        self.format_layout.addSpacing(6)
        _add_output_row(self.format_card, self.format_layout, self.format_label, self.format_combo)

        self.save_card = QGroupBox("Save options", self.output_section)
        self.save_card.setObjectName("saveSection")
        self.save_layout = QVBoxLayout(self.save_card)
        self.save_layout.setContentsMargins(8, 8, 8, 6)
        self.save_layout.setSpacing(8)
        self.filename_edit = QLineEdit(self.save_card)
        self.filename_edit.setPlaceholderText("Optional single-video filename")
        self.file_name_label = QLabel("File name", self.save_card)
        self.file_name_label.setObjectName("saveBlockLabel")

        folder_row = QWidget(self.save_card)
        self.folder_row_layout = QHBoxLayout(folder_row)
        self.folder_row_layout.setContentsMargins(0, 0, 0, 0)
        self.folder_row_layout.setSpacing(8)
        self.output_dir_edit = QLineEdit(str(Path.home() / "Downloads"), self.save_card)
        self.output_dir_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...", self.save_card)
        self.browse_button.clicked.connect(self._pick_folder)
        self.folder_row_layout.addWidget(self.output_dir_edit, stretch=1)
        self.folder_row_layout.addWidget(self.browse_button)
        self.output_folder_label = QLabel("Output folder", self.save_card)
        self.output_folder_label.setObjectName("saveBlockLabel")

        def _add_save_block(label: QLabel, field: QWidget) -> None:
            block = QWidget(self.save_card)
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(4)
            block_layout.addWidget(label)
            block_layout.addWidget(field)
            self.save_layout.addWidget(block)

        _add_save_block(self.file_name_label, self.filename_edit)
        _add_save_block(self.output_folder_label, folder_row)
        self.save_layout.addStretch(1)
        self._set_output_form_label_width(min_width=96)

        self.output_layout.addWidget(self.format_card, 0, 0)
        self.output_layout.addWidget(self.save_card, 0, 1)
        main_layout.addWidget(self.output_section)

        run = QGroupBox("3. Run", self.main_page)
        run.setObjectName("runSection")
        run_layout = QVBoxLayout(run)
        run_layout.setContentsMargins(10, 12, 10, 8)
        run_layout.setSpacing(6)
        self.status_value = QLabel("Idle", run)
        self.status_value.setObjectName("statusLine")
        self.status_value.setVisible(False)
        run_layout.addWidget(self.status_value)

        self.progress_bar = QProgressBar(run)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        run_layout.addWidget(self.progress_bar)

        buttons_row = QWidget(run)
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        self.start_button = QPushButton("Download", buttons_row)
        self.start_button.setObjectName("primaryActionButton")
        self.start_button.clicked.connect(self._on_start)
        self.add_queue_button = QPushButton("Add to queue", buttons_row)
        self.add_queue_button.clicked.connect(self._on_add_to_queue)
        self.start_queue_button = QPushButton("Download queue", buttons_row)
        self.start_queue_button.clicked.connect(self._on_start_queue)
        self.cancel_button = QPushButton("Cancel", buttons_row)
        self.cancel_button.clicked.connect(self._on_cancel)

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.add_queue_button)
        buttons_layout.addWidget(self.start_queue_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addStretch(1)
        run_layout.addWidget(buttons_row)

        self.metrics_strip = QFrame(run)
        self.metrics_strip.setObjectName("metricsStrip")
        metrics_layout = QHBoxLayout(self.metrics_strip)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(10)
        self.progress_label = QLabel("Progress: -", self.metrics_strip)
        self.progress_label.setObjectName("metricInline")
        self.speed_label = QLabel("Speed: -", self.metrics_strip)
        self.speed_label.setObjectName("metricInline")
        self.eta_label = QLabel("ETA: -", self.metrics_strip)
        self.eta_label.setObjectName("metricInline")
        self.item_label = QLabel("Item: -", self.metrics_strip)
        self.item_label.setObjectName("metricInlineItem")
        self.item_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        metrics_layout.addWidget(self.progress_label)
        metrics_layout.addWidget(self.speed_label)
        metrics_layout.addWidget(self.eta_label)
        metrics_layout.addWidget(self.item_label, stretch=1)
        metrics_layout.addStretch(1)
        run_layout.addWidget(self.metrics_strip)
        self.metrics_strip.setVisible(False)

        self.download_result_card = QFrame(run)
        self.download_result_card.setObjectName("downloadResultCard")
        result_layout = QHBoxLayout(self.download_result_card)
        result_layout.setContentsMargins(10, 6, 10, 6)
        result_layout.setSpacing(10)
        self.download_result_title = QLabel("Latest:", self.download_result_card)
        self.download_result_title.setObjectName("downloadResultTitle")
        self.download_result_path = QLabel("-", self.download_result_card)
        self.download_result_path.setObjectName("downloadResultPath")
        self.download_result_path.setWordWrap(False)
        self.download_result_path.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.download_result_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        result_actions = QWidget(self.download_result_card)
        result_actions_layout = QHBoxLayout(result_actions)
        result_actions_layout.setContentsMargins(0, 0, 0, 0)
        result_actions_layout.setSpacing(8)
        self.open_last_output_folder_button = QPushButton("Open folder", result_actions)
        self.open_last_output_folder_button.clicked.connect(self._open_last_output_folder)
        self.copy_output_path_button = QPushButton("Copy path", result_actions)
        self.copy_output_path_button.clicked.connect(self._copy_last_output_path)
        result_actions_layout.addWidget(self.open_last_output_folder_button)
        result_actions_layout.addWidget(self.copy_output_path_button)
        result_layout.addWidget(self.download_result_title)
        result_layout.addWidget(self.download_result_path, stretch=1)
        result_layout.addWidget(result_actions)
        self.download_result_card.setVisible(False)
        run_layout.addWidget(self.download_result_card)

        main_layout.addWidget(run)
        main_layout.addStretch(1)

        self._main_page_index = self.panel_stack.addWidget(self.main_page)

        settings_panel = self._build_settings_panel()
        queue_panel = self._build_queue_panel()
        history_panel = self._build_history_panel()
        logs_panel = self._build_logs_panel()

        self._panel_name_to_index = {
            "settings": self.panel_stack.addWidget(settings_panel),
            "queue": self.panel_stack.addWidget(queue_panel),
            "history": self.panel_stack.addWidget(history_panel),
            "logs": self.panel_stack.addWidget(logs_panel),
        }
        self._panel_buttons = {
            "downloads": self.downloads_button,
            "settings": self.settings_button,
            "queue": self.queue_button,
            "history": self.history_button,
            "logs": self.logs_button,
        }
        self._configure_top_action_icons()

        self.downloads_button.clicked.connect(lambda _checked: self._close_panel())
        self.settings_button.clicked.connect(
            lambda _checked: self._toggle_panel("settings")
        )
        self.queue_button.clicked.connect(lambda _checked: self._toggle_panel("queue"))
        self.history_button.clicked.connect(
            lambda _checked: self._toggle_panel("history")
        )
        self.logs_button.clicked.connect(lambda _checked: self._toggle_panel("logs"))
        self.downloads_button.setChecked(True)

        combo_arrow_path = (
            Path(__file__).resolve().parent / "assets" / "combo-down-arrow.svg"
        ).as_posix()
        self.setStyleSheet(qt_style.build_stylesheet(combo_arrow_path))
        self._normalize_control_sizing()
        self._set_logs_alert(False)
        self._install_tooltips()
        self._apply_responsive_layout()
        self._set_source_feedback(
            "Paste a video or playlist URL to load available formats.",
            tone="neutral",
        )

    def _register_native_combo(self, combo: QComboBox) -> None:
        combo.setMinimumHeight(27)
        popup_view = QListView(combo)
        popup_view.setObjectName("nativeComboView")
        popup_view.setFrameShape(QFrame.Shape.NoFrame)
        popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        popup_view.setMouseTracking(True)
        popup_view.viewport().setMouseTracking(True)
        combo.setView(popup_view)
        self._native_combos.append(combo)

    def _fit_combo_popup_to_contents(
        self,
        combo: QComboBox,
        *,
        min_width: int = 240,
        padding: int = 44,
    ) -> None:
        view = combo.view()
        if view is None:
            return
        metrics = QFontMetrics(view.font())
        text_width = 0
        for idx in range(combo.count()):
            text_width = max(text_width, metrics.horizontalAdvance(combo.itemText(idx)))
        view.setMinimumWidth(max(min_width, text_width + padding))
        row_height = max(30, metrics.height() + 10)
        rows = max(1, min(combo.count(), combo.maxVisibleItems()))
        popup_height = (row_height * rows) + 10
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setMinimumHeight(popup_height)
        view.setMaximumHeight(popup_height)

    def _harmonize_form_label_widths(
        self, layouts: list[QFormLayout], *, min_width: int = 120
    ) -> None:
        labels: list[QLabel] = []
        width = min_width
        for layout in layouts:
            for row in range(layout.rowCount()):
                item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
                if item is None:
                    continue
                label = item.widget()
                if not isinstance(label, QLabel):
                    continue
                labels.append(label)
                width = max(width, label.sizeHint().width())
        for label in labels:
            label.setMinimumWidth(width)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _set_output_form_label_width(self, *, min_width: int = 96) -> None:
        labels = [label for label in getattr(self, "_output_form_labels", []) if label is not None]
        if not labels:
            return
        width = max(min_width, max(label.sizeHint().width() for label in labels))
        for label in labels:
            label.setMinimumWidth(width)
            label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

    def _set_uniform_button_width(
        self, buttons: list[QPushButton], *, extra_px: int = 28
    ) -> None:
        live = [btn for btn in buttons if btn is not None]
        if not live:
            return
        metrics = QFontMetrics(live[0].font())
        width = 0
        for button in live:
            text_width = metrics.horizontalAdvance(button.text())
            icon_width = 0
            if not button.icon().isNull():
                icon_size = button.iconSize()
                icon_width = max(icon_size.width(), icon_size.height()) + 8
            width = max(width, text_width + icon_width)
        width += extra_px
        for button in live:
            button.setMinimumWidth(width)

    def _normalize_control_sizing(self) -> None:
        metrics = QFontMetrics(self.font())
        control_height = max(27, metrics.height() + 7)
        toggle_height = max(20, control_height - 7)
        for edit in (
            self.url_edit,
            self.playlist_items_edit,
            self.filename_edit,
            self.output_dir_edit,
            self.subtitle_languages_edit,
            self.network_timeout_edit,
            self.network_retries_edit,
            self.retry_backoff_edit,
            self.concurrent_fragments_edit,
        ):
            edit.setMinimumHeight(control_height)

        for combo in (
            self.container_combo,
            self.codec_combo,
            self.format_combo,
            self.audio_language_combo,
        ):
            combo.setMinimumHeight(control_height)

        for button in (
            self.downloads_button,
            self.settings_button,
            self.queue_button,
            self.history_button,
            self.logs_button,
            self.paste_button,
            self.use_single_video_url_button,
            self.use_playlist_url_button,
            self.browse_button,
            self.sample_url_button,
            self.start_button,
            self.add_queue_button,
            self.start_queue_button,
            self.cancel_button,
            self.open_last_output_folder_button,
            self.copy_output_path_button,
            self.export_diagnostics_button,
            self.queue_remove_button,
            self.queue_move_up_button,
            self.queue_move_down_button,
            self.queue_clear_button,
            self.history_open_file_button,
            self.history_open_folder_button,
            self.history_clear_button,
            self.logs_clear_button,
        ):
            button.setMinimumHeight(control_height)

        for toggle in (
            self.video_radio,
            self.audio_radio,
            self.convert_check,
        ):
            toggle.setMinimumHeight(toggle_height)

        for label in getattr(self, "_output_form_labels", []):
            label.setMinimumHeight(toggle_height)

        for row in getattr(self, "_output_form_rows", []):
            row.setMinimumHeight(control_height)

        self._set_uniform_button_width(
            [
                self.downloads_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ],
            extra_px=26,
        )
        self._set_uniform_button_width(
            [
                self.start_button,
                self.add_queue_button,
                self.start_queue_button,
                self.cancel_button,
            ],
            extra_px=34,
        )
        self._set_uniform_button_width(
            [
                self.open_last_output_folder_button,
                self.copy_output_path_button,
            ],
            extra_px=24,
        )
        self._set_uniform_button_width(
            [
                self.use_single_video_url_button,
                self.use_playlist_url_button,
            ],
            extra_px=10,
        )
        self._set_output_form_label_width(min_width=96)
        self._normalize_input_widths()

    def _normalize_input_widths(self) -> None:
        width = max(1, self.width())
        compact = width < 1280
        field_ratio = 0.24 if compact else 0.20
        field_width = max(140, min(320, int(width * field_ratio)))
        folder_field_width = max(120, min(260, field_width - 70))
        dropdown_width = max(120, min(240, int(width * 0.14)))
        small_field_width = max(84, min(138, int(width * 0.105)))

        self.url_edit.setMinimumWidth(field_width)
        self.playlist_items_edit.setMinimumWidth(field_width)
        self.filename_edit.setMinimumWidth(field_width)
        self.output_dir_edit.setMinimumWidth(folder_field_width)
        self.subtitle_languages_edit.setMinimumWidth(field_width)

        self.container_combo.setMinimumWidth(dropdown_width)
        self.codec_combo.setMinimumWidth(dropdown_width)
        self.format_combo.setMinimumWidth(dropdown_width)
        self.audio_language_combo.setMinimumWidth(dropdown_width)

        self.network_timeout_edit.setFixedWidth(small_field_width)
        self.network_retries_edit.setFixedWidth(small_field_width)
        self.retry_backoff_edit.setFixedWidth(small_field_width)
        self.concurrent_fragments_edit.setFixedWidth(small_field_width)

        if self._output_layout_mode == "compact":
            self.save_card.setMinimumWidth(0)
            self.save_card.setMaximumWidth(16777215)
        else:
            save_card_width = max(290, min(390, int(width * 0.34)))
            self.save_card.setMinimumWidth(save_card_width)
            self.save_card.setMaximumWidth(save_card_width)

    def _set_output_layout_mode(self, mode: str) -> None:
        compact = mode == "compact"
        if compact:
            self.output_layout.addWidget(self.format_card, 0, 0)
            self.output_layout.addWidget(self.save_card, 1, 0)
            self.output_layout.setColumnStretch(0, 1)
            self.output_layout.setColumnStretch(1, 0)
            self.output_layout.setHorizontalSpacing(8)
            self.output_layout.setVerticalSpacing(8)
        else:
            self.output_layout.addWidget(self.format_card, 0, 0)
            self.output_layout.addWidget(self.save_card, 0, 1)
            self.output_layout.setColumnStretch(0, 1)
            self.output_layout.setColumnStretch(1, 0)
            self.output_layout.setHorizontalSpacing(14)
            self.output_layout.setVerticalSpacing(8)

        self.format_layout.setSpacing(7)
        self.save_layout.setSpacing(8)
        self._set_output_form_label_width(min_width=96)
        self.mode_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.folder_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.folder_row_layout.setSpacing(8)
        self.folder_row_layout.setStretch(0, 1)

    def _apply_responsive_layout(self) -> None:
        width = self.width()
        desired_mode = "wide"
        if desired_mode != self._output_layout_mode:
            self._set_output_layout_mode(desired_mode)
            self._output_layout_mode = desired_mode

        self.mixed_buttons_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self._sync_source_details_height()

    def _install_tooltips(self) -> None:
        self.downloads_button.setToolTip("Open the main downloads view.")
        self.settings_button.setToolTip("Open settings view.")
        self.queue_button.setToolTip("Open queue manager view.")
        self.history_button.setToolTip("Open download history view.")
        self.logs_button.setToolTip("Open logs view.")

        self.url_edit.setToolTip("Paste a video or playlist URL.")
        self.paste_button.setToolTip("Paste URL from clipboard.")
        self.mixed_url_alert.setToolTip(
            "Choose how to treat URLs that contain both video and playlist IDs."
        )
        self.use_single_video_url_button.setToolTip(
            "Remove playlist parameters and use only the video URL."
        )
        self.use_playlist_url_button.setToolTip(
            "Switch to the playlist URL and ignore the direct video ID."
        )
        self.playlist_items_edit.setToolTip(
            "Optional playlist range (for example 1-5,7,10-). Leave blank for full playlist."
        )
        self.preview_value.setToolTip(PREVIEW_TITLE_TOOLTIP_DEFAULT)

        self.video_radio.setToolTip("Download video and audio.")
        self.audio_radio.setToolTip("Download audio only.")
        self.container_combo.setToolTip("Choose output container format.")
        self.codec_combo.setToolTip("Choose preferred video codec.")
        self.format_combo.setToolTip("Choose exact format/quality.")
        self.convert_check.setToolTip("Re-encode WebM to MP4 after download.")
        self.filename_edit.setToolTip(
            "Optional custom filename for single-video downloads."
        )
        self.output_dir_edit.setToolTip("Selected output folder.")
        self.browse_button.setToolTip("Choose output folder.")

        self.subtitle_languages_edit.setToolTip(
            "Comma-separated subtitle languages (for example en,es)."
        )
        self.write_subtitles_check.setToolTip("Write subtitle files.")
        self.embed_subtitles_check.setToolTip("Embed subtitles into the media file.")
        self.audio_language_combo.setToolTip(
            "Prefer a specific detected audio language."
        )
        self.network_timeout_edit.setToolTip("Socket timeout in seconds.")
        self.network_retries_edit.setToolTip("Number of retry attempts.")
        self.retry_backoff_edit.setToolTip("Retry backoff in seconds.")
        self.concurrent_fragments_edit.setToolTip(
            "Concurrent fragment downloads (1-4, capped at 4)."
        )
        self.show_header_icons_check.setToolTip(
            "Turn top bar action icons on or off."
        )
        self.open_folder_after_download_check.setToolTip(
            "Open the selected output folder after downloads finish."
        )
        self.export_diagnostics_button.setToolTip(
            "Export a diagnostics report to your output folder."
        )

        self.start_button.setToolTip("Start one download.")
        self.add_queue_button.setToolTip("Add the current URL/settings to queue.")
        self.start_queue_button.setToolTip("Start queue download.")
        self.cancel_button.setToolTip("Cancel the current download.")
        self.status_value.setToolTip("Current run status.")

        self.queue_list.setToolTip("Queued downloads.")
        self.queue_remove_button.setToolTip("Remove selected queue items.")
        self.queue_move_up_button.setToolTip("Move selected queue items up.")
        self.queue_move_down_button.setToolTip("Move selected queue items down.")
        self.queue_clear_button.setToolTip("Clear the queue.")

        self.history_list.setToolTip("Recent downloaded files.")
        self.history_open_file_button.setToolTip("Open selected file.")
        self.history_open_folder_button.setToolTip("Open selected file folder.")
        self.history_clear_button.setToolTip("Clear download history.")

        self.logs_view.setToolTip("Download logs.")
        self.logs_clear_button.setToolTip("Clear logs.")
        self.sample_url_button.setToolTip("Fill a sample URL for quick testing.")
        self.source_feedback_label.setToolTip(
            "Current source URL validation and format-loading feedback."
        )
        self.open_last_output_folder_button.setToolTip(
            "Open the folder containing the latest downloaded file."
        )
        self.copy_output_path_button.setToolTip(
            "Copy the full path of the latest downloaded file."
        )

    def _refresh_widget_style(self, widget: QWidget) -> None:
        style = widget.style()
        if style is None:
            return
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _set_source_feedback(self, text: str, *, tone: str = "neutral") -> None:
        tone_value = tone if tone in {"neutral", "loading", "success", "warning", "error"} else "neutral"
        self.source_feedback_label.setText(str(text or "").strip())
        if self.source_feedback_label.property("tone") != tone_value:
            self.source_feedback_label.setProperty("tone", tone_value)
            self._refresh_widget_style(self.source_feedback_label)

    def _populate_sample_url(self) -> None:
        self.url_edit.setText(SAMPLE_VIDEO_URL)
        self.url_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _set_metrics_visible(self, visible: bool) -> None:
        enabled = bool(visible)
        self.metrics_strip.setVisible(enabled)
        self.item_label.setVisible(enabled)

    def _clear_last_output_path(self) -> None:
        self._latest_output_path = None
        self.download_result_path.setText("-")
        self.download_result_path.setToolTip("")
        self.download_result_card.setVisible(False)
        self.open_last_output_folder_button.setEnabled(False)
        self.copy_output_path_button.setEnabled(False)

    def _refresh_last_output_text(self) -> None:
        if self._latest_output_path is None:
            self.download_result_path.setText("-")
            self.download_result_path.setToolTip("")
            return
        full_text = str(self._latest_output_path)
        width = max(80, self.download_result_path.width() - 4)
        metrics = QFontMetrics(self.download_result_path.font())
        shown_text = metrics.elidedText(
            full_text,
            Qt.TextElideMode.ElideMiddle,
            width,
        )
        self.download_result_path.setText(shown_text)
        self.download_result_path.setToolTip(full_text)

    def _set_last_output_path(self, output_path: Path) -> None:
        resolved = Path(output_path).expanduser()
        self._latest_output_path = resolved
        show_latest_output = not self._is_downloading
        self.open_last_output_folder_button.setEnabled(
            show_latest_output and resolved.parent.exists()
        )
        self.copy_output_path_button.setEnabled(show_latest_output)
        self.download_result_card.setVisible(show_latest_output)
        self._refresh_last_output_text()
        QTimer.singleShot(0, self._refresh_last_output_text)

    def _open_last_output_folder(self) -> None:
        if self._latest_output_path is None:
            return
        folder = self._latest_output_path.parent
        if not folder.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _copy_last_output_path(self) -> None:
        if self._latest_output_path is None:
            return
        QApplication.clipboard().setText(str(self._latest_output_path))
        self._set_status("Output path copied", log=False)

    def _set_current_item_display(self, *, progress: str, title: str) -> None:
        progress_clean = str(progress or "-").strip() or "-"
        title_clean = re.sub(r"\s+", " ", str(title or "-").strip()) or "-"
        if progress_clean == "-":
            self.item_label.setText(f"Item: {title_clean}")
        else:
            self.item_label.setText(f"Item: {progress_clean} - {title_clean}")
        self.item_label.setToolTip(title_clean)
        self.item_label.setVisible(self.metrics_strip.isVisible())

    def _set_current_item_from_text(self, item: str) -> None:
        clean = re.sub(r"\s+", " ", str(item or "").strip())
        if not clean:
            self._set_current_item_display(progress="-", title="-")
            return
        match = re.match(r"^(\d+/\d+)\s+(.+)$", clean)
        if match:
            self._set_current_item_display(
                progress=match.group(1),
                title=match.group(2),
            )
            return
        self._set_current_item_display(progress="-", title=clean)

    def _build_settings_panel(self) -> QWidget:
        return qt_panels.build_settings_panel(self)

    def _build_queue_panel(self) -> QWidget:
        return qt_panels.build_queue_panel(self)

    def _build_history_panel(self) -> QWidget:
        return qt_panels.build_history_panel(self)

    def _build_logs_panel(self) -> QWidget:
        return qt_panels.build_logs_panel(self, max_lines=LOG_MAX_LINES)

    def _default_output_dir(self) -> str:
        return str(Path.home() / "Downloads")

    def _load_user_settings(self) -> None:
        settings = settings_store.load_settings(
            default_output_dir=self._default_output_dir()
        )
        self._applying_user_settings = True
        try:
            self.output_dir_edit.setText(self._default_output_dir())
            self.subtitle_languages_edit.setText(
                str(settings.get("subtitle_languages") or "")
            )
            self.write_subtitles_check.setChecked(
                bool(settings.get("write_subtitles"))
            )
            self.network_timeout_edit.setText(str(settings.get("network_timeout") or ""))
            self.network_retries_edit.setText(str(settings.get("network_retries") or ""))
            self.retry_backoff_edit.setText(str(settings.get("retry_backoff") or ""))
            self.concurrent_fragments_edit.setText(
                str(settings.get("concurrent_fragments") or "")
            )
            show_header_icons = bool(settings.get("show_header_icons", True))
            self.show_header_icons_check.setChecked(show_header_icons)
            self._set_header_icons_enabled(show_header_icons)
            self.open_folder_after_download_check.setChecked(
                bool(settings.get("open_folder_after_download"))
            )
        finally:
            self._applying_user_settings = False

    def _capture_user_settings(self) -> dict[str, object]:
        return {
            "subtitle_languages": self.subtitle_languages_edit.text().strip(),
            "write_subtitles": bool(self.write_subtitles_check.isChecked()),
            "network_timeout": self.network_timeout_edit.text().strip(),
            "network_retries": self.network_retries_edit.text().strip(),
            "retry_backoff": self.retry_backoff_edit.text().strip(),
            "concurrent_fragments": self.concurrent_fragments_edit.text().strip(),
            "show_header_icons": bool(self.show_header_icons_check.isChecked()),
            "open_folder_after_download": bool(
                self.open_folder_after_download_check.isChecked()
            ),
        }

    def _save_user_settings(self) -> None:
        if self._applying_user_settings:
            return
        settings_store.save_settings(
            self._capture_user_settings(),
            default_output_dir=self._default_output_dir(),
        )

    def _connect_settings_autosave(self) -> None:
        self.subtitle_languages_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.write_subtitles_check.stateChanged.connect(
            lambda _state: self._save_user_settings()
        )
        self.network_timeout_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.network_retries_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.retry_backoff_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.concurrent_fragments_edit.textChanged.connect(
            lambda _text: self._save_user_settings()
        )
        self.show_header_icons_check.stateChanged.connect(
            self._on_show_header_icons_changed
        )
        self.open_folder_after_download_check.stateChanged.connect(
            lambda _state: self._save_user_settings()
        )

    def _on_show_header_icons_changed(self, _state: int) -> None:
        self._set_header_icons_enabled(self.show_header_icons_check.isChecked())
        self._save_user_settings()

    def _maybe_open_output_folder(self) -> None:
        if not self.open_folder_after_download_check.isChecked():
            return
        output_dir = Path(
            self.output_dir_edit.text().strip() or self._default_output_dir()
        ).expanduser()
        if not output_dir.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))

    def _apply_header_layout(self) -> None:
        self.classic_actions.setVisible(True)
        self._refresh_top_action_icons()

    def _toggle_panel(self, name: str) -> None:
        if self._active_panel_name == name:
            self._close_panel()
            return
        self._open_panel(name)

    def _build_alert_dot_icon(self, *, diameter: int = 8) -> QIcon:
        size = max(6, int(diameter))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d64545"))
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        return QIcon(pixmap)

    def _load_asset_icon(self, filename: str) -> QIcon:
        path = Path(__file__).resolve().parent / "assets" / filename
        if not path.exists():
            return QIcon()
        return QIcon(path.as_posix())

    def _set_header_icons_enabled(self, enabled: bool) -> None:
        enabled_flag = bool(enabled)
        if self._header_icons_enabled == enabled_flag:
            return
        self._header_icons_enabled = enabled_flag
        self._refresh_top_action_icons()

    def _panel_icon(self, name: str, *, checked: bool, alert: bool = False) -> QIcon:
        variants = self._top_action_icons.get(name, {})
        if name == "logs" and alert:
            return variants.get("alert", variants.get("normal", QIcon()))
        if checked:
            return variants.get("active", variants.get("normal", QIcon()))
        return variants.get("normal", QIcon())

    def _refresh_top_action_icons(self) -> None:
        full_icon_size = QSize(TOP_ACTION_ICON_PX, TOP_ACTION_ICON_PX)
        alert_dot_size = QSize(8, 8)

        if self._header_icons_enabled:
            self.downloads_button.setIcon(QIcon())
            self.settings_button.setIcon(
                self._panel_icon("settings", checked=self.settings_button.isChecked())
            )
            self.queue_button.setIcon(
                self._panel_icon("queue", checked=self.queue_button.isChecked())
            )
            self.history_button.setIcon(
                self._panel_icon("history", checked=self.history_button.isChecked())
            )
            self.logs_button.setIcon(
                self._panel_icon(
                    "logs",
                    checked=self.logs_button.isChecked(),
                    alert=self._logs_alert_active,
                )
            )
            for button in (
                self.downloads_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ):
                button.setIconSize(full_icon_size)
        else:
            self.downloads_button.setIcon(QIcon())
            self.settings_button.setIcon(QIcon())
            self.queue_button.setIcon(QIcon())
            self.history_button.setIcon(QIcon())
            self.logs_button.setIcon(
                self._legacy_log_alert_icon if self._logs_alert_active else QIcon()
            )
            self.logs_button.setIconSize(alert_dot_size)
            for button in (
                self.downloads_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
            ):
                button.setIconSize(full_icon_size)

        self._set_uniform_button_width(
            [
                self.downloads_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ],
            extra_px=26,
        )

    def _configure_top_action_icons(self) -> None:
        self._top_action_icons = {
            "settings": {
                "normal": self._load_asset_icon("tmp-settings.svg"),
                "active": self._load_asset_icon("tmp-settings-active.svg"),
            },
            "queue": {
                "normal": self._load_asset_icon("tmp-queue.svg"),
                "active": self._load_asset_icon("tmp-queue-active.svg"),
            },
            "history": {
                "normal": self._load_asset_icon("tmp-history.svg"),
                "active": self._load_asset_icon("tmp-history-active.svg"),
            },
            "logs": {
                "normal": self._load_asset_icon("tmp-logs.svg"),
                "active": self._load_asset_icon("tmp-logs-active.svg"),
                "alert": self._load_asset_icon("tmp-logs-alert.svg"),
            },
        }
        self._refresh_top_action_icons()

    def _set_logs_alert(self, active: bool) -> None:
        if self._logs_alert_active == active:
            return
        self._logs_alert_active = active
        self._refresh_top_action_icons()

    def _is_attention_log(self, text: str) -> bool:
        lower = text.lower()
        return (
            "[error]" in lower
            or "error" in lower
            or "failed" in lower
            or "exception" in lower
            or "traceback" in lower
        )

    def _track_animation(self, anim: QPropertyAnimation) -> None:
        self._active_animations.append(anim)
        anim.finished.connect(lambda a=anim: self._release_animation(a))

    def _release_animation(self, anim: QPropertyAnimation) -> None:
        if anim in self._active_animations:
            self._active_animations.remove(anim)
        if anim is self._progress_anim:
            self._progress_anim = None
        anim.deleteLater()

    def _animate_widget_fade_in(
        self, widget: QWidget | None, *, duration_ms: int = 170
    ) -> None:
        if widget is None:
            return
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._track_animation(anim)
        anim.start()

    def _open_panel(self, name: str) -> None:
        window_size = self.size()
        index = self._panel_name_to_index.get(name)
        if index is None:
            return
        self.panel_stack.setCurrentIndex(index)
        self._animate_widget_fade_in(self.panel_stack.currentWidget())
        self._active_panel_name = name
        if name == "logs":
            self._set_logs_alert(False)
        for panel_name, button in self._panel_buttons.items():
            button.setChecked(panel_name == name)
        self._refresh_top_action_icons()
        self._set_mixed_url_alert_visible(False)
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _close_panel(self) -> None:
        window_size = self.size()
        self.panel_stack.setCurrentIndex(self._main_page_index)
        self._animate_widget_fade_in(self.panel_stack.currentWidget())
        self._active_panel_name = None
        for panel_name, button in self._panel_buttons.items():
            button.setChecked(panel_name == "downloads")
        self._refresh_top_action_icons()
        self._set_mixed_url_alert_visible(bool(self._pending_mixed_url))
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _append_log(self, text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        self._log_lines.append(clean)
        if len(self._log_lines) > LOG_MAX_LINES:
            self._log_lines = self._log_lines[-LOG_MAX_LINES:]
        self.logs_view.appendPlainText(clean)
        if self._active_panel_name != "logs" and self._is_attention_log(clean):
            self._set_logs_alert(True)

    def _clear_logs(self) -> None:
        self._log_lines.clear()
        self.logs_view.clear()
        self._set_logs_alert(False)

    def _set_status(self, text: str, *, log: bool = True) -> None:
        value = (text or "").strip() or "Idle"
        self.status_value.setText(value)
        if log:
            self._append_log(f"[status] {value}")

    def _set_preview_title(self, title: str) -> None:
        shown, tooltip = preview_title_fields(title)
        self.preview_value.setText(shown)
        self.preview_value.setToolTip(tooltip)

    def _set_mixed_url_alert_visible(self, visible: bool) -> None:
        should_show = bool(visible) and (
            self.panel_stack.currentIndex() == self._main_page_index
        )
        self._layout_mixed_url_overlay()
        self.mixed_url_overlay.setVisible(should_show)
        if should_show:
            self.mixed_url_overlay.raise_()

    def _set_playlist_items_visible(self, visible: bool) -> None:
        if bool(visible):
            self.source_details_stack.setCurrentIndex(SOURCE_DETAILS_PLAYLIST_INDEX)
        elif self.source_details_stack.currentIndex() == SOURCE_DETAILS_PLAYLIST_INDEX:
            self.source_details_stack.setCurrentIndex(SOURCE_DETAILS_NONE_INDEX)
        self._sync_source_details_height()

    def _sync_source_details_height(self) -> None:
        current = self.source_details_stack.currentWidget()
        if current is None:
            self.source_details_host.setFixedHeight(0)
            self.source_details_stack.setFixedHeight(0)
            return
        if self.source_details_stack.currentIndex() == SOURCE_DETAILS_NONE_INDEX:
            target = 0
        else:
            target = max(0, current.sizeHint().height())
        self.source_details_host.setFixedHeight(target)
        self.source_details_stack.setFixedHeight(target)

    def _layout_mixed_url_overlay(self) -> None:
        root = self.centralWidget()
        if root is None:
            return
        panel_rect = self.panel_stack.geometry()
        self.mixed_url_overlay.setGeometry(panel_rect)
        max_width = max(320, panel_rect.width() - 56)
        self.mixed_url_alert.setMaximumWidth(min(760, max_width))
        layout = self.mixed_url_alert.layout()
        if layout is not None:
            layout.activate()
        self.mixed_url_alert.adjustSize()
        self.mixed_url_alert.setMinimumHeight(self.mixed_url_alert.sizeHint().height())

    def _update_source_details_visibility(self) -> None:
        window_size = self.size()
        prompt_visible = bool(self._pending_mixed_url)
        self._set_mixed_url_alert_visible(prompt_visible)
        self._set_playlist_items_visible(bool(self._playlist_mode) and (not prompt_visible))
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _apply_mixed_url_choice(self, *, use_playlist: bool) -> None:
        source_url = core_urls.strip_url_whitespace(
            self._pending_mixed_url or self.url_edit.text().strip()
        )
        if not source_url or not core_urls.is_mixed_url(source_url):
            self._pending_mixed_url = ""
            self._update_source_details_visibility()
            return
        resolved = (
            core_urls.to_playlist_url(source_url)
            if use_playlist
            else core_urls.strip_list_param(source_url)
        )
        self._pending_mixed_url = ""
        self._update_source_details_visibility()
        self.url_edit.setText(resolved)
        self._set_status(
            "Using playlist URL" if use_playlist else "Using single-video URL"
        )

    def _paste_url(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if not clip:
            self._set_status("Clipboard is empty")
            return
        self.url_edit.setText(core_urls.strip_url_whitespace(clip))
        self._set_status("URL pasted")

    def _pick_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select output folder")
        if selected:
            self.output_dir_edit.setText(selected)

    def _on_url_changed(self) -> None:
        current = self.url_edit.text()
        normalized = core_urls.strip_url_whitespace(current)
        if normalized != current:
            self.url_edit.blockSignals(True)
            self.url_edit.setText(normalized)
            self.url_edit.blockSignals(False)
        has_mixed_url = bool(normalized and core_urls.is_mixed_url(normalized))
        if has_mixed_url:
            self._pending_mixed_url = normalized
            if (
                self.status_value.text()
                != "Choose video or playlist URL before fetching formats."
            ):
                self._set_status("Choose video or playlist URL before fetching formats.")
            self._set_source_feedback(
                "Choose Single video or Playlist before loading formats.",
                tone="warning",
            )
        else:
            self._pending_mixed_url = ""

        self._fetch_timer.stop()
        self._fetch_request_seq += 1
        self._active_fetch_request_id = self._fetch_request_seq
        self._is_fetching = False
        self._playlist_mode = core_urls.is_playlist_url(normalized)

        self._set_mode_unselected()
        self._set_combo_items(
            self.container_combo, [("Select container", "")], keep_current=False
        )
        self.codec_combo.blockSignals(True)
        self.codec_combo.setCurrentIndex(0)
        self.codec_combo.blockSignals(False)
        self.convert_check.setChecked(False)
        self.playlist_items_edit.clear()
        self._video_labels = []
        self._video_lookup = {}
        self._audio_labels = []
        self._audio_lookup = {}
        self._filtered_labels = []
        self._filtered_lookup = {}
        self._audio_languages = []
        self._set_preview_title("")
        self.format_combo.clear()
        self._set_audio_language_values([])
        self._update_source_details_visibility()

        if not normalized:
            self._set_source_feedback(
                "Paste a video or playlist URL to load available formats.",
                tone="neutral",
            )
        elif (not has_mixed_url) and (not self._is_downloading):
            self._set_source_feedback(
                "URL captured. Loading available formats...",
                tone="loading",
            )

        if normalized and (not has_mixed_url) and not self._is_downloading:
            self._fetch_timer.start()
        self._update_controls_state()

    def _start_fetch_formats(self) -> None:
        if self._is_downloading:
            return
        url = self.url_edit.text().strip()
        if not url or self._pending_mixed_url:
            return
        self._fetch_request_seq += 1
        request_id = self._fetch_request_seq
        self._active_fetch_request_id = request_id
        self._is_fetching = True
        self._set_status("Fetching formats...")
        self._set_source_feedback("Loading available formats...", tone="loading")
        self._update_controls_state()
        thread = threading.Thread(
            target=self._fetch_formats_worker,
            args=(request_id, url),
            daemon=True,
        )
        thread.start()

    def _fetch_formats_worker(self, request_id: int, url: str) -> None:
        try:
            info = helpers.fetch_info(url)
            formats = formats_mod.formats_from_info(info)
            collections = format_pipeline.build_format_collections(formats)
            payload = {
                "collections": collections,
                "preview_title": format_pipeline.preview_title_from_info(info),
            }
            is_playlist = bool(
                info.get("_type") == "playlist" or info.get("entries") is not None
            )
            self._signals.formats_loaded.emit(
                request_id, url, payload, False, is_playlist
            )
        except Exception as exc:
            self._signals.log.emit(f"[error] Could not fetch formats: {exc}")
            self._signals.formats_loaded.emit(request_id, url, {}, True, False)

    def _on_formats_loaded(
        self,
        request_id: int,
        url: str,
        payload: object,
        error: bool,
        is_playlist: bool,
    ) -> None:
        if request_id != self._active_fetch_request_id:
            return
        current_url = self.url_edit.text().strip()
        if url != current_url:
            self._is_fetching = False
            if current_url and not self._is_downloading:
                self._fetch_timer.start()
            self._update_controls_state()
            return
        self._is_fetching = False
        self._playlist_mode = bool(is_playlist)
        self._update_source_details_visibility()

        if error or not isinstance(payload, dict):
            self._video_labels = []
            self._video_lookup = {}
            self._audio_labels = []
            self._audio_lookup = {}
            self._audio_languages = []
            self._filtered_labels = []
            self._filtered_lookup = {}
            self._set_preview_title("")
            self.format_combo.clear()
            self._set_audio_language_values([])
            status_text = "Could not fetch formats" if error else "No formats found"
            self._set_status(status_text)
            self._set_source_feedback(
                "Could not load formats. Check the URL or network and try again."
                if error
                else "No formats found for this URL. Try a different link.",
                tone="error" if error else "warning",
            )
            self._update_controls_state()
            return

        collections = payload.get("collections") or {}
        self._video_labels = list(collections.get("video_labels", []))
        self._video_lookup = dict(collections.get("video_lookup", {}))
        self._audio_labels = list(collections.get("audio_labels", []))
        self._audio_lookup = dict(collections.get("audio_lookup", {}))
        self._audio_languages = list(collections.get("audio_languages", []))
        preview_title = str(payload.get("preview_title") or "").strip()
        self._set_preview_title(preview_title)
        self._set_audio_language_values(self._audio_languages)
        if self._video_labels or self._audio_labels:
            self._set_status("Formats loaded")
            self._set_source_feedback(
                "Formats are ready. Choose options and start the download.",
                tone="success",
            )
        else:
            self._set_status("No formats found")
            self._set_source_feedback(
                "No formats found for this URL. Try a different link.",
                tone="warning",
            )
        self._apply_mode_formats()
        self._update_controls_state()

    def _set_audio_language_values(self, languages: list[str]) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for value in languages:
            clean = str(value or "").strip().lower()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            unique.append(clean)
        values = ["Any"] + unique
        current = self.audio_language_combo.currentText().strip() or "Any"
        self.audio_language_combo.blockSignals(True)
        self.audio_language_combo.clear()
        self.audio_language_combo.addItems(values)
        idx = self.audio_language_combo.findText(current, Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            idx = 0
        self.audio_language_combo.setCurrentIndex(idx)
        self.audio_language_combo.blockSignals(False)

    def _set_mode_unselected(self) -> None:
        self.video_radio.setAutoExclusive(False)
        self.audio_radio.setAutoExclusive(False)
        self.video_radio.setChecked(False)
        self.audio_radio.setChecked(False)
        self.video_radio.setAutoExclusive(True)
        self.audio_radio.setAutoExclusive(True)

    def _current_mode(self) -> str:
        if self.video_radio.isChecked():
            return "video"
        if self.audio_radio.isChecked():
            return "audio"
        return ""

    def _current_container(self) -> str:
        value = (self.container_combo.currentData() or "").strip().lower()
        return value

    def _current_codec(self) -> str:
        value = (self.codec_combo.currentData() or "").strip().lower()
        return value

    def _set_combo_items(
        self,
        combo: QComboBox,
        items: list[tuple[str, str]],
        *,
        keep_current: bool = True,
    ) -> None:
        current = combo.currentData() if keep_current else None
        combo.blockSignals(True)
        combo.clear()
        for label, value in items:
            combo.addItem(label, value)
        if keep_current and current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _on_mode_change(self) -> None:
        mode = self._current_mode()
        if mode == "audio":
            items = [
                ("Select container", ""),
                *[(c.upper(), c) for c in AUDIO_CONTAINERS],
            ]
            self._set_combo_items(self.container_combo, items)
            self.codec_combo.setCurrentIndex(0)
        elif mode == "video":
            items = [
                ("Select container", ""),
                *[(c.upper(), c) for c in VIDEO_CONTAINERS],
            ]
            self._set_combo_items(self.container_combo, items)
        else:
            self._set_combo_items(
                self.container_combo, [("Select container", "")], keep_current=False
            )
            self.codec_combo.setCurrentIndex(0)
        self._apply_mode_formats()
        self._update_controls_state()

    def _on_container_change(self) -> None:
        self._apply_mode_formats()
        self._update_controls_state()

    def _on_codec_change(self) -> None:
        self._apply_mode_formats()
        self._update_controls_state()

    def _apply_mode_formats(self) -> None:
        mode = self._current_mode()
        container = self._current_container()
        codec = self._current_codec()
        result = core_format_selection.select_mode_formats(
            mode=mode,
            container=container,
            codec=codec,
            video_labels=list(self._video_labels),
            video_lookup=dict(self._video_lookup),
            audio_labels=list(self._audio_labels),
            audio_lookup=dict(self._audio_lookup),
            video_containers=VIDEO_CONTAINERS,
            required_video_codecs=CODECS,
        )
        self._filtered_labels = list(result.labels)
        self._filtered_lookup = dict(result.lookup)

        current = self.format_combo.currentText().strip()
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for label in self._filtered_labels:
            self.format_combo.addItem(label)
        if current and current in self._filtered_labels:
            self.format_combo.setCurrentText(current)
        self.format_combo.blockSignals(False)

    def _selected_format_label(self) -> str:
        return self.format_combo.currentText().strip()

    def _selected_format_info(self) -> dict | None:
        label = self._selected_format_label()
        if not label:
            return None
        return self._filtered_lookup.get(label)

    def _snapshot_download_options(self) -> DownloadOptions:
        return app_service.build_download_options(
            network_timeout_raw=self.network_timeout_edit.text(),
            network_retries_raw=self.network_retries_edit.text(),
            retry_backoff_raw=self.retry_backoff_edit.text(),
            concurrent_fragments_raw=self.concurrent_fragments_edit.text(),
            subtitle_languages_raw=self.subtitle_languages_edit.text(),
            write_subtitles_requested=bool(self.write_subtitles_check.isChecked()),
            embed_subtitles_requested=bool(self.embed_subtitles_check.isChecked()),
            is_video_mode=self._current_mode() == "video",
            audio_language_raw=self.audio_language_combo.currentText(),
            custom_filename_raw=self.filename_edit.text(),
        )

    def _capture_queue_settings(self) -> QueueSettings:
        fmt_label = self._selected_format_label()
        fmt_info = self._selected_format_info() or {}
        options = self._snapshot_download_options()
        return app_service.build_queue_settings(
            mode=self._current_mode(),
            format_filter=self._current_container(),
            codec_filter=self._current_codec(),
            convert_to_mp4=bool(self.convert_check.isChecked()),
            format_label=fmt_label,
            format_info=fmt_info,
            output_dir=self.output_dir_edit.text().strip(),
            playlist_items=self.playlist_items_edit.text(),
            options=options,
        )

    def _on_start(self) -> None:
        if self._is_downloading:
            return
        url = self.url_edit.text().strip()
        issue = core_workflow.single_start_issue(
            url=url,
            formats_loaded=bool(self._filtered_lookup),
        )
        if issue is not None:
            title, message = core_workflow.single_start_error_text(issue)
            QMessageBox.critical(self, title, message)
            return

        output_dir = Path(self.output_dir_edit.text().strip()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Output folder unavailable",
                f"Could not create/access output folder:\n{output_dir}\n\n{exc}",
            )
            return

        options = self._snapshot_download_options()
        self._is_downloading = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self._show_progress_item = bool(self._playlist_mode)
        self._clear_logs()
        self._reset_progress_summary()
        self._clear_last_output_path()
        self._set_metrics_visible(True)
        self._set_status("Downloading...")
        self._set_source_feedback("Download in progress...", tone="loading")
        self._update_controls_state()

        request, was_normalized = app_service.build_single_download_request(
            url=url,
            output_dir=output_dir,
            fmt_info=self._selected_format_info(),
            fmt_label=self._selected_format_label(),
            format_filter=self._current_container(),
            convert_to_mp4=bool(self.convert_check.isChecked()),
            playlist_enabled=bool(self._playlist_mode),
            playlist_items_raw=self.playlist_items_edit.text(),
            options=options,
        )
        if was_normalized:
            self._append_log("[info] Playlist items normalized (spaces removed).")
        if request["playlist_enabled"]:
            self._append_log(
                f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}"
            )
        thread = threading.Thread(
            target=self._run_single_download_worker,
            kwargs={"request": request},
            daemon=True,
        )
        thread.start()

    def _run_single_download_worker(self, *, request: DownloadRequest) -> None:
        result = app_service.run_download_request(
            request=request,
            cancel_event=self._cancel_event,
            log=lambda msg: self._signals.log.emit(str(msg)),
            update_progress=lambda payload: self._signals.progress.emit(dict(payload)),
            record_output=lambda p: self._signals.record_output.emit(
                str(p), str(request["url"])
            ),
        )
        self._signals.download_done.emit(str(result))

    def _on_download_done(self, result: str) -> None:
        if self.queue_active:
            return
        self._is_downloading = False
        self._cancel_requested = False
        self._cancel_event = None
        self._show_progress_item = False
        self._reset_progress_summary()
        if result == download.DOWNLOAD_SUCCESS:
            self._set_status("Download complete")
            self._set_source_feedback(
                "Download complete. You can paste another URL anytime.",
                tone="success",
            )
            self._maybe_open_output_folder()
        elif result == download.DOWNLOAD_CANCELLED:
            self._set_status("Cancelled")
            self._set_source_feedback(
                "Download cancelled. Update settings or URL and try again.",
                tone="warning",
            )
            self._clear_last_output_path()
        else:
            self._set_status("Download failed")
            self._set_source_feedback(
                "Download failed. Check Logs and try again.",
                tone="error",
            )
            self._clear_last_output_path()
        self._update_controls_state()
        self._maybe_close_after_cancel()

    def _maybe_close_after_cancel(self) -> None:
        if self._is_downloading or not self._close_after_cancel:
            return
        self._close_after_cancel = False
        QTimer.singleShot(0, self.close)

    def _on_cancel(self) -> None:
        if not self._is_downloading or self._cancel_requested:
            return
        self._cancel_requested = True
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._set_status("Cancelling...")
        self._update_controls_state()

    def _on_add_to_queue(self) -> None:
        if self._is_downloading:
            return
        url = core_urls.strip_url_whitespace(self.url_edit.text().strip())

        settings = self._capture_queue_settings()
        issue = core_queue_logic.queue_add_issue(
            url=url,
            playlist_mode=bool(self._playlist_mode or core_urls.is_playlist_url(url)),
            formats_loaded=bool(self._filtered_lookup),
            settings=settings,
        )
        if issue:
            status_text, log_text = core_queue_logic.queue_add_feedback(issue)
            self._set_status(status_text)
            self._append_log(log_text)
            return

        self.queue_items.append(core_queue_logic.queue_item(url, settings))
        self._refresh_queue_panel()
        self._set_status("Added item to queue")
        self._update_controls_state()

    def _on_start_queue(self) -> None:
        self._start_queue_download()

    def _start_queue_download(self) -> None:
        queue_check = core_workflow.validate_queue_start(
            is_downloading=self._is_downloading,
            queue_items=self.queue_items,
        )
        if not queue_check.can_start:
            if queue_check.invalid_index is None or queue_check.invalid_issue is None:
                return
            QMessageBox.critical(
                self,
                "Missing settings",
                (
                    "Queue item "
                    f"{queue_check.invalid_index} is missing "
                    f"{core_queue_logic.queue_start_missing_detail(queue_check.invalid_issue)}."
                ),
            )
            return

        self.queue_active = True
        self.queue_index = 0
        self._queue_failed_items = 0
        self._is_downloading = True
        self._show_progress_item = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self._clear_logs()
        self._reset_progress_summary()
        self._clear_last_output_path()
        self._set_metrics_visible(True)
        self._set_status("Downloading queue...")
        self._set_source_feedback("Queue download in progress...", tone="loading")
        self._update_controls_state()
        self._refresh_queue_panel()
        self._start_next_queue_item()

    def _start_next_queue_item(self) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        next_item = core_workflow.next_queue_run_item(self.queue_items, self.queue_index)
        if next_item is None:
            self._finish_queue()
            return
        self.queue_index = next_item.index
        self._append_log(
            f"[queue] item {next_item.display_index}/{next_item.total} {next_item.url}"
        )
        self._set_current_item_display(
            progress=f"{next_item.display_index}/{next_item.total}",
            title="Resolving title...",
        )
        self._refresh_queue_panel()

        thread = threading.Thread(
            target=self._run_queue_download_worker,
            kwargs={
                "url": next_item.url,
                "settings": next_item.settings,
                "index": next_item.display_index,
                "total": next_item.total,
                "default_output_dir": self.output_dir_edit.text().strip(),
            },
            daemon=True,
        )
        thread.start()

    def _resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        return app_service.resolve_format_for_url(
            url=url,
            settings=settings,
            log=lambda msg: self._signals.log.emit(msg),
        )

    def _run_queue_download_worker(
        self,
        *,
        url: str,
        settings: QueueSettings,
        index: int,
        total: int,
        default_output_dir: str,
    ) -> None:
        had_error = False
        cancelled = False
        try:
            resolved = self._resolve_format_for_url(url, settings)
            item_text = f"{index}/{total} {resolved.get('title') or url}"
            self._signals.progress.emit({"status": "item", "item": item_text})

            request = app_service.build_queue_download_request(
                url=url,
                settings=settings,
                resolved=resolved,
                default_output_dir=default_output_dir,
            )

            if request["playlist_enabled"]:
                self._signals.log.emit(
                    f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}"
                )
            result = app_service.run_download_request(
                request=request,
                cancel_event=self._cancel_event,
                log=lambda msg: self._signals.log.emit(str(msg)),
                update_progress=lambda payload: self._signals.progress.emit(
                    dict(payload)
                ),
                record_output=lambda p: self._signals.record_output.emit(str(p), url),
                ensure_output_dir=True,
            )
            had_error = result == download.DOWNLOAD_ERROR
            cancelled = result == download.DOWNLOAD_CANCELLED
        except Exception as exc:
            had_error = True
            self._signals.log.emit(f"[queue] failed: {exc}")
        finally:
            self._signals.queue_item_done.emit(had_error, cancelled)

    def _on_queue_item_done(self, had_error: bool, cancelled: bool) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        progress = core_workflow.advance_queue_progress(
            queue_length=len(self.queue_items),
            current_index=self.queue_index,
            failed_items=self._queue_failed_items,
            cancel_requested=self._cancel_requested,
            had_error=had_error,
            cancelled=cancelled,
        )
        self._queue_failed_items = progress.failed_items
        self._cancel_requested = progress.cancel_requested
        if progress.should_finish:
            if progress.finish_cancelled:
                self._append_log("[queue] cancelled")
            self._finish_queue(cancelled=progress.finish_cancelled)
            return
        self.queue_index = progress.next_index
        if self.queue_index is None:
            self._append_log("[queue] cancelled")
            self._finish_queue()
            return
        self._reset_progress_summary()
        self._start_next_queue_item()

    def _finish_queue(self, *, cancelled: bool = False) -> None:
        failed_items = self._queue_failed_items
        self.queue_active = False
        self.queue_index = None
        self._queue_failed_items = 0
        self._is_downloading = False
        self._show_progress_item = False
        self._cancel_requested = False
        self._cancel_event = None

        outcome = core_workflow.queue_finish_outcome(
            cancelled=cancelled,
            failed_items=failed_items,
        )
        if outcome == "cancelled":
            self._append_log("[queue] stopped by cancellation")
            self._set_status("Queue cancelled")
            self._set_source_feedback(
                "Queue cancelled. You can adjust items and restart.",
                tone="warning",
            )
            self._clear_last_output_path()
        elif outcome == "failed":
            self._append_log(f"[queue] finished with {failed_items} failed item(s)")
            self._set_status("Queue finished with errors")
            self._set_source_feedback(
                "Queue finished with errors. Check Logs for failed items.",
                tone="warning",
            )
        else:
            self._append_log("[queue] finished successfully")
            self._set_status("Queue complete")
            self._set_source_feedback(
                "Queue complete. Paste another URL or review your history.",
                tone="success",
            )

        if outcome != "cancelled":
            self._maybe_open_output_folder()

        self._reset_progress_summary()
        self._update_controls_state()
        self._refresh_queue_panel()
        self._maybe_close_after_cancel()

    def _queue_selected_indices(self) -> list[int]:
        indices = sorted({idx.row() for idx in self.queue_list.selectedIndexes()})
        return [i for i in indices if 0 <= i < len(self.queue_items)]

    def _queue_remove_selected(self) -> None:
        if self.queue_active:
            return
        indices = self._queue_selected_indices()
        if not indices:
            return
        for idx in sorted(indices, reverse=True):
            self.queue_items.pop(idx)
        self._refresh_queue_panel()
        self._update_controls_state()

    def _queue_move_up(self) -> None:
        if self.queue_active:
            return
        indices = self._queue_selected_indices()
        moved = False
        for idx in indices:
            if idx <= 0 or idx >= len(self.queue_items):
                continue
            self.queue_items[idx - 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx - 1],
            )
            moved = True
        if moved:
            self._refresh_queue_panel()

    def _queue_move_down(self) -> None:
        if self.queue_active:
            return
        indices = self._queue_selected_indices()
        moved = False
        for idx in reversed(indices):
            if idx < 0 or idx >= len(self.queue_items) - 1:
                continue
            self.queue_items[idx + 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx + 1],
            )
            moved = True
        if moved:
            self._refresh_queue_panel()

    def _queue_clear(self) -> None:
        if self.queue_active:
            return
        if not self.queue_items:
            return
        self.queue_items.clear()
        self._refresh_queue_panel()
        self._update_controls_state()

    def _refresh_queue_panel(self) -> None:
        self.queue_list.clear()
        for idx, item in enumerate(self.queue_items, start=1):
            settings = item.get("settings") or {}
            mode = settings.get("mode") or "-"
            container = settings.get("format_filter") or "-"
            codec = settings.get("codec_filter") or "-"
            label = settings.get("format_label") or "-"
            prefix = ""
            if (
                self.queue_active
                and self.queue_index is not None
                and (idx - 1) == self.queue_index
            ):
                prefix = "> "
            text = f"{prefix}{idx}. {item.get('url', '')} [{mode}/{container}/{codec}] {label}"
            self.queue_list.addItem(text)

    def _on_record_output(self, output_path_raw: str, source_url: str) -> None:
        self._record_download_output(Path(output_path_raw), source_url)

    def _record_download_output(self, output_path: Path, source_url: str = "") -> None:
        recorded = app_service.record_history_output(
            history=self.download_history,
            seen_paths=self._history_seen_paths,
            output_path=output_path,
            source_url=source_url,
            max_entries=HISTORY_MAX_ENTRIES,
        )
        if not recorded:
            return
        self._set_last_output_path(output_path)
        self._refresh_history_panel()

    def _refresh_history_panel(self) -> None:
        self.history_list.clear()
        for item in self.download_history:
            timestamp = item.get("timestamp", "")
            name = item.get("name", "")
            self.history_list.addItem(f"{timestamp}  {name}")

    def _selected_history_item(self) -> HistoryItem | None:
        row = self.history_list.currentRow()
        if row < 0 or row >= len(self.download_history):
            return None
        return self.download_history[row]

    def _open_selected_history_file(self) -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_selected_history_folder(self) -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _clear_download_history(self) -> None:
        if not self.download_history:
            return
        self.download_history.clear()
        self._history_seen_paths.clear()
        self._refresh_history_panel()
        self._set_status("Download history cleared")

    def _stop_progress_animation(self) -> None:
        if self._progress_anim is None:
            return
        anim = self._progress_anim
        self._progress_anim = None
        if anim in self._active_animations:
            self._active_animations.remove(anim)
        anim.stop()
        anim.deleteLater()

    def _animate_progress_bar_to(self, percent: float, *, immediate: bool = False) -> None:
        clamped = max(0.0, min(100.0, float(percent)))
        target = int(round(clamped * 10))
        if immediate:
            self._stop_progress_animation()
            self.progress_bar.setValue(target)
            return
        if target == self.progress_bar.value():
            return
        self._stop_progress_animation()
        anim = QPropertyAnimation(self.progress_bar, b"value", self)
        anim.setDuration(220)
        anim.setStartValue(self.progress_bar.value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_anim = anim
        self._track_animation(anim)
        anim.start()

    def _reset_progress_summary(self) -> None:
        self._stop_progress_animation()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: -")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")
        self._set_current_item_display(progress="-", title="-")
        self._set_metrics_visible(False)

    def _on_progress_update(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        status = payload.get("status")
        if status == "downloading":
            self._set_metrics_visible(True)
            percent = payload.get("percent")
            speed = payload.get("speed")
            eta = payload.get("eta")
            playlist_eta = str(payload.get("playlist_eta") or "").strip()
            if isinstance(percent, (int, float)):
                self._animate_progress_bar_to(float(percent))
                self.progress_label.setText(f"Progress: {float(percent):.1f}%")
            if isinstance(speed, str):
                self.speed_label.setText(f"Speed: {speed or '-'}")
            eta_text = str(eta).strip() if isinstance(eta, str) else ""
            if playlist_eta:
                self.eta_label.setText(f"ETA: {eta_text or '-'} / {playlist_eta}")
            elif eta_text:
                self.eta_label.setText(f"ETA: {eta_text}")
            else:
                self.eta_label.setText("ETA: -")
        elif status == "item":
            if not self._show_progress_item:
                return
            item = str(payload.get("item") or "").strip()
            if item:
                self._set_current_item_from_text(item)
        elif status == "finished":
            # yt-dlp may emit "finished" for intermediate steps (e.g. one stream
            # before another starts). Do not force 100% here to avoid UI flicker.
            self.eta_label.setText("ETA: Finalizing")
        elif status == "cancelled":
            self._reset_progress_summary()

    def _export_diagnostics(self) -> None:
        timestamp = datetime.now()
        base_dir = Path(
            self.output_dir_edit.text().strip() or (Path.home() / "Downloads")
        ).expanduser()
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            base_dir = Path.home() / "Downloads"
            base_dir.mkdir(parents=True, exist_ok=True)

        output_path = base_dir / f"yt-dlp-gui-diagnostics-{timestamp:%Y%m%d-%H%M%S}.txt"
        options = self._snapshot_download_options()
        payload = diagnostics.build_report_payload(
            generated_at=timestamp,
            status=self.status_value.text(),
            simple_state=self.status_value.text(),
            url=self.url_edit.text(),
            mode=self._current_mode(),
            container=self._current_container(),
            codec=self._current_codec(),
            format_label=self._selected_format_label(),
            queue_items=self.queue_items,
            queue_active=self.queue_active,
            is_downloading=self._is_downloading,
            preview_title=self.preview_value.text(),
            options=options,
            history_items=self.download_history,
            logs_text="\n".join(self._log_lines),
        )
        try:
            output_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Diagnostics export failed", str(exc))
            return
        self._append_log(f"[diag] exported {output_path}")
        self._set_status("Diagnostics exported")
        QMessageBox.information(
            self, "Diagnostics exported", f"Saved to:\n{output_path}"
        )

    def _update_controls_state(self) -> None:
        url_present = bool(self.url_edit.text().strip())
        has_formats_data = bool(self._video_labels or self._audio_labels)
        mode = self._current_mode()
        container_value = self._current_container()
        if mode == "audio" and container_value not in AUDIO_CONTAINERS:
            container_value = ""
        is_playlist_url = self._playlist_mode or core_urls.is_playlist_url(
            self.url_edit.text().strip()
        )
        state = core_ui_state.compute_control_state(
            url_present=url_present,
            has_formats_data=has_formats_data,
            mode=mode,
            container_value=container_value,
            codec_value=self._current_codec(),
            format_available=bool(self._filtered_labels),
            format_selected=bool(self._selected_format_label()),
            queue_ready=bool(self.queue_items),
            queue_active=self.queue_active,
            is_fetching=self._is_fetching,
            is_downloading=self._is_downloading,
            cancel_requested=self._cancel_requested,
            is_playlist_url=is_playlist_url,
            mixed_prompt_active=False,
            playlist_items_requested=bool(self._playlist_mode),
            write_subtitles_requested=bool(self.write_subtitles_check.isChecked()),
            allow_queue_input_context=False,
            audio_containers=AUDIO_CONTAINERS,
            video_containers=VIDEO_CONTAINERS,
        )

        self.start_button.setEnabled(state.can_start_single)
        self.add_queue_button.setEnabled(state.can_add_queue)
        self.start_queue_button.setEnabled(state.can_start_queue)
        self.cancel_button.setEnabled(state.can_cancel)

        self.video_radio.setEnabled(state.mode_enabled)
        self.audio_radio.setEnabled(state.mode_enabled)

        self.container_combo.setEnabled(state.container_enabled)
        self.codec_combo.setEnabled(state.codec_enabled)
        self.convert_check.setEnabled(state.convert_enabled)
        if not self.convert_check.isEnabled():
            self.convert_check.setChecked(False)

        self.format_combo.setEnabled(state.format_enabled)

        self.playlist_items_edit.setEnabled(state.playlist_items_enabled)
        self.filename_edit.setEnabled(state.filename_enabled)

        self.url_edit.setEnabled(state.input_fields_enabled)
        self.paste_button.setEnabled(state.input_fields_enabled)
        self.sample_url_button.setEnabled(state.input_fields_enabled)
        self.browse_button.setEnabled(state.input_fields_enabled)
        mixed_actions_enabled = state.input_fields_enabled and bool(self._pending_mixed_url)
        self.use_single_video_url_button.setEnabled(mixed_actions_enabled)
        self.use_playlist_url_button.setEnabled(mixed_actions_enabled)

        self.subtitle_languages_edit.setEnabled(state.subtitle_controls_enabled)
        self.write_subtitles_check.setEnabled(state.subtitle_controls_enabled)
        self.embed_subtitles_check.setEnabled(state.embed_allowed)
        if not state.embed_allowed:
            self.embed_subtitles_check.setChecked(False)

        self.audio_language_combo.setEnabled(state.input_fields_enabled)
        self.network_timeout_edit.setEnabled(state.input_fields_enabled)
        self.network_retries_edit.setEnabled(state.input_fields_enabled)
        self.retry_backoff_edit.setEnabled(state.input_fields_enabled)
        self.concurrent_fragments_edit.setEnabled(state.input_fields_enabled)

        has_last_output = (self._latest_output_path is not None) and (
            not self._is_downloading
        )
        self.download_result_card.setVisible(has_last_output)
        if has_last_output:
            self._refresh_last_output_text()
        self.open_last_output_folder_button.setEnabled(
            has_last_output and bool(self._latest_output_path and self._latest_output_path.parent.exists())
        )
        self.copy_output_path_button.setEnabled(has_last_output)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._normalize_input_widths()
        self._apply_responsive_layout()
        self._layout_mixed_url_overlay()
        if self._is_downloading:
            self._set_metrics_visible(True)
        if self._latest_output_path is not None:
            self._refresh_last_output_text()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_user_settings()
        if not self._is_downloading:
            event.accept()
            return
        if self._cancel_requested:
            force_quit = QMessageBox.question(
                self,
                "Cancellation in progress",
                (
                    "A download is still shutting down.\n\n"
                    "Force close now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if force_quit == QMessageBox.StandardButton.Yes:
                event.accept()
                return
            event.ignore()
            return

        choice = QMessageBox.question(
            self,
            "Download in progress",
            (
                "A download is currently running.\n\n"
                "Cancel the download and close when it stops?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            self._close_after_cancel = True
            self._on_cancel()
        event.ignore()


def main() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication([])
    assert app is not None
    sigint_pump: QTimer | None = None

    # Ensure Ctrl+C from a terminal cleanly exits the Qt event loop.
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, lambda _sig, _frame: app.quit())
        sigint_pump = QTimer()
        sigint_pump.setInterval(100)
        sigint_pump.timeout.connect(lambda: None)
        sigint_pump.start()

    window = QtYtDlpGui()
    setattr(window, "_sigint_pump", sigint_pump)
    window.show()
    if owns_app:
        return int(app.exec())
    return 0
