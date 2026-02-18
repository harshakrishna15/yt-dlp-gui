from __future__ import annotations

import signal
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
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
    QPushButton,
    QRadioButton,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import (
    diagnostics,
    download,
    format_pipeline,
    formats as formats_mod,
    history_store,
    qt_panels,
    qt_style,
    yt_dlp_helpers as helpers,
)
from .core import download_plan as core_download_plan
from .core import format_selection as core_format_selection
from .core import options as core_options
from .core import queue_logic as core_queue_logic
from .core import urls as core_urls
from .qt_state import PREVIEW_TITLE_TOOLTIP_DEFAULT, preview_title_fields
from .qt_widgets import _NativeComboBox, _PanelSelectorComboBox, _QtSignals
from .shared_types import DownloadOptions, DownloadRequest, HistoryItem, QueueItem, QueueSettings

VIDEO_CONTAINERS = ("mp4", "webm")
AUDIO_CONTAINERS = ("m4a", "mp3", "opus", "wav", "flac")
CODECS = ("avc1", "av01")

FETCH_DEBOUNCE_MS = 600
HISTORY_MAX_ENTRIES = 250
LOG_MAX_LINES = 1000
PANEL_SELECTOR_PLACEHOLDER = "Panel"

def _is_playlist_url(url: str) -> bool:
    return core_urls.is_playlist_url(url)


def _is_mixed_url(url: str) -> bool:
    return core_urls.is_mixed_url(url)


def _strip_list_param(url: str) -> str:
    return core_urls.strip_list_param(url)


def _to_playlist_url(url: str) -> str:
    return core_urls.to_playlist_url(url)


def _strip_url_whitespace(url: str) -> str:
    return core_urls.strip_url_whitespace(url)


class QtYtDlpGui(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("yt-dlp-gui (Qt)")
        self.resize(1080, 780)
        self._native_combos: list[QComboBox] = []

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
        self._last_mixed_prompt_url = ""

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

        self._build_ui()
        self._set_preview_title("")
        self._set_audio_language_values([])
        self._set_mode_unselected()
        self._apply_header_layout()
        self._update_controls_state()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(10)

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        brand_col = QWidget(header)
        brand_layout = QVBoxLayout(brand_col)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)
        title = QLabel("yt-dlp-gui", brand_col)
        title.setObjectName("titleLabel")
        subtitle = QLabel("Qt frontend with Tk feature parity.", brand_col)
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
        self.settings_button = QPushButton("Settings", self.classic_actions)
        self.queue_button = QPushButton("Queue", self.classic_actions)
        self.history_button = QPushButton("History", self.classic_actions)
        self.logs_button = QPushButton("Logs", self.classic_actions)
        for button in (
            self.settings_button,
            self.queue_button,
            self.history_button,
            self.logs_button,
        ):
            button.setCheckable(True)
            classic_layout.addWidget(button)

        self.simple_panel_selector = _PanelSelectorComboBox(self.top_actions)
        self._register_native_combo(self.simple_panel_selector)
        self.simple_panel_selector.setObjectName("topPanelSelector")
        panel_selector_view = QListView(self.simple_panel_selector)
        panel_selector_view.setObjectName("topPanelSelectorView")
        panel_selector_view.setFrameShape(QFrame.Shape.NoFrame)
        panel_selector_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        panel_selector_view.viewport().setAutoFillBackground(True)
        panel_selector_view.setMinimumWidth(240)
        self.simple_panel_selector.setView(panel_selector_view)
        self.simple_panel_selector.setMaxVisibleItems(4)
        panel_selector_view.setMouseTracking(True)
        panel_selector_view.viewport().setMouseTracking(True)
        self.simple_panel_selector.addItems(
            [
                PANEL_SELECTOR_PLACEHOLDER,
                "Queue",
                "History",
                "Logs",
            ]
        )
        self._fit_combo_popup_to_contents(
            self.simple_panel_selector, min_width=280, padding=48
        )
        self.simple_settings_button = QPushButton("Settings", self.top_actions)
        self.simple_settings_button.setCheckable(True)

        top_actions_layout.addWidget(self.classic_actions)
        top_actions_layout.addWidget(self.simple_panel_selector)
        top_actions_layout.addWidget(self.simple_settings_button)

        header_layout.addWidget(brand_col, stretch=1)
        header_layout.addWidget(self.top_actions)
        root_layout.addWidget(header)

        self.panel_stack = QStackedWidget(self)
        root_layout.addWidget(self.panel_stack, stretch=1)

        self.main_page = QWidget(self.panel_stack)
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        source = QGroupBox("1. Source", self.main_page)
        source.setObjectName("sourceSection")
        source_layout = QFormLayout(source)
        source_layout.setContentsMargins(12, 14, 12, 10)
        source_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        source_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        source_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        source_layout.setHorizontalSpacing(14)
        source_layout.setVerticalSpacing(10)

        url_row = QWidget(source)
        url_row_layout = QHBoxLayout(url_row)
        url_row_layout.setContentsMargins(0, 0, 0, 0)
        url_row_layout.setSpacing(8)
        self.url_edit = QLineEdit(source)
        self.url_edit.setPlaceholderText("Paste video or playlist URL")
        self.url_edit.textChanged.connect(self._on_url_changed)
        self.paste_button = QPushButton("Paste", source)
        self.paste_button.clicked.connect(self._paste_url)
        url_row_layout.addWidget(self.url_edit, stretch=1)
        url_row_layout.addWidget(self.paste_button)
        source_layout.addRow("Video URL", url_row)

        self.playlist_items_edit = QLineEdit(source)
        self.playlist_items_edit.setPlaceholderText("Optional: 1-5,7,10-")
        source_layout.addRow("Playlist items", self.playlist_items_edit)

        self.preview_value = QLabel("-", source)
        self.preview_value.setWordWrap(False)
        self.preview_value.setMinimumHeight(38)
        source_layout.addRow("Preview title", self.preview_value)
        main_layout.addWidget(source)

        output = QGroupBox("2. Output", self.main_page)
        output.setObjectName("outputSection")
        output_layout = QGridLayout(output)
        output_layout.setContentsMargins(12, 14, 12, 10)
        output_layout.setHorizontalSpacing(14)
        output_layout.setVerticalSpacing(10)
        output_layout.setColumnStretch(0, 1)
        output_layout.setColumnStretch(1, 1)

        format_card = QGroupBox("Format setup", output)
        format_card.setObjectName("formatSection")
        format_layout = QFormLayout(format_card)
        format_layout.setContentsMargins(12, 14, 12, 10)
        format_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        format_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        format_layout.setHorizontalSpacing(14)
        format_layout.setVerticalSpacing(10)

        mode_row = QWidget(format_card)
        mode_row_layout = QHBoxLayout(mode_row)
        mode_row_layout.setContentsMargins(0, 0, 0, 0)
        self.video_radio = QRadioButton("Video and Audio", mode_row)
        self.audio_radio = QRadioButton("Audio only", mode_row)
        self.video_radio.toggled.connect(self._on_mode_change)
        self.audio_radio.toggled.connect(self._on_mode_change)
        mode_row_layout.addWidget(self.video_radio)
        mode_row_layout.addWidget(self.audio_radio)
        mode_row_layout.addStretch(1)
        format_layout.addRow("Content type", mode_row)

        container_row = QWidget(format_card)
        container_row_layout = QHBoxLayout(container_row)
        container_row_layout.setContentsMargins(0, 0, 0, 0)
        container_row_layout.setSpacing(0)
        self.container_combo = _NativeComboBox(container_row)
        self._register_native_combo(self.container_combo)
        self.container_combo.setMinimumWidth(190)
        self.container_combo.currentIndexChanged.connect(self._on_container_change)
        self.convert_check = QCheckBox("Convert WebM to MP4", format_card)
        self.convert_check.stateChanged.connect(
            lambda _state: self._update_controls_state()
        )
        container_row_layout.addWidget(self.container_combo)
        format_layout.addRow("Container", container_row)
        format_layout.addRow("Post-process", self.convert_check)

        self.codec_combo = _NativeComboBox(format_card)
        self._register_native_combo(self.codec_combo)
        self.codec_combo.setMinimumWidth(190)
        self.codec_combo.addItem("Select codec", "")
        self.codec_combo.addItem("avc1 (H.264)", "avc1")
        self.codec_combo.addItem("av01 (AV1)", "av01")
        self.codec_combo.currentIndexChanged.connect(self._on_codec_change)
        format_layout.addRow("Codec", self.codec_combo)

        self.format_combo = _NativeComboBox(format_card)
        self._register_native_combo(self.format_combo)
        self.format_combo.setMinimumWidth(260)
        self.format_combo.currentIndexChanged.connect(
            lambda _idx: self._update_controls_state()
        )
        format_layout.addRow("Format", self.format_combo)

        save_card = QGroupBox("Save options", output)
        save_card.setObjectName("saveSection")
        save_layout = QFormLayout(save_card)
        save_layout.setContentsMargins(12, 14, 12, 10)
        save_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        save_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        save_layout.setHorizontalSpacing(14)
        save_layout.setVerticalSpacing(10)
        self.filename_edit = QLineEdit(save_card)
        self.filename_edit.setPlaceholderText("Optional single-video filename")
        save_layout.addRow("File name", self.filename_edit)

        folder_row = QWidget(save_card)
        folder_row_layout = QHBoxLayout(folder_row)
        folder_row_layout.setContentsMargins(0, 0, 0, 0)
        folder_row_layout.setSpacing(8)
        self.output_dir_edit = QLineEdit(str(Path.home() / "Downloads"), save_card)
        self.output_dir_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...", save_card)
        self.browse_button.clicked.connect(self._pick_folder)
        folder_row_layout.addWidget(self.output_dir_edit, stretch=1)
        folder_row_layout.addWidget(self.browse_button)
        save_layout.addRow("Output folder", folder_row)

        self._harmonize_form_label_widths(
            [format_layout, save_layout], min_width=112
        )

        output_layout.addWidget(format_card, 0, 0)
        output_layout.addWidget(save_card, 0, 1)
        main_layout.addWidget(output)

        run = QGroupBox("3. Run", self.main_page)
        run.setObjectName("runSection")
        run_layout = QVBoxLayout(run)
        run_layout.setContentsMargins(12, 14, 12, 10)
        run_layout.setSpacing(10)
        self.status_value = QLabel("Idle", run)
        self.status_value.setObjectName("statusLine")
        run_layout.addWidget(self.status_value)

        buttons_row = QWidget(run)
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        self.start_button = QPushButton("Download", buttons_row)
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

        metrics = QFrame(run)
        metrics.setObjectName("metricsStrip")
        metrics_layout = QHBoxLayout(metrics)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(12)
        self.progress_label = QLabel("Progress: -", metrics)
        self.speed_label = QLabel("Speed: -", metrics)
        self.eta_label = QLabel("ETA: -", metrics)
        metrics_layout.addWidget(self.progress_label)
        metrics_layout.addWidget(self.speed_label)
        metrics_layout.addWidget(self.eta_label)
        metrics_layout.addStretch(1)
        run_layout.addWidget(metrics)

        self.item_label = QLabel("Current item: -", run)
        run_layout.addWidget(self.item_label)

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
            "settings": self.settings_button,
            "queue": self.queue_button,
            "history": self.history_button,
            "logs": self.logs_button,
        }

        self.settings_button.clicked.connect(
            lambda _checked: self._toggle_panel("settings")
        )
        self.simple_settings_button.clicked.connect(
            lambda _checked: self._toggle_panel("settings")
        )
        self.queue_button.clicked.connect(lambda _checked: self._toggle_panel("queue"))
        self.history_button.clicked.connect(
            lambda _checked: self._toggle_panel("history")
        )
        self.logs_button.clicked.connect(lambda _checked: self._toggle_panel("logs"))
        self.simple_panel_selector.currentTextChanged.connect(
            self._on_simple_selector_changed
        )

        combo_arrow_path = (
            Path(__file__).resolve().parent / "assets" / "combo-down-arrow.svg"
        ).as_posix()
        self.setStyleSheet(qt_style.build_stylesheet(combo_arrow_path))
        self._normalize_control_sizing()
        self._install_tooltips()

    def _register_native_combo(self, combo: QComboBox) -> None:
        combo.setMinimumHeight(38)
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

    def _set_uniform_button_width(
        self, buttons: list[QPushButton], *, extra_px: int = 28
    ) -> None:
        live = [btn for btn in buttons if btn is not None]
        if not live:
            return
        metrics = QFontMetrics(live[0].font())
        width = max(metrics.horizontalAdvance(btn.text()) for btn in live) + extra_px
        for button in live:
            button.setMinimumWidth(width)

    def _normalize_control_sizing(self) -> None:
        control_height = 38
        for edit in (
            self.url_edit,
            self.playlist_items_edit,
            self.filename_edit,
            self.output_dir_edit,
            self.subtitle_languages_edit,
            self.network_timeout_edit,
            self.network_retries_edit,
            self.retry_backoff_edit,
        ):
            edit.setMinimumHeight(control_height)

        for combo in (
            self.simple_panel_selector,
            self.container_combo,
            self.codec_combo,
            self.format_combo,
            self.audio_language_combo,
            self.ui_layout_combo,
        ):
            combo.setMinimumHeight(control_height)

        for button in (
            self.settings_button,
            self.simple_settings_button,
            self.queue_button,
            self.history_button,
            self.logs_button,
            self.paste_button,
            self.browse_button,
            self.start_button,
            self.add_queue_button,
            self.start_queue_button,
            self.cancel_button,
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

        self._set_uniform_button_width(
            [
                self.settings_button,
                self.simple_settings_button,
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
        self._normalize_input_widths()

    def _normalize_input_widths(self) -> None:
        field_width = 500
        dropdown_width = 280
        panel_width = 220
        small_field_width = 120

        self.simple_panel_selector.setMinimumWidth(panel_width)
        self.url_edit.setMinimumWidth(field_width)
        self.playlist_items_edit.setMinimumWidth(field_width)
        self.filename_edit.setMinimumWidth(field_width)
        self.output_dir_edit.setMinimumWidth(field_width)
        self.subtitle_languages_edit.setMinimumWidth(field_width)

        self.container_combo.setMinimumWidth(dropdown_width)
        self.codec_combo.setMinimumWidth(dropdown_width)
        self.format_combo.setMinimumWidth(dropdown_width)
        self.audio_language_combo.setMinimumWidth(dropdown_width)
        self.ui_layout_combo.setMinimumWidth(dropdown_width)

        self.network_timeout_edit.setFixedWidth(small_field_width)
        self.network_retries_edit.setFixedWidth(small_field_width)
        self.retry_backoff_edit.setFixedWidth(small_field_width)

    def _install_tooltips(self) -> None:
        self.simple_panel_selector.setToolTip(
            "Switch between Panel, Queue, History, and Logs."
        )
        self.settings_button.setToolTip("Open settings view.")
        self.simple_settings_button.setToolTip("Open settings view.")
        self.queue_button.setToolTip("Open queue manager view.")
        self.history_button.setToolTip("Open download history view.")
        self.logs_button.setToolTip("Open logs view.")

        self.url_edit.setToolTip("Paste a video or playlist URL.")
        self.paste_button.setToolTip("Paste URL from clipboard.")
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
        self.ui_layout_combo.setToolTip("Simple: panel dropdown. Classic: top buttons.")
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

    def _build_settings_panel(self) -> QWidget:
        return qt_panels.build_settings_panel(self)

    def _build_queue_panel(self) -> QWidget:
        return qt_panels.build_queue_panel(self)

    def _build_history_panel(self) -> QWidget:
        return qt_panels.build_history_panel(self)

    def _build_logs_panel(self) -> QWidget:
        return qt_panels.build_logs_panel(self, max_lines=LOG_MAX_LINES)

    def _apply_header_layout(self) -> None:
        mode = self.ui_layout_combo.currentText().strip().lower()
        use_classic = mode == "classic"
        self.classic_actions.setVisible(use_classic)
        self.simple_panel_selector.setVisible(not use_classic)
        self.simple_settings_button.setVisible(not use_classic)
        if not use_classic:
            label = PANEL_SELECTOR_PLACEHOLDER
            if self._active_panel_name in {"queue", "history", "logs"}:
                label = self._active_panel_name.title()
            self.simple_panel_selector.blockSignals(True)
            self.simple_panel_selector.setCurrentText(label)
            self.simple_panel_selector.blockSignals(False)
            self.simple_settings_button.setChecked(self._active_panel_name == "settings")

    def _on_simple_selector_changed(self, text: str) -> None:
        label = (text or "").strip().lower()
        if label in {"", PANEL_SELECTOR_PLACEHOLDER.lower()}:
            self._close_panel()
            return
        if label in {"queue", "history", "logs"}:
            self._open_panel(label)

    def _toggle_panel(self, name: str) -> None:
        if self._active_panel_name == name:
            self._close_panel()
            return
        self._open_panel(name)

    def _open_panel(self, name: str) -> None:
        index = self._panel_name_to_index.get(name)
        if index is None:
            return
        self.panel_stack.setCurrentIndex(index)
        self._active_panel_name = name
        for panel_name, button in self._panel_buttons.items():
            button.setChecked(panel_name == name)
        self.simple_settings_button.setChecked(name == "settings")
        if not self.classic_actions.isVisible():
            label = PANEL_SELECTOR_PLACEHOLDER
            if name in {"queue", "history", "logs"}:
                label = name.title()
            self.simple_panel_selector.blockSignals(True)
            self.simple_panel_selector.setCurrentText(label)
            self.simple_panel_selector.blockSignals(False)

    def _close_panel(self) -> None:
        self.panel_stack.setCurrentIndex(self._main_page_index)
        self._active_panel_name = None
        for button in self._panel_buttons.values():
            button.setChecked(False)
        self.simple_settings_button.setChecked(False)
        if not self.classic_actions.isVisible():
            self.simple_panel_selector.blockSignals(True)
            self.simple_panel_selector.setCurrentText(PANEL_SELECTOR_PLACEHOLDER)
            self.simple_panel_selector.blockSignals(False)

    def _append_log(self, text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        self._log_lines.append(clean)
        if len(self._log_lines) > LOG_MAX_LINES:
            self._log_lines = self._log_lines[-LOG_MAX_LINES:]
        self.logs_view.appendPlainText(clean)

    def _clear_logs(self) -> None:
        self._log_lines.clear()
        self.logs_view.clear()

    def _set_status(self, text: str, *, log: bool = True) -> None:
        value = (text or "").strip() or "Idle"
        self.status_value.setText(value)
        if log:
            self._append_log(f"[status] {value}")

    def _set_preview_title(self, title: str) -> None:
        shown, tooltip = preview_title_fields(title)
        self.preview_value.setText(shown)
        self.preview_value.setToolTip(tooltip)

    def _resolve_mixed_url_choice(self, url: str) -> str:
        choice = QMessageBox.question(
            self,
            "Mixed URL detected",
            (
                "This URL contains both a video and playlist ID.\n\n"
                "Yes: use playlist URL\n"
                "No: use single-video URL"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Yes:
            return _to_playlist_url(url)
        return _strip_list_param(url)

    def _paste_url(self) -> None:
        clip = QApplication.clipboard().text().strip()
        if not clip:
            self._set_status("Clipboard is empty")
            return
        self.url_edit.setText(_strip_url_whitespace(clip))
        self._set_status("URL pasted")

    def _pick_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select output folder")
        if selected:
            self.output_dir_edit.setText(selected)

    def _on_url_changed(self) -> None:
        current = self.url_edit.text()
        normalized = _strip_url_whitespace(current)
        if normalized != current:
            self.url_edit.blockSignals(True)
            self.url_edit.setText(normalized)
            self.url_edit.blockSignals(False)
        if normalized and _is_mixed_url(normalized):
            if normalized != self._last_mixed_prompt_url:
                self._last_mixed_prompt_url = normalized
                resolved = self._resolve_mixed_url_choice(normalized)
                resolved = _strip_url_whitespace(resolved)
                if resolved and resolved != normalized:
                    self.url_edit.blockSignals(True)
                    self.url_edit.setText(resolved)
                    self.url_edit.blockSignals(False)
                    normalized = resolved
        else:
            self._last_mixed_prompt_url = ""

        self._fetch_timer.stop()
        self._fetch_request_seq += 1
        self._active_fetch_request_id = self._fetch_request_seq
        self._is_fetching = False
        self._playlist_mode = _is_playlist_url(normalized)

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

        if normalized and not self._is_downloading:
            self._fetch_timer.start()
        self._update_controls_state()

    def _start_fetch_formats(self) -> None:
        if self._is_downloading:
            return
        url = self.url_edit.text().strip()
        if not url:
            return
        self._fetch_request_seq += 1
        request_id = self._fetch_request_seq
        self._active_fetch_request_id = request_id
        self._is_fetching = True
        self._set_status("Fetching formats...")
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
        else:
            self._set_status("No formats found")
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

    @staticmethod
    def _codec_matches_preference(vcodec_raw: str, codec_pref: str) -> bool:
        return core_format_selection.codec_matches_preference(vcodec_raw, codec_pref)

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
        return core_options.build_download_options(
            network_timeout_raw=self.network_timeout_edit.text(),
            network_retries_raw=self.network_retries_edit.text(),
            retry_backoff_raw=self.retry_backoff_edit.text(),
            subtitle_languages_raw=self.subtitle_languages_edit.text(),
            write_subtitles_requested=bool(self.write_subtitles_check.isChecked()),
            embed_subtitles_requested=bool(self.embed_subtitles_check.isChecked()),
            is_video_mode=self._current_mode() == "video",
            audio_language_raw=self.audio_language_combo.currentText(),
            custom_filename_raw=self.filename_edit.text(),
            timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
            retries_default=download.YDL_ATTEMPT_RETRIES,
            backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
        )

    def _capture_queue_settings(self) -> QueueSettings:
        fmt_label = self._selected_format_label()
        fmt_info = self._selected_format_info() or {}
        estimated_size = helpers.humanize_bytes(
            helpers.estimate_filesize_bytes(fmt_info)
        )
        options = self._snapshot_download_options()
        return core_options.build_queue_settings(
            mode=self._current_mode(),
            format_filter=self._current_container(),
            codec_filter=self._current_codec(),
            convert_to_mp4=bool(self.convert_check.isChecked()),
            format_label=fmt_label,
            estimated_size=estimated_size,
            output_dir=self.output_dir_edit.text().strip(),
            playlist_items=self.playlist_items_edit.text(),
            options=options,
        )

    def _on_start(self) -> None:
        if self._is_downloading:
            return
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.critical(
                self, "Missing URL", "Please paste a video URL to download."
            )
            return
        if not self._filtered_lookup:
            QMessageBox.critical(
                self, "Formats unavailable", "Formats have not been loaded yet."
            )
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
        self._set_status("Downloading...")
        self._update_controls_state()

        request = core_download_plan.build_single_download_request(
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
        thread = threading.Thread(
            target=self._run_single_download_worker,
            kwargs={"request": request},
            daemon=True,
        )
        thread.start()

    def _run_single_download_worker(self, *, request: DownloadRequest) -> None:
        result = download.run_download(
            url=request["url"],
            output_dir=request["output_dir"],
            fmt_info=request["fmt_info"],
            fmt_label=request["fmt_label"],
            format_filter=request["format_filter"],
            convert_to_mp4=request["convert_to_mp4"],
            playlist_enabled=request["playlist_enabled"],
            playlist_items=request["playlist_items"],
            cancel_event=self._cancel_event,
            log=lambda msg: self._signals.log.emit(str(msg)),
            update_progress=lambda payload: self._signals.progress.emit(dict(payload)),
            network_timeout_s=int(request["network_timeout_s"]),
            network_retries=int(request["network_retries"]),
            retry_backoff_s=float(request["retry_backoff_s"]),
            subtitle_languages=list(request["subtitle_languages"]),
            write_subtitles=bool(request["write_subtitles"]),
            embed_subtitles=bool(request["embed_subtitles"]),
            audio_language=str(request["audio_language"]),
            custom_filename=str(request["custom_filename"]),
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
        elif result == download.DOWNLOAD_CANCELLED:
            self._set_status("Cancelled")
        else:
            self._set_status("Download failed")
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
        url = _strip_url_whitespace(self.url_edit.text().strip())

        settings = self._capture_queue_settings()
        issue = core_queue_logic.queue_add_issue(
            url=url,
            playlist_mode=bool(self._playlist_mode or _is_playlist_url(url)),
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
        if self._is_downloading or not self.queue_items:
            return
        invalid = core_queue_logic.first_invalid_queue_item(self.queue_items)
        if invalid is not None:
            idx, issue = invalid
            QMessageBox.critical(
                self,
                "Missing settings",
                (
                    "Queue item "
                    f"{idx} is missing {core_queue_logic.queue_start_missing_detail(issue)}."
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
        self._set_status("Downloading queue...")
        self._update_controls_state()
        self._refresh_queue_panel()
        self._start_next_queue_item()

    def _start_next_queue_item(self) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        next_index = core_queue_logic.next_non_empty_queue_index(
            self.queue_items, self.queue_index
        )
        if next_index is None:
            self._finish_queue()
            return
        self.queue_index = next_index

        item = self.queue_items[self.queue_index]
        url = str(item.get("url", "")).strip()
        settings = item.get("settings") or {}
        total = len(self.queue_items)
        self._append_log(f"[queue] item {self.queue_index + 1}/{total} {url}")
        self.item_label.setText(f"Current item: {self.queue_index + 1}/{total}")
        self._refresh_queue_panel()

        thread = threading.Thread(
            target=self._run_queue_download_worker,
            kwargs={
                "url": url,
                "settings": settings,
                "index": self.queue_index + 1,
                "total": total,
                "default_output_dir": self.output_dir_edit.text().strip(),
            },
            daemon=True,
        )
        thread.start()

    def _resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        info = helpers.fetch_info(url)
        formats = formats_mod.formats_from_info(info)
        return core_format_selection.resolve_format_for_info(
            info=info,
            formats=formats,
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

            request = core_download_plan.build_queue_download_request(
                url=url,
                settings=settings,
                resolved=resolved,
                default_output_dir=default_output_dir,
                timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
                retries_default=download.YDL_ATTEMPT_RETRIES,
                backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
            )
            output_dir = request["output_dir"]
            output_dir.mkdir(parents=True, exist_ok=True)

            result = download.run_download(
                url=request["url"],
                output_dir=output_dir,
                fmt_info=request["fmt_info"],
                fmt_label=request["fmt_label"],
                format_filter=request["format_filter"],
                convert_to_mp4=bool(request["convert_to_mp4"]),
                playlist_enabled=bool(request["playlist_enabled"]),
                playlist_items=request["playlist_items"],
                cancel_event=self._cancel_event,
                log=lambda msg: self._signals.log.emit(str(msg)),
                update_progress=lambda payload: self._signals.progress.emit(
                    dict(payload)
                ),
                network_retries=int(request["network_retries"]),
                network_timeout_s=int(request["network_timeout_s"]),
                retry_backoff_s=float(request["retry_backoff_s"]),
                subtitle_languages=list(request["subtitle_languages"]),
                write_subtitles=bool(request["write_subtitles"]),
                embed_subtitles=bool(request["embed_subtitles"]),
                audio_language=str(request["audio_language"]),
                custom_filename=str(request["custom_filename"]),
                record_output=lambda p: self._signals.record_output.emit(str(p), url),
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
        if had_error:
            self._queue_failed_items += 1
        if cancelled:
            self._cancel_requested = True
        if self._cancel_requested:
            self._append_log("[queue] cancelled")
            self._finish_queue(cancelled=True)
            return
        self.queue_index += 1
        if self.queue_index >= len(self.queue_items):
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

        if cancelled:
            self._append_log("[queue] stopped by cancellation")
            self._set_status("Queue cancelled")
        elif failed_items:
            self._append_log(f"[queue] finished with {failed_items} failed item(s)")
            self._set_status("Queue finished with errors")
        else:
            self._append_log("[queue] finished successfully")
            self._set_status("Queue complete")

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
        normalized = history_store.normalize_output_path(output_path)
        if not normalized:
            return
        history_store.upsert_history_entry(
            self.download_history,
            self._history_seen_paths,
            normalized_path=normalized,
            source_url=source_url,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            max_entries=HISTORY_MAX_ENTRIES,
        )
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

    def _reset_progress_summary(self) -> None:
        self.progress_label.setText("Progress: -")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")
        self.item_label.setText("Current item: -")

    def _on_progress_update(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        status = payload.get("status")
        if status == "downloading":
            percent = payload.get("percent")
            speed = payload.get("speed")
            eta = payload.get("eta")
            if isinstance(percent, (int, float)):
                self.progress_label.setText(f"Progress: {float(percent):.1f}%")
            if isinstance(speed, str):
                self.speed_label.setText(f"Speed: {speed or '-'}")
            if isinstance(eta, str) and eta.strip():
                self.eta_label.setText(f"ETA: {eta}")
        elif status == "item":
            if not self._show_progress_item:
                return
            item = str(payload.get("item") or "").strip()
            if item:
                self.item_label.setText(f"Current item: {item}")
        elif status == "finished":
            self.progress_label.setText("Progress: 100.0%")
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
        is_audio_mode = mode == "audio"
        is_video_mode = mode == "video"
        mode_chosen = is_audio_mode or is_video_mode
        container_value = self._current_container()
        if is_audio_mode and container_value not in AUDIO_CONTAINERS:
            container_value = ""
        filter_chosen = container_value in (
            AUDIO_CONTAINERS if is_audio_mode else VIDEO_CONTAINERS
        )
        codec_chosen = bool(self._current_codec())
        format_available = bool(self._filtered_labels)
        format_selected = bool(self._selected_format_label())
        queue_ready = bool(self.queue_items)

        base_ready = (
            (not self._is_fetching) and (not self._is_downloading) and mode_chosen
        )
        single_ready = base_ready and url_present and has_formats_data

        can_start_single = (
            single_ready
            and filter_chosen
            and format_selected
            and (is_audio_mode or codec_chosen)
        )
        is_playlist_url = self._playlist_mode or _is_playlist_url(
            self.url_edit.text().strip()
        )
        can_add_queue = can_start_single and (not is_playlist_url)
        can_start_queue = queue_ready and (not self._is_downloading)
        can_cancel = self._is_downloading and (not self._cancel_requested)

        self.start_button.setEnabled(can_start_single)
        self.add_queue_button.setEnabled(can_add_queue and not self.queue_active)
        self.start_queue_button.setEnabled(can_start_queue)
        self.cancel_button.setEnabled(can_cancel)

        mode_enabled = url_present and (not self._is_downloading) and has_formats_data
        self.video_radio.setEnabled(mode_enabled)
        self.audio_radio.setEnabled(mode_enabled)

        self.container_combo.setEnabled(base_ready)
        self.codec_combo.setEnabled(is_video_mode and base_ready and filter_chosen)
        self.convert_check.setEnabled(
            base_ready and filter_chosen and container_value == "webm"
        )
        if not self.convert_check.isEnabled():
            self.convert_check.setChecked(False)

        self.format_combo.setEnabled(
            single_ready
            and filter_chosen
            and format_available
            and (is_audio_mode or codec_chosen)
        )

        self.playlist_items_edit.setEnabled(
            self._playlist_mode and (not self._is_downloading)
        )
        self.filename_edit.setEnabled(
            (not self._is_downloading) and (not is_playlist_url)
        )

        self.url_edit.setEnabled(not self._is_downloading)
        self.paste_button.setEnabled(not self._is_downloading)
        self.browse_button.setEnabled(not self._is_downloading)

        subtitle_controls_enabled = is_video_mode and (not self._is_downloading)
        self.subtitle_languages_edit.setEnabled(subtitle_controls_enabled)
        self.write_subtitles_check.setEnabled(subtitle_controls_enabled)
        embed_allowed = (
            subtitle_controls_enabled and self.write_subtitles_check.isChecked()
        )
        self.embed_subtitles_check.setEnabled(embed_allowed)
        if not embed_allowed:
            self.embed_subtitles_check.setChecked(False)

        self.audio_language_combo.setEnabled(not self._is_downloading)
        self.network_timeout_edit.setEnabled(not self._is_downloading)
        self.network_retries_edit.setEnabled(not self._is_downloading)
        self.retry_backoff_edit.setEnabled(not self._is_downloading)

    def closeEvent(self, event: QCloseEvent) -> None:
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
