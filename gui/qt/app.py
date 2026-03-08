from __future__ import annotations

import signal
import re
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QListView,
    QMainWindow,
    QGraphicsOpacityEffect,
    QPushButton,
    QWidget,
)

from ..common import settings_store
from . import style as qt_style
from .constants import (
    AUDIO_CONTAINERS,
    CODECS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FETCH_DEBOUNCE_MS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SOURCE_DETAILS_NONE_INDEX,
    SOURCE_DETAILS_PLAYLIST_INDEX,
    TOP_ACTION_ICON_PX,
    VIDEO_CONTAINERS,
)
from .controllers import RunQueueController, RunQueueState, SourceController, SourceState
from .ports import SideEffectPorts
from .qt_ports import build_qt_side_effect_ports
from .presenter import StatusPresenter
from .ui_state_mapper import apply_control_state
from .window_feedback import WindowFeedbackMixin
from .window_settings import WindowSettingsMixin
from .view_builders import (
    DownloadsViewCallbacks,
    MainUiBuilder,
    RunSectionCallbacks,
    UiRefs,
)
from ..core import format_selection as core_format_selection
from ..core import urls as core_urls
from ..core import ui_state as core_ui_state
from ..services import app_service
from .state import PREVIEW_TITLE_TOOLTIP_DEFAULT
from .widgets import _QtSignals
from ..common.types import DownloadOptions, DownloadRequest, HistoryItem, QueueItem, QueueSettings


class QtYtDlpGui(WindowSettingsMixin, WindowFeedbackMixin, QMainWindow):
    def __init__(self, *, effects: SideEffectPorts | None = None) -> None:
        super().__init__()
        self.setWindowTitle("yt-dlp-gui")
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
        self._effects = effects or build_qt_side_effect_ports()
        self._source_state = SourceState()
        self._run_queue_state = RunQueueState()

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

        self.download_history: list[HistoryItem] = []
        self._history_seen_paths: set[str] = set()

        self._log_lines: list[str] = []
        self._last_error_log = ""
        self._last_source_feedback_log: tuple[str, str] | None = None
        self._status_presenter = StatusPresenter()
        self._active_panel_name: str | None = None
        self._applying_user_settings = False
        self._latest_output_path: Path | None = None
        self._current_item_progress = "-"
        self._current_item_title = "-"
        self._current_item_title_tooltip = "-"
        self._source_controller = SourceController(
            self,
            state=self._source_state,
            ports=self._effects,
        )
        self._run_queue_controller = RunQueueController(
            self,
            state=self._run_queue_state,
            ports=self._effects,
        )

        self._build_ui()
        self._update_source_details_visibility()
        self._set_preview_title("")
        self._set_audio_language_values([])
        self._set_mode_unselected()
        self._load_user_settings()
        self._connect_settings_autosave()
        self._apply_header_layout()
        self._update_controls_state()

    @property
    def _fetch_request_seq(self) -> int:
        return self._source_state.fetch_request_seq

    @_fetch_request_seq.setter
    def _fetch_request_seq(self, value: int) -> None:
        self._source_state.fetch_request_seq = int(value)

    @property
    def _active_fetch_request_id(self) -> int:
        return self._source_state.active_fetch_request_id

    @_active_fetch_request_id.setter
    def _active_fetch_request_id(self, value: int) -> None:
        self._source_state.active_fetch_request_id = int(value)

    @property
    def _is_fetching(self) -> bool:
        return self._source_state.is_fetching

    @_is_fetching.setter
    def _is_fetching(self, value: bool) -> None:
        self._source_state.is_fetching = bool(value)

    @property
    def _pending_mixed_url(self) -> str:
        return self._source_state.pending_mixed_url

    @_pending_mixed_url.setter
    def _pending_mixed_url(self, value: str) -> None:
        self._source_state.pending_mixed_url = str(value or "")

    @property
    def _last_formats_error_popup_key(self) -> str:
        return self._source_state.last_formats_error_popup_key

    @_last_formats_error_popup_key.setter
    def _last_formats_error_popup_key(self, value: str) -> None:
        self._source_state.last_formats_error_popup_key = str(value or "")

    @property
    def _playlist_mode(self) -> bool:
        return self._source_state.playlist_mode

    @_playlist_mode.setter
    def _playlist_mode(self, value: bool) -> None:
        self._source_state.playlist_mode = bool(value)

    @property
    def _video_labels(self) -> list[str]:
        return self._source_state.video_labels

    @_video_labels.setter
    def _video_labels(self, value: list[str]) -> None:
        self._source_state.video_labels = list(value)

    @property
    def _video_lookup(self) -> dict[str, dict]:
        return self._source_state.video_lookup

    @_video_lookup.setter
    def _video_lookup(self, value: dict[str, dict]) -> None:
        self._source_state.video_lookup = dict(value)

    @property
    def _audio_labels(self) -> list[str]:
        return self._source_state.audio_labels

    @_audio_labels.setter
    def _audio_labels(self, value: list[str]) -> None:
        self._source_state.audio_labels = list(value)

    @property
    def _audio_lookup(self) -> dict[str, dict]:
        return self._source_state.audio_lookup

    @_audio_lookup.setter
    def _audio_lookup(self, value: dict[str, dict]) -> None:
        self._source_state.audio_lookup = dict(value)

    @property
    def _audio_languages(self) -> list[str]:
        return self._source_state.audio_languages

    @_audio_languages.setter
    def _audio_languages(self, value: list[str]) -> None:
        self._source_state.audio_languages = list(value)

    @property
    def _filtered_labels(self) -> list[str]:
        return self._source_state.filtered_labels

    @_filtered_labels.setter
    def _filtered_labels(self, value: list[str]) -> None:
        self._source_state.filtered_labels = list(value)

    @property
    def _filtered_lookup(self) -> dict[str, dict]:
        return self._source_state.filtered_lookup

    @_filtered_lookup.setter
    def _filtered_lookup(self, value: dict[str, dict]) -> None:
        self._source_state.filtered_lookup = dict(value)

    @property
    def _is_downloading(self) -> bool:
        return self._run_queue_state.is_downloading

    @_is_downloading.setter
    def _is_downloading(self, value: bool) -> None:
        self._run_queue_state.is_downloading = bool(value)

    @property
    def _cancel_requested(self) -> bool:
        return self._run_queue_state.cancel_requested

    @_cancel_requested.setter
    def _cancel_requested(self, value: bool) -> None:
        self._run_queue_state.cancel_requested = bool(value)

    @property
    def _cancel_event(self) -> object | None:
        return self._run_queue_state.cancel_event

    @_cancel_event.setter
    def _cancel_event(self, value: object | None) -> None:
        self._run_queue_state.cancel_event = value

    @property
    def _show_progress_item(self) -> bool:
        return self._run_queue_state.show_progress_item

    @_show_progress_item.setter
    def _show_progress_item(self, value: bool) -> None:
        self._run_queue_state.show_progress_item = bool(value)

    @property
    def _close_after_cancel(self) -> bool:
        return self._run_queue_state.close_after_cancel

    @_close_after_cancel.setter
    def _close_after_cancel(self, value: bool) -> None:
        self._run_queue_state.close_after_cancel = bool(value)

    @property
    def queue_items(self) -> list[QueueItem]:
        return self._run_queue_state.queue_items

    @queue_items.setter
    def queue_items(self, value: list[QueueItem]) -> None:
        self._run_queue_state.queue_items = list(value)

    @property
    def queue_active(self) -> bool:
        return self._run_queue_state.queue_active

    @queue_active.setter
    def queue_active(self, value: bool) -> None:
        self._run_queue_state.queue_active = bool(value)

    @property
    def queue_index(self) -> int | None:
        return self._run_queue_state.queue_index

    @queue_index.setter
    def queue_index(self, value: int | None) -> None:
        self._run_queue_state.queue_index = value

    @property
    def _queue_failed_items(self) -> int:
        return self._run_queue_state.queue_failed_items

    @_queue_failed_items.setter
    def _queue_failed_items(self, value: int) -> None:
        self._run_queue_state.queue_failed_items = int(value)

    @property
    def _queue_started_ts(self) -> float | None:
        return self._run_queue_state.queue_started_ts

    @_queue_started_ts.setter
    def _queue_started_ts(self, value: float | None) -> None:
        self._run_queue_state.queue_started_ts = value

    def _build_ui(self) -> None:
        callbacks = DownloadsViewCallbacks(
            on_url_changed=self._on_url_changed,
            on_fetch_formats=self._start_fetch_formats,
            on_paste_url=self._paste_url,
            on_mode_change=self._on_mode_change,
            on_container_change=self._on_container_change,
            on_codec_change=self._on_codec_change,
            on_update_controls_state=self._update_controls_state,
            on_pick_folder=self._pick_folder,
            on_use_single_video_url=lambda: self._apply_mixed_url_choice(
                use_playlist=False
            ),
            on_use_playlist_url=lambda: self._apply_mixed_url_choice(
                use_playlist=True
            ),
            run=RunSectionCallbacks(
                on_start=self._on_start,
                on_add_to_queue=self._on_add_to_queue,
                on_start_queue=self._on_start_queue,
                on_cancel=self._on_cancel,
                on_open_last_output_folder=self._open_last_output_folder,
                on_copy_output_path=self._copy_last_output_path,
            ),
        )
        ui = MainUiBuilder.build(
            window=self,
            register_native_combo=self._register_native_combo,
            callbacks=callbacks,
        )
        self.setCentralWidget(ui.root)
        self._bind_ui_refs(ui)
        self._sync_source_details_height()
        self._set_output_form_label_width(min_width=112)

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

    def _bind_ui_refs(self, ui: UiRefs) -> None:
        self._ui = ui
        self.panel_stack = ui.panel_stack

        top = ui.top_bar
        self.top_actions = top.top_actions
        self.classic_actions = top.classic_actions
        self.downloads_button = top.downloads_button
        self.queue_button = top.queue_button
        self.history_button = top.history_button
        self.logs_button = top.logs_button
        self.settings_button = top.settings_button

        mixed = ui.mixed_url
        self.mixed_url_overlay = mixed.overlay
        self.mixed_url_overlay_layout = mixed.overlay_layout
        self.mixed_url_alert = mixed.alert
        self.mixed_url_alert_label = mixed.alert_label
        self.mixed_buttons_layout = mixed.buttons_layout
        self.use_single_video_url_button = mixed.use_single_video_url_button
        self.use_playlist_url_button = mixed.use_playlist_url_button

        downloads = ui.downloads
        self.main_page = downloads.main_page
        self._main_page_index = downloads.main_page_index
        self.url_edit = downloads.url_edit
        self.paste_button = downloads.paste_button
        self.source_details_host = downloads.source_details_host
        self.source_details_stack = downloads.source_details_stack
        self.source_details_empty = downloads.source_details_empty
        self.playlist_items_panel = downloads.playlist_items_panel
        self.playlist_items_edit = downloads.playlist_items_edit
        self.preview_value = downloads.preview_value
        self.preview_title_label = downloads.preview_title_label
        self.source_details_label = downloads.source_details_label
        self.output_section = downloads.output_section
        self.output_layout = downloads.output_layout
        self.format_card = downloads.format_card
        self.format_layout = downloads.format_layout
        self.mode_row_layout = downloads.mode_row_layout
        self.video_radio = downloads.video_radio
        self.audio_radio = downloads.audio_radio
        self.content_type_label = downloads.content_type_label
        self.container_combo = downloads.container_combo
        self.convert_check = downloads.convert_check
        self.container_label = downloads.container_label
        self.post_process_label = downloads.post_process_label
        self.codec_combo = downloads.codec_combo
        self.codec_label = downloads.codec_label
        self.format_combo = downloads.format_combo
        self.format_label = downloads.format_label
        self._output_form_labels = list(downloads.output_form_labels)
        self._output_form_rows = list(downloads.output_form_rows)
        self.save_card = downloads.save_card
        self.save_layout = downloads.save_layout
        self.filename_edit = downloads.filename_edit
        self.file_name_label = downloads.file_name_label
        self.folder_row_layout = downloads.folder_row_layout
        self.output_dir_edit = downloads.output_dir_edit
        self.browse_button = downloads.browse_button
        self.output_folder_label = downloads.output_folder_label

        run = downloads.run
        self.status_value = run.status_value
        self.progress_bar = run.progress_bar
        self.start_button = run.start_button
        self.add_queue_button = run.add_queue_button
        self.start_queue_button = run.start_queue_button
        self.cancel_button = run.cancel_button
        self.ready_summary_label = run.ready_summary_label
        self.metrics_strip = run.metrics_strip
        self.progress_label = run.progress_label
        self.speed_label = run.speed_label
        self.eta_label = run.eta_label
        self.item_label = run.item_label
        self.download_result_card = run.download_result_card
        self.download_result_title = run.download_result_title
        self.download_result_stack = run.download_result_stack
        self._download_result_info_index = run.download_result_info_index
        self._download_result_latest_index = run.download_result_latest_index
        self.download_result_path = run.download_result_path
        self.open_last_output_folder_button = run.open_last_output_folder_button
        self.copy_output_path_button = run.copy_output_path_button

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
        padding: int = 40,
    ) -> None:
        view = combo.view()
        if view is None:
            return
        metrics = QFontMetrics(view.font())
        text_width = 0
        for idx in range(combo.count()):
            text_width = max(text_width, metrics.horizontalAdvance(combo.itemText(idx)))
        scrollbar = view.verticalScrollBar()
        scrollbar_width = scrollbar.sizeHint().width() if scrollbar is not None else 18
        view.setMinimumWidth(max(min_width, text_width + padding + scrollbar_width))
        row_height = max(30, metrics.height() + 10)
        rows = max(1, min(combo.count(), combo.maxVisibleItems()))
        popup_height = (row_height * rows) + 10
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
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
            label.setFixedWidth(width)
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
        control_height = max(29, metrics.height() + 9)
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
        self.start_button.setMinimumHeight(control_height + 4)

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
            extra_px=18,
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
            extra_px=18,
        )

        self._set_output_form_label_width(min_width=112)
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

        save_card_width = max(350, min(540, int(width * 0.40)))
        self.save_card.setMinimumWidth(save_card_width)
        self.save_card.setMaximumWidth(save_card_width)

    def _set_output_layout_mode(self) -> None:
        self.output_layout.addWidget(self.format_card, 0, 0)
        self.output_layout.addWidget(self.save_card, 0, 1)
        self.output_layout.setColumnStretch(0, 5)
        self.output_layout.setColumnStretch(1, 4)
        self.output_layout.setHorizontalSpacing(22)
        self.output_layout.setVerticalSpacing(8)
        self.format_layout.setSpacing(4)
        self.save_layout.setSpacing(8)
        self._set_output_form_label_width(min_width=112)
        self.mode_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.folder_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.folder_row_layout.setSpacing(8)
        self.folder_row_layout.setStretch(0, 1)

    def _apply_responsive_layout(self) -> None:
        desired_mode = "wide"
        if desired_mode != self._output_layout_mode:
            self._set_output_layout_mode()
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
        self.edit_friendly_encoder_combo.setToolTip(
            "Choose how edit-friendly MP4 re-encoding selects hardware."
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
        self._status_presenter.last_source_feedback_log = self._last_source_feedback_log
        self._status_presenter.set_source_feedback(
            text,
            tone=tone,
            append_log=self._append_log,
        )
        self._last_source_feedback_log = self._status_presenter.last_source_feedback_log

    def _set_metrics_visible(self, visible: bool) -> None:
        # Keep the info row mounted in the result card to avoid layout shifts.
        self.metrics_strip.setVisible(True)
        self.item_label.setVisible(True)
        if bool(visible):
            self.download_result_stack.setCurrentIndex(self._download_result_info_index)
            self.download_result_title.setText("Download info:")

    def _ready_summary_quality(self, format_label: str) -> str:
        label = str(format_label or "").strip()
        if not label:
            return "Auto quality"
        match = re.search(r"\b(\d{3,4}p)\b", label, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        if self._current_mode() == "audio":
            bitrate = re.search(r"\b(\d{2,4}k)\b", label, re.IGNORECASE)
            if bitrate:
                return bitrate.group(1).lower()
        compact = re.sub(r"\s+", " ", label).strip()
        if len(compact) > 24:
            compact = f"{compact[:24].rstrip()}..."
        return compact or "Auto quality"

    def _ready_summary_codec(self) -> str:
        codec = self._current_codec()
        if codec:
            return codec.upper()

        info = self._selected_format_info() or {}
        mode = self._current_mode()
        if mode == "audio":
            raw_codec = str(info.get("acodec") or "").strip().lower()
        else:
            raw_codec = str(info.get("vcodec") or "").strip().lower()
            if raw_codec in {"", "none"}:
                raw_codec = str(info.get("acodec") or "").strip().lower()

        if not raw_codec or raw_codec == "none":
            return "Codec"

        alias_map = {
            "avc1": "AVC1",
            "av01": "AV01",
            "h264": "H264",
            "h265": "H265",
            "hev1": "H265",
            "hvc1": "H265",
            "vp9": "VP9",
            "vp8": "VP8",
            "mp4a": "AAC",
            "aac": "AAC",
            "opus": "OPUS",
        }
        for prefix, label in alias_map.items():
            if raw_codec.startswith(prefix):
                return label
        return raw_codec.split(".", 1)[0].upper()

    def _ready_summary_folder(self) -> str:
        raw = self.output_dir_edit.text().strip() or self._default_output_dir()
        try:
            folder = Path(raw).expanduser()
        except (TypeError, ValueError, OSError):
            folder = Path(self._default_output_dir())
        name = folder.name.strip()
        if name:
            return f"{name} folder"
        return "Output folder"

    def _refresh_ready_summary(self) -> None:
        container = self._current_container()
        container_text = container.upper() if container else "Container"
        codec_text = self._ready_summary_codec()
        quality_text = self._ready_summary_quality(self._selected_format_label())
        folder_text = self._ready_summary_folder()
        self.ready_summary_label.setText(
            f"{container_text} • {codec_text} • {quality_text} • {folder_text}"
        )

    def _apply_header_layout(self) -> None:
        self.classic_actions.setVisible(True)
        self._refresh_top_action_icons()

    def _toggle_panel(self, name: str) -> None:
        if self._active_panel_name == name:
            for panel_name, button in self._panel_buttons.items():
                button.setChecked(panel_name == name)
            self._refresh_top_action_icons()
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
            return self._legacy_log_alert_icon
        icon = QIcon(path.as_posix())
        if icon.isNull():
            return self._legacy_log_alert_icon
        return icon

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
        for name, button in (
            ("downloads", self.downloads_button),
            ("settings", self.settings_button),
            ("queue", self.queue_button),
            ("history", self.history_button),
            ("logs", self.logs_button),
        ):
            icon = QIcon()
            if self._header_icons_enabled:
                icon = self._panel_icon(
                    name,
                    checked=(
                        name == "downloads" and self._active_panel_name is None
                    )
                    or self._active_panel_name == name,
                    alert=(
                        name == "logs"
                        and self._logs_alert_active
                        and self._active_panel_name != "logs"
                    ),
                )
                if icon.isNull():
                    icon = self._legacy_log_alert_icon
            button.setIcon(icon)
            button.setIconSize(full_icon_size)

        self._set_uniform_button_width(
            [
                self.downloads_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ],
            extra_px=12,
        )

    def _configure_top_action_icons(self) -> None:
        self._top_action_icons = {
            "downloads": {
                "normal": self._load_asset_icon("downloads.svg"),
                "active": self._load_asset_icon("downloads-active.svg"),
            },
            "settings": {
                "normal": self._load_asset_icon("settings.svg"),
                "active": self._load_asset_icon("settings-active.svg"),
            },
            "queue": {
                "normal": self._load_asset_icon("queue.svg"),
                "active": self._load_asset_icon("queue-active.svg"),
            },
            "history": {
                "normal": self._load_asset_icon("history.svg"),
                "active": self._load_asset_icon("history-active.svg"),
            },
            "logs": {
                "normal": self._load_asset_icon("logs.svg"),
                "active": self._load_asset_icon("logs-active.svg"),
                "alert": self._load_asset_icon("logs-alert.svg"),
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

    def _set_mixed_url_alert_visible(self, visible: bool) -> None:
        should_show = bool(visible) and (
            self.panel_stack.currentIndex() == self._main_page_index
        )
        self._layout_mixed_url_overlay()
        self.mixed_url_overlay.setVisible(should_show)
        if should_show:
            self.mixed_url_overlay.raise_()

    def _show_feedback_popup(self, *, title: str, message: str, critical: bool = False) -> None:
        clean_message = str(message or "").strip() or "Something went wrong."
        detail = str(self._last_error_log or "").strip()
        body = clean_message
        if detail:
            lower_body = clean_message.lower()
            if detail.lower() not in lower_body:
                body = f"{clean_message}\n\nDetails:\n{detail}"
        if critical:
            self._effects.dialogs.critical(self, title, body)
            return
        self._effects.dialogs.warning(self, title, body)

    def _set_playlist_items_visible(self, visible: bool) -> None:
        if bool(visible):
            self.source_details_label.setText("Playlist items")
            self.source_details_stack.setCurrentIndex(SOURCE_DETAILS_PLAYLIST_INDEX)
        else:
            self.source_details_label.setText("")
            if self.source_details_stack.currentIndex() == SOURCE_DETAILS_PLAYLIST_INDEX:
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
            target = max(0, current.sizeHint().height(), current.minimumSizeHint().height())
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
        clip = self._effects.clipboard.get_text().strip()
        if not clip:
            self._set_status("Clipboard is empty")
            return
        self.url_edit.setText(core_urls.strip_url_whitespace(clip))
        self._set_status("URL pasted")

    def _pick_folder(self) -> None:
        selected = self._effects.file_dialogs.pick_directory(
            self,
            "Select output folder",
        )
        if selected:
            self._set_output_dir_text(selected)
            self._refresh_ready_summary()

    def _on_url_changed(self) -> None:
        self._source_controller.on_url_changed()

    def _start_fetch_formats(self) -> None:
        self._source_controller.start_fetch_formats()

    def _fetch_formats_worker(self, request_id: int, url: str) -> None:
        self._source_controller.fetch_formats_worker(request_id, url)

    def _on_formats_loaded(
        self,
        request_id: int,
        url: str,
        payload: object,
        error: bool,
        is_playlist: bool,
    ) -> None:
        self._source_controller.on_formats_loaded(
            request_id=request_id,
            url=url,
            payload=payload,
            error=error,
            is_playlist=is_playlist,
        )

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
            edit_friendly_encoder_raw=str(
                self.edit_friendly_encoder_combo.currentData() or "auto"
            ),
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
        self._run_queue_controller.on_start()

    def _run_single_download_worker(self, *, request: DownloadRequest) -> None:
        self._run_queue_controller.run_single_download_worker(request=request)

    def _on_download_done(self, result: str) -> None:
        self._run_queue_controller.on_download_done(result)

    def _maybe_close_after_cancel(self) -> None:
        if self._is_downloading or not self._close_after_cancel:
            return
        self._close_after_cancel = False
        QTimer.singleShot(0, self.close)

    def _on_cancel(self) -> None:
        self._run_queue_controller.on_cancel()

    def _on_add_to_queue(self) -> None:
        self._run_queue_controller.on_add_to_queue()

    def _on_start_queue(self) -> None:
        self._run_queue_controller.on_start_queue()

    def _start_queue_download(self) -> None:
        self._run_queue_controller.start_queue_download()

    def _start_next_queue_item(self) -> None:
        self._run_queue_controller.start_next_queue_item()

    def _resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        return self._run_queue_controller.resolve_format_for_url(url, settings)

    def _run_queue_download_worker(
        self,
        *,
        url: str,
        settings: QueueSettings,
        index: int,
        total: int,
        default_output_dir: str,
    ) -> None:
        self._run_queue_controller.run_queue_download_worker(
            url=url,
            settings=settings,
            index=index,
            total=total,
            default_output_dir=default_output_dir,
        )

    def _on_queue_item_done(self, had_error: bool, cancelled: bool) -> None:
        self._run_queue_controller.on_queue_item_done(had_error, cancelled)

    def _finish_queue(self, *, cancelled: bool = False) -> None:
        self._run_queue_controller.finish_queue(cancelled=cancelled)

    def _queue_selection_rows(self) -> list[int]:
        return [idx.row() for idx in self.queue_list.selectedIndexes()]

    def _queue_remove_selected(self) -> None:
        self._run_queue_controller.on_queue_remove_selected(self._queue_selection_rows())

    def _queue_move_up(self) -> None:
        self._run_queue_controller.on_queue_move_up(self._queue_selection_rows())

    def _queue_move_down(self) -> None:
        self._run_queue_controller.on_queue_move_down(self._queue_selection_rows())

    def _queue_clear(self) -> None:
        self._run_queue_controller.on_queue_clear()

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
        apply_control_state(
            self,
            state,
            pending_mixed_url=self._pending_mixed_url,
        )

        self._refresh_ready_summary()
        self._refresh_download_result_view()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._normalize_input_widths()
        self._apply_responsive_layout()
        self._layout_mixed_url_overlay()
        self._refresh_current_item_text()
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
            force_quit = self._effects.dialogs.question(
                self,
                "Cancellation in progress",
                (
                    "A download is still shutting down.\n\n"
                    "Force close now?"
                ),
                default_yes=False,
            )
            if force_quit:
                event.accept()
                return
            event.ignore()
            return

        choice = self._effects.dialogs.question(
            self,
            "Download in progress",
            (
                "A download is currently running.\n\n"
                "Cancel the download and close when it stops?"
            ),
            default_yes=True,
        )
        if choice:
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
