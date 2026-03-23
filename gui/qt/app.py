from __future__ import annotations

import signal
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QListView,
    QMainWindow,
    QGraphicsOpacityEffect,
    QPlainTextEdit,
    QProxyStyle,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..common import settings_store
from ..app_meta import (
    APP_BUNDLE_IDENTIFIER,
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_ICON_FILENAME,
    APP_ORGANIZATION_DOMAIN,
    APP_ORGANIZATION_NAME,
    APP_REPO_NAME,
    APP_VERSION,
)
from . import style as qt_style
from .constants import (
    AUDIO_CONTAINERS,
    CODECS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FETCH_DEBOUNCE_MS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    OUTPUT_CARD_STACK_GAP,
    PANEL_SWITCH_FADE_MS,
    ROOMY_CONTENT_LAYOUT_MIN_HEIGHT,
    RUN_SECTION_CARD_GAP,
    SOURCE_DETAILS_NONE_INDEX,
    SOURCE_DETAILS_PLAYLIST_INDEX,
    TOOLTIP_WAKE_UP_DELAY_MS,
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
from ..core import queue_presentation
from ..core import urls as core_urls
from ..core import ui_state as core_ui_state
from ..services import app_service
from .state import PREVIEW_TITLE_TOOLTIP_DEFAULT
from .widgets import QUEUE_SOURCE_INDEX_ROLE, WorkspaceSummaryWidget, _NativeComboBox, _QtSignals
from ..common.types import DownloadOptions, DownloadRequest, HistoryItem, QueueItem, QueueSettings


@dataclass
class _SourceFeedbackToastEntry:
    card: QFrame
    title_label: QLabel
    message_label: QLabel
    dismiss_button: QPushButton
    timer: QTimer | None = None
    animation: QPropertyAnimation | None = None
    placeholder: bool = False


class _TooltipDelayProxyStyle(QProxyStyle):
    def __init__(self, base_style: QStyle, *, wake_up_delay_ms: int) -> None:
        super().__init__(base_style)
        self._wake_up_delay_ms = max(0, int(wake_up_delay_ms))

    def styleHint(  # type: ignore[override]
        self,
        hint,
        option=None,
        widget=None,
        returnData=None,
    ) -> int:
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return self._wake_up_delay_ms
        return int(super().styleHint(hint, option, widget, returnData))


def _apply_tooltip_delay_style(app: QApplication) -> None:
    style = app.style()
    if style is None:
        return
    if isinstance(style, _TooltipDelayProxyStyle):
        return
    app.setStyle(
        _TooltipDelayProxyStyle(style, wake_up_delay_ms=TOOLTIP_WAKE_UP_DELAY_MS)
    )


class QtYtDlpGui(WindowSettingsMixin, WindowFeedbackMixin, QMainWindow):
    def __init__(self, *, effects: SideEffectPorts | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self._native_combos: list[_NativeComboBox] = []
        self._active_animations: list[QPropertyAnimation] = []
        self._shortcuts: list[QShortcut] = []
        self._progress_anim: QPropertyAnimation | None = None
        self._source_feedback_toasts: list[_SourceFeedbackToastEntry] = []
        self._source_feedback_toast_placeholder: _SourceFeedbackToastEntry | None = None
        self._source_feedback_toast_parent: QWidget | None = None
        self._last_toasted_source_feedback_version: int | None = None
        self._logs_alert_active = False
        self._header_icons_enabled = True
        self._legacy_log_alert_icon = self._build_alert_dot_icon()
        self._top_action_icons: dict[str, dict[str, QIcon]] = {}
        self._output_layout_mode: str | None = None
        self._source_row_control_height = 0
        self._source_preview_locked_heights: dict[bool, int] = {
            False: 0,
            True: 0,
        }
        self._source_section_locked_heights: dict[bool, int] = {
            False: 0,
            True: 0,
        }
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
        self._resize_sync_timer = QTimer(self)
        self._resize_sync_timer.setSingleShot(True)
        self._resize_sync_timer.timeout.connect(self._run_deferred_resize_sync)

        self.download_history: list[HistoryItem] = []
        self._history_seen_paths: set[str] = set()
        self.queue_empty_state = None

        self._log_lines: list[str] = []
        self._last_error_log = ""
        self._last_source_feedback_log: tuple[str, str] | None = None
        self._current_source_feedback_message = ""
        self._current_source_feedback_tone = "neutral"
        self._source_feedback_version = 0
        self._dismissed_source_feedback_version: int | None = None
        self._status_presenter = StatusPresenter()
        self._active_panel_name: str | None = None
        self._active_workspace_name = "queue"
        self._applying_user_settings = False
        self._latest_output_path: Path | None = None
        self._preview_title_raw = ""
        self._source_summary_data: dict[str, str] | None = None
        self._current_item_progress = "-"
        self._current_item_title = "-"
        self._current_item_title_tooltip = "-"
        self._session_started_ts: float | None = None
        self._session_total_items = 0
        self._session_completed_items = 0
        self._session_failed_items = 0
        self._session_downloaded_bytes = 0
        self._session_speed_sample_total_bps = 0.0
        self._session_speed_sample_count = 0
        self._session_peak_speed_bps = 0.0
        self._session_progress_item_key = ""
        self._session_current_item_downloaded_bytes = 0
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
        self._apply_window_icon()

        self._build_ui()
        self._update_source_details_visibility()
        self._set_preview_title("")
        self._set_source_summary(None)
        self._set_mode_unselected()
        self._reset_progress_summary()
        self._reset_session_metrics(total_items=0)
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
            on_analyze_url=self._start_fetch_formats,
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
        session_panel = self._build_session_panel()
        queue_panel = self._build_queue_panel()
        history_panel = self._build_history_panel()
        logs_panel = self._build_logs_panel()

        self._panel_name_to_index = {
            "settings": self.panel_stack.addWidget(settings_panel),
            "session": self.panel_stack.addWidget(session_panel),
            "queue": self.panel_stack.addWidget(queue_panel),
            "history": self.panel_stack.addWidget(history_panel),
            "logs": self.panel_stack.addWidget(logs_panel),
        }
        self._panel_buttons = {
            "downloads": self.downloads_button,
            "session": self.session_button,
            "settings": self.settings_button,
            "queue": self.queue_button,
            "history": self.history_button,
            "logs": self.logs_button,
        }
        self._configure_top_action_icons()

        self.queue_view_button.clicked.connect(
            lambda _checked: self._show_main_workspace("queue")
        )
        self.history_view_button.clicked.connect(
            lambda _checked: self._show_main_workspace("history")
        )
        self.downloads_button.clicked.connect(
            lambda _checked: self._show_main_workspace(self._active_workspace_name)
        )
        self.session_button.clicked.connect(
            lambda _checked: self._toggle_panel("session")
        )
        self.settings_button.clicked.connect(
            lambda _checked: self._toggle_panel("settings")
        )
        self.queue_button.clicked.connect(
            lambda _checked: self._toggle_panel("queue")
        )
        self.history_button.clicked.connect(
            lambda _checked: self._toggle_panel("history")
        )
        self.logs_button.clicked.connect(lambda _checked: self._toggle_panel("logs"))
        self._select_workspace_view("queue")

        combo_arrow_path = (
            Path(__file__).resolve().parent / "assets" / "combo-down-arrow.svg"
        ).as_posix()
        self.setStyleSheet(qt_style.build_stylesheet(combo_arrow_path))
        self._normalize_control_sizing()
        self._set_logs_alert(False)
        self._install_tooltips()
        self._install_shortcuts()
        self._apply_responsive_layout()
        self._refresh_queue_panel()
        self._refresh_history_panel()
        self._refresh_logs_panel_state()
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
        self.session_button = top.session_button
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

        source_toast = ui.source_toast
        self._source_feedback_toast_parent = source_toast.card.parentWidget() or ui.root
        self._source_feedback_toast_placeholder = _SourceFeedbackToastEntry(
            card=source_toast.card,
            title_label=source_toast.title_label,
            message_label=source_toast.message_label,
            dismiss_button=source_toast.dismiss_button,
            placeholder=True,
        )
        self._sync_source_feedback_toast_refs()
        self.source_feedback_toast_dismiss_button.clicked.connect(
            self._dismiss_source_feedback_toast
        )

        downloads = ui.downloads
        self.main_page = downloads.main_page
        self._main_page_index = downloads.main_page_index
        self.workspace_layout = downloads.workspace_layout
        self.source_view_stack = downloads.source_view_stack
        self._queue_view_index = downloads.queue_view_index
        self._history_view_index = downloads.history_view_index
        self.queue_view_button = downloads.queue_view_button
        self.history_view_button = downloads.history_view_button
        self.queue_workspace_stack = downloads.queue_workspace_stack
        self._queue_workspace_preview_index = downloads.queue_workspace_preview_index
        self._queue_workspace_summary_index = downloads.queue_workspace_summary_index
        self.queue_summary_list = downloads.queue_summary_list
        self.queue_summary_empty = downloads.queue_summary_empty
        self.history_summary_list = downloads.history_summary_list
        self.history_summary_empty = downloads.history_summary_empty
        self.source_row = downloads.source_row
        self.url_edit = downloads.url_edit
        self.paste_button = downloads.paste_button
        self.analyze_button = downloads.analyze_button
        self.source_details_host = downloads.source_details_host
        self.source_details_stack = downloads.source_details_stack
        self.source_details_empty = downloads.source_details_empty
        self.playlist_items_panel = downloads.playlist_items_panel
        self.playlist_items_edit = downloads.playlist_items_edit
        self.source_preview_card = downloads.source_preview_card
        self.source_preview_badge = downloads.source_preview_badge
        self.preview_value = downloads.preview_value
        self.preview_title_label = downloads.preview_title_label
        self.source_preview_placeholder = downloads.source_preview_placeholder
        self.source_preview_subtitle = downloads.source_preview_subtitle
        self.source_preview_detail_one = downloads.source_preview_detail_one
        self.source_preview_detail_two = downloads.source_preview_detail_two
        self.source_preview_detail_three = downloads.source_preview_detail_three
        self.source_details_label = downloads.source_details_label
        self.source_feedback_label = downloads.source_feedback_label
        self.output_section = downloads.output_section
        self.output_stage_hint_label = downloads.output_stage_hint_label
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
        self.progress_bar = downloads.progress_bar
        self.ready_summary_label = downloads.ready_summary_label
        self.metrics_card = downloads.metrics_card
        self.metrics_strip = downloads.metrics_strip
        self.progress_label = downloads.progress_label
        self.speed_label = downloads.speed_label
        self.eta_label = downloads.eta_label
        self.item_label = downloads.item_label

        run = downloads.run
        self.run_section = run.section
        self.run_activity_card = run.activity_card
        self.run_actions_card = run.actions_card
        self.run_actions_shell_layout = run.actions_shell_layout
        self.run_actions_layout = run.actions_layout
        self.run_stage_hint_label = run.stage_hint_label
        self.session_title_label = run.session_title_label
        self.run_stats_grid = run.stats_grid
        self.status_value = run.status_value
        self.start_button = run.start_button
        self.add_queue_button = run.add_queue_button
        self.start_queue_button = run.start_queue_button
        self.cancel_button = run.cancel_button
        self.download_result_card = run.download_result_card
        self.download_result_title = run.download_result_title
        self.download_result_path = run.download_result_path
        self.session_completed_value = run.session_completed_value
        self.session_failed_value = run.session_failed_value
        self.session_success_rate_value = run.session_success_rate_value
        self.session_remaining_value = run.session_remaining_value
        self.session_speed_value = run.session_speed_value
        self.session_peak_speed_value = run.session_peak_speed_value
        self.session_downloaded_value = run.session_downloaded_value
        self.session_elapsed_value = run.session_elapsed_value
        self.open_last_output_folder_button = run.open_last_output_folder_button
        self.copy_output_path_button = run.copy_output_path_button

        for widget in (self.queue_summary_list, self.history_summary_list):
            widget.setSelectionMode(widget.SelectionMode.NoSelection)
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _register_native_combo(self, combo: _NativeComboBox) -> None:
        combo.setMinimumHeight(27)
        popup_view = QListView(combo)
        popup_view.setObjectName("nativeComboView")
        popup_view.setFrameShape(QFrame.Shape.NoFrame)
        popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        popup_view.setMouseTracking(True)
        popup_view.viewport().setMouseTracking(True)
        combo.setView(popup_view)
        combo.set_before_popup_callback(
            lambda combo=combo: self._fit_combo_popup_to_contents(combo)
        )
        self._native_combos.append(combo)

    def _fit_combo_popup_to_contents(
        self,
        combo: _NativeComboBox,
        *,
        min_width: int = 240,
        padding: int = 28,
        screen_margin: int = 120,
    ) -> None:
        view = combo.view()
        if view is None or combo.count() <= 0:
            return
        metrics = QFontMetrics(view.font())
        text_width = 0
        for idx in range(combo.count()):
            text_width = max(text_width, metrics.horizontalAdvance(combo.itemText(idx)))
        row_height = view.sizeHintForRow(0)
        if row_height <= 0:
            row_height = max(combo.height(), metrics.height() + 12)
        frame_height = max(2, view.frameWidth() * 2)
        popup_height = (row_height * combo.count()) + frame_height + 8
        max_popup_height = popup_height
        screen = combo.screen()
        if screen is not None:
            max_popup_height = max(
                row_height + frame_height + 8,
                screen.availableGeometry().height() - screen_margin,
            )
        popup_height = min(popup_height, max_popup_height)
        scroll_needed = popup_height < ((row_height * combo.count()) + frame_height + 8)
        scrollbar = view.verticalScrollBar()
        scrollbar_width = (
            scrollbar.sizeHint().width() if scroll_needed and scrollbar is not None else 0
        )
        combo.setMaxVisibleItems(max(1, combo.count()))
        view.setMinimumWidth(
            max(combo.width(), min_width, text_width + padding + scrollbar_width)
        )
        view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if scroll_needed
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
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
        stacked_mode = self._output_layout_mode == "stacked"
        if stacked_mode:
            for label in labels:
                label.setMinimumWidth(0)
                label.setMaximumWidth(16777215)
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            return
        width = max(min_width, max(label.sizeHint().width() for label in labels))
        for label in labels:
            label.setFixedWidth(width)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _set_uniform_button_width(
        self,
        buttons: list[QPushButton],
        *,
        extra_px: int = 28,
        fixed: bool = False,
    ) -> None:
        live = [btn for btn in buttons if btn is not None]
        if not live:
            return
        width = 0
        for button in live:
            metrics = button.fontMetrics()
            text_width = max(
                metrics.horizontalAdvance(button.text()),
                metrics.boundingRect(button.text()).width(),
                metrics.tightBoundingRect(button.text()).width(),
            )
            icon_width = 0
            if not button.icon().isNull():
                icon_size = button.iconSize()
                icon_width = max(icon_size.width(), icon_size.height()) + 8
            width = max(
                width,
                button.minimumSizeHint().width(),
                button.sizeHint().width(),
                text_width + icon_width + extra_px,
            )
        for button in live:
            if fixed:
                button.setFixedWidth(width)
            else:
                button.setMinimumWidth(width)

    def _set_fixed_label_width_for_samples(
        self, label: QLabel, samples: tuple[str, ...], *, extra_px: int = 4
    ) -> None:
        metrics = QFontMetrics(label.font())
        width = max(
            label.minimumSizeHint().width(),
            *(metrics.horizontalAdvance(sample) for sample in samples),
        )
        label.setFixedWidth(width + extra_px)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _stabilize_run_section_sizing(self) -> None:
        self._set_fixed_label_width_for_samples(
            self.progress_label,
            ("Progress: 100.0%",),
        )
        self._set_fixed_label_width_for_samples(
            self.speed_label,
            ("Speed: 9999.99 MiB/s", "Speed: 99.99 GiB/s"),
        )
        self._set_fixed_label_width_for_samples(
            self.eta_label,
            ("ETA: Finalizing", "ETA: 99:59:59 / 999:59:59"),
        )

        for card in self.run_stats_grid.findChildren(QFrame, "sessionMetricCard"):
            target_height = max(card.minimumSizeHint().height(), card.sizeHint().height())
            card.setMinimumHeight(target_height)
            card.setMaximumHeight(target_height)

        result_height = max(
            self.download_result_card.minimumSizeHint().height(),
            self.download_result_card.sizeHint().height(),
        )
        self.download_result_card.setMinimumHeight(result_height)
        self.download_result_card.setMaximumHeight(result_height)

    def _use_compact_content_layout(self) -> bool:
        return self.height() < ROOMY_CONTENT_LAYOUT_MIN_HEIGHT

    def _use_compact_run_layout(self) -> bool:
        # The always-visible metrics and result cards currently only fit reliably
        # with the denser run layout metrics.
        return True

    def _set_source_row_button_widths(self) -> None:
        self._set_uniform_button_width([self.paste_button], extra_px=16)
        self._set_uniform_button_width([self.analyze_button], extra_px=16)

    def _normalize_control_sizing(self) -> None:
        compact_height = self._use_compact_content_layout()
        source_row_inputs = (self.url_edit,)
        text_inputs = (
            self.playlist_items_edit,
            self.filename_edit,
            self.output_dir_edit,
        )
        combos = (
            self.container_combo,
            self.codec_combo,
            self.format_combo,
        )
        control_height = max(
            31 if compact_height else 34,
            *(
                max(widget.minimumSizeHint().height(), widget.sizeHint().height())
                for widget in (*text_inputs, *combos)
            ),
        )
        for widget in (*source_row_inputs, *text_inputs, *combos):
            widget.setMinimumHeight(control_height)

        for button in (
            self.downloads_button,
            self.session_button,
            self.settings_button,
            self.queue_button,
            self.history_button,
            self.logs_button,
            self.paste_button,
            self.analyze_button,
            self.use_single_video_url_button,
            self.use_playlist_url_button,
            self.browse_button,
            self.start_button,
            self.add_queue_button,
            self.start_queue_button,
            self.cancel_button,
            self.open_last_output_folder_button,
            self.copy_output_path_button,
            self.about_button,
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
        self.start_button.setMinimumHeight(
            control_height if compact_height else control_height + 4
        )

        toggles = (
            self.video_radio,
            self.audio_radio,
            self.convert_check,
        )
        toggle_height = max(
            23 if compact_height else 25,
            *(
                max(toggle.minimumSizeHint().height(), toggle.sizeHint().height())
                for toggle in toggles
            ),
        )
        for toggle in toggles:
            toggle.setMinimumHeight(toggle_height)

        for label in getattr(self, "_output_form_labels", []):
            label.setMinimumHeight(
                max(
                    toggle_height,
                    label.minimumSizeHint().height(),
                    label.sizeHint().height(),
                )
            )

        self._sync_output_form_row_heights(control_height)
        if compact_height:
            for button in (
                self.start_button,
                self.add_queue_button,
                self.start_queue_button,
                self.cancel_button,
            ):
                button.setMinimumHeight(34)

        self._set_uniform_button_width(
            [
                self.downloads_button,
                self.session_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ],
            extra_px=18,
            fixed=True,
        )
        self._set_source_row_button_widths()
        self._source_row_control_height = control_height
        self._lock_source_row_control_heights()
        self._set_uniform_button_width(
            [
                self.start_button,
                self.add_queue_button,
                self.start_queue_button,
                self.cancel_button,
            ],
            extra_px=12 if compact_height else 34,
        )
        self._set_uniform_button_width(
            [
                self.about_button,
                self.export_diagnostics_button,
            ],
            extra_px=24,
        )
        self._set_uniform_button_width(
            [
                self.use_single_video_url_button,
                self.use_playlist_url_button,
            ],
            extra_px=24,
        )

        self._set_output_form_label_width(min_width=120)
        self._normalize_input_widths()
        self._stabilize_source_preview_card_sizing()

    def _stabilize_source_preview_card_sizing(self) -> None:
        title_slot_height = max(
            self.preview_value.minimumSizeHint().height(),
            self.preview_value.sizeHint().height(),
            self.source_preview_placeholder.minimumSizeHint().height(),
            self.source_preview_placeholder.sizeHint().height(),
        )
        for label in (self.preview_value, self.source_preview_placeholder):
            label.setFixedHeight(title_slot_height)
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        detail_row = self.source_preview_detail_one.parentWidget()
        detail_layout = detail_row.layout()
        detail_row_margins = (
            detail_layout.contentsMargins() if detail_layout is not None else None
        )
        detail_vertical_padding = (
            detail_row_margins.top() + detail_row_margins.bottom()
            if detail_row_margins is not None
            else 0
        )
        detail_row_height = max(
            self.source_preview_detail_one.minimumSizeHint().height(),
            self.source_preview_detail_one.sizeHint().height(),
            self.source_preview_detail_two.minimumSizeHint().height(),
            self.source_preview_detail_two.sizeHint().height(),
            self.source_preview_detail_three.minimumSizeHint().height(),
            self.source_preview_detail_three.sizeHint().height(),
        )
        for chip in (
            self.source_preview_detail_one,
            self.source_preview_detail_two,
            self.source_preview_detail_three,
        ):
            chip.setFixedHeight(
                max(chip.minimumSizeHint().height(), chip.sizeHint().height())
            )
            chip.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        detail_row.setFixedHeight(detail_row_height + detail_vertical_padding + 2)

        compact_height = self._use_compact_content_layout()
        if not self.isVisible():
            self._source_preview_locked_heights[compact_height] = 0
            self.source_preview_card.setMinimumHeight(0)
            self.source_preview_card.setMaximumHeight(16777215)
            self.source_preview_card.updateGeometry()
            source_content = self.source_preview_card.parentWidget()
            source_section = (
                source_content.parentWidget() if source_content is not None else None
            )
            if source_section is not None:
                source_section.setMinimumHeight(0)
                source_section.updateGeometry()
            return

        if not self.source_preview_card.isVisible():
            self.source_preview_card.setMinimumHeight(0)
            self.source_preview_card.setMaximumHeight(0)
            self.source_preview_card.updateGeometry()
            source_content = self.source_preview_card.parentWidget()
            source_section = (
                source_content.parentWidget() if source_content is not None else None
            )
            if source_section is not None:
                source_section.setMinimumHeight(0)
                source_section.updateGeometry()
            return

        base_min_height = 50 if compact_height else 58
        preview_layout = self.source_preview_card.layout()
        locked_height = self._source_preview_locked_heights[compact_height]
        preview_height = max(
            base_min_height,
            locked_height,
            self.source_preview_card.minimumSizeHint().height(),
        )
        if preview_layout is not None:
            preview_layout.activate()
            preview_height = max(
                preview_height,
                preview_layout.sizeHint().height(),
            )
        self._source_preview_locked_heights[compact_height] = preview_height
        self.source_preview_card.setFixedHeight(preview_height)
        self.source_preview_card.updateGeometry()

        source_content = self.source_preview_card.parentWidget()
        source_section = (
            source_content.parentWidget() if source_content is not None else None
        )
        if source_section is not None:
            self._source_section_locked_heights[compact_height] = 0
            source_section.setMinimumHeight(0)
            source_section.updateGeometry()

    def _prime_hidden_source_layout_geometry(self) -> None:
        widget = self.source_preview_card
        while widget is not None and widget is not self.main_page:
            layout = widget.layout()
            if layout is not None:
                layout.activate()
            if not widget.isVisible():
                widget.adjustSize()
            widget.updateGeometry()
            widget = widget.parentWidget()

    def _lock_source_row_control_heights(self) -> None:
        target = max(0, int(self._source_row_control_height))
        if target <= 0:
            return
        controls = (
            self.url_edit,
            self.paste_button,
            self.analyze_button,
        )
        target = max(
            target,
            *(
                max(widget.minimumSizeHint().height(), widget.sizeHint().height())
                for widget in controls
            ),
        )
        row_margins = self.source_row.layout().contentsMargins() if self.source_row.layout() else None
        if row_margins is not None:
            shell_vertical_inset = 0
            url_shell = self.url_edit.parentWidget()
            shell_layout = (
                url_shell.layout()
                if (
                    url_shell is not None
                    and url_shell.objectName() == "urlInputShell"
                    and url_shell.isVisible()
                )
                else None
            )
            if shell_layout is not None:
                shell_margins = shell_layout.contentsMargins()
                shell_vertical_inset = shell_margins.top() + shell_margins.bottom()
            self.source_row.setFixedHeight(
                target
                + row_margins.top()
                + row_margins.bottom()
                + shell_vertical_inset
                + 1
            )
        for widget in controls:
            widget.setFixedHeight(target)

    def _constrain_source_row_widths(self, *, preferred_url_width: int) -> None:
        row_layout = self.source_row.layout()
        row_spacing = row_layout.spacing() if row_layout is not None else 0
        row_margins = row_layout.contentsMargins() if row_layout is not None else None
        horizontal_padding = (
            row_margins.left() + row_margins.right() if row_margins is not None else 0
        )
        shell_extra_width = 0
        url_shell = self.url_edit.parentWidget()
        shell_layout = (
            url_shell.layout()
            if (
                url_shell is not None
                and url_shell.objectName() == "urlInputShell"
                and url_shell.isVisible()
            )
            else None
        )
        if shell_layout is not None:
            shell_margins = shell_layout.contentsMargins()
            shell_extra_width += shell_margins.left() + shell_margins.right()
            shell_extra_width += shell_layout.spacing() * max(0, shell_layout.count() - 1)
            for index in range(shell_layout.count()):
                widget = shell_layout.itemAt(index).widget()
                if widget is None or widget is self.url_edit:
                    continue
                shell_extra_width += max(
                    widget.minimumWidth(),
                    widget.minimumSizeHint().width(),
                )
        action_width = sum(
            max(button.minimumWidth(), button.minimumSizeHint().width())
            for button in (self.paste_button, self.analyze_button)
        )
        reserved_width = action_width + horizontal_padding + (row_spacing * 2)
        available_width = self.source_row.width()
        if available_width <= 0:
            source_parent = self.source_row.parentWidget()
            if source_parent is not None:
                available_width = source_parent.contentsRect().width()
        if available_width <= 0:
            available_width = max(self.width(), reserved_width + preferred_url_width)
        url_width = min(
            preferred_url_width,
            max(0, available_width - reserved_width - shell_extra_width),
        )
        self.url_edit.setMinimumWidth(url_width)

    def _normalize_input_widths(self) -> None:
        width = max(1, self.width())
        stacked_mode = self._output_layout_mode == "stacked"
        single_panel_workspace = self.workspace_layout.count() <= 1
        compact = width < 1240
        field_ratio = 0.26 if compact else 0.22
        field_width = max(210, min(380, int(width * field_ratio)))
        dropdown_width = max(220, min(420, int(width * 0.23)))

        self._constrain_source_row_widths(preferred_url_width=field_width)
        self.playlist_items_edit.setMinimumWidth(field_width)
        self.filename_edit.setMinimumWidth(field_width)
        self.output_dir_edit.setMinimumWidth(0)

        self.container_combo.setMinimumWidth(dropdown_width)
        self.codec_combo.setMinimumWidth(dropdown_width)
        self.format_combo.setMinimumWidth(dropdown_width)
        if stacked_mode or single_panel_workspace:
            self.output_section.setMinimumWidth(0)
            self.output_section.setMaximumWidth(16777215)
            self.run_actions_card.setMinimumWidth(0)
            self.run_actions_card.setMaximumWidth(16777215)
        else:
            inspector_width = max(440, min(640, int(width * 0.46)))
            for widget in (self.output_section, self.run_actions_card):
                widget.setMinimumWidth(inspector_width)
                widget.setMaximumWidth(inspector_width)

    def _set_output_layout_mode(self, mode: str) -> None:
        stacked_mode = mode == "stacked"
        compact_height = self._use_compact_content_layout()
        self._output_layout_mode = mode
        self.workspace_layout.setDirection(
            QBoxLayout.Direction.TopToBottom
            if stacked_mode
            else QBoxLayout.Direction.LeftToRight
        )
        self.workspace_layout.setSpacing(14 if stacked_mode else 18)
        output_shell_layout = self.output_section.layout()
        if isinstance(output_shell_layout, QVBoxLayout):
            output_shell_layout.setContentsMargins(0, 0, 0, 0)
            output_shell_layout.setSpacing(8 if compact_height else 12)
        outer_spacing = (
            10
            if compact_height
            else OUTPUT_CARD_STACK_GAP
        )
        card_spacing = 5 if compact_height else 10
        card_side_margin = 10 if compact_height else 14
        card_top_margin = 9 if compact_height else 14
        card_bottom_margin = 10 if compact_height else 14
        self.output_layout.setSpacing(outer_spacing)
        self.format_layout.setSpacing(card_spacing)
        self.save_layout.setSpacing(6 if compact_height else max(6, card_spacing - 2))
        self.format_layout.setContentsMargins(
            card_side_margin,
            card_top_margin,
            card_side_margin,
            card_bottom_margin,
        )
        self.save_layout.setContentsMargins(
            0,
            2 if compact_height else 4,
            0,
            0,
        )
        self._set_output_form_label_width()
        self.mode_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.mode_row_layout.setSpacing(10 if stacked_mode else 14)
        self.folder_row_layout.setDirection(
            QBoxLayout.Direction.TopToBottom
            if stacked_mode
            else QBoxLayout.Direction.LeftToRight
        )
        self.folder_row_layout.setSpacing(8 if compact_height else 10)

    def _set_run_section_layout_mode(self) -> None:
        compact_height = self._use_compact_run_layout()
        self.session_title_label.setVisible(True)
        self.run_stats_grid.setVisible(True)

        run_layout = self.run_section.layout()
        if isinstance(run_layout, QBoxLayout):
            run_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            run_layout.setSpacing(RUN_SECTION_CARD_GAP)
            run_layout.setStretch(0, 13)
            run_layout.setStretch(1, 7)

        action_margin = 0
        action_spacing = 4 if compact_height else 8
        buttons_shell_layout = self.run_actions_shell_layout
        buttons_shell_layout.setContentsMargins(
            action_margin, action_margin, action_margin, action_margin
        )
        buttons_layout = self.run_actions_layout
        buttons_layout.setHorizontalSpacing(action_spacing)
        buttons_layout.setVerticalSpacing(action_spacing)

        activity_layout = self.run_activity_card.layout()
        if isinstance(activity_layout, QVBoxLayout):
            activity_margin = 4 if compact_height else 16
            activity_layout.setContentsMargins(
                activity_margin, activity_margin, activity_margin, activity_margin
            )
            activity_layout.setSpacing(2 if compact_height else 12)

        metrics_card_layout = self.metrics_card.layout()
        if isinstance(metrics_card_layout, QBoxLayout):
            metrics_card_layout.setContentsMargins(
                10 if compact_height else 12,
                8 if compact_height else 10,
                10 if compact_height else 12,
                10 if compact_height else 12,
            )
            metrics_card_layout.setSpacing(6 if compact_height else 8)
        metrics_strip_layout = self.metrics_strip.layout()
        if isinstance(metrics_strip_layout, QBoxLayout):
            metrics_strip_layout.setSpacing(4 if compact_height else 12)

        stats_layout = self.run_stats_grid.layout()
        if isinstance(stats_layout, QGridLayout):
            stats_layout.setHorizontalSpacing(4 if compact_height else 10)
            stats_layout.setVerticalSpacing(0 if compact_height else 10)

        result_layout = self.download_result_card.layout()
        if isinstance(result_layout, QHBoxLayout):
            result_margin_h = 6 if compact_height else 14
            result_margin_v = 1 if compact_height else 12
            result_layout.setContentsMargins(
                result_margin_h, result_margin_v, result_margin_h, result_margin_v
            )
            result_layout.setSpacing(3 if compact_height else 8)

        for widget in (
            self.start_button,
            self.add_queue_button,
            self.cancel_button,
            self.session_title_label,
            self.ready_summary_label,
            self.progress_label,
            self.speed_label,
            self.eta_label,
            self.item_label,
        ):
            self._set_widget_property(widget, "compact", compact_height)

        for label in self.run_stats_grid.findChildren(QLabel):
            if label.objectName() in {"sessionMetricValue", "sessionMetricLabel"}:
                self._set_widget_property(label, "compact", compact_height)

        for card in self.run_stats_grid.findChildren(QFrame, "sessionMetricCard"):
            self._set_widget_property(card, "compact", compact_height)
            card_layout = card.layout()
            if isinstance(card_layout, QVBoxLayout):
                card_layout.setContentsMargins(
                    4 if compact_height else 14,
                    3 if compact_height else 12,
                    4 if compact_height else 14,
                    3 if compact_height else 12,
                )
                card_layout.setSpacing(1 if compact_height else 4)

        self._stabilize_run_section_sizing()

        for button in (
            self.start_button,
            self.add_queue_button,
            self.start_queue_button,
            self.cancel_button,
        ):
            buttons_layout.removeWidget(button)

        buttons_layout.addWidget(self.start_button, 0, 0)
        buttons_layout.addWidget(self.add_queue_button, 0, 1)
        buttons_layout.addWidget(self.cancel_button, 0, 2)
        buttons_layout.setColumnStretch(0, 1)
        buttons_layout.setColumnStretch(1, 1)
        buttons_layout.setColumnStretch(2, 1)
        buttons_layout.setRowStretch(0, 0)
        buttons_layout.setRowStretch(1, 0)
        buttons_layout.setRowStretch(2, 0)
        buttons_layout.setRowStretch(3, 0)

    def _apply_responsive_layout(self) -> None:
        desired_mode = "stacked" if self.width() < 860 else "split"
        self._set_output_layout_mode(desired_mode)
        self._set_run_section_layout_mode()

        self.source_preview_subtitle.setVisible(self.height() >= MIN_WINDOW_HEIGHT)
        self._stabilize_source_preview_card_sizing()
        self._prime_hidden_source_layout_geometry()
        self._sync_source_feedback_visibility()
        self.mixed_buttons_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self._sync_source_details_height()

    def _install_tooltips(self) -> None:
        self.downloads_button.setToolTip("Open the downloads workspace.")
        self.session_button.setToolTip("Open the session panel.")
        self.settings_button.setToolTip("Open settings view.")
        self.queue_button.setToolTip("Open the download queue window.")
        self.history_button.setToolTip("Open the download history window.")
        self.logs_button.setToolTip("Open logs view.")
        self.queue_view_button.setToolTip("Show the current queue and source summary.")
        self.history_view_button.setToolTip("Show download history.")

        self.url_edit.setToolTip("Paste a video or playlist URL.")
        self.paste_button.setToolTip("Paste URL from clipboard.")
        self.analyze_button.setToolTip("Load formats and preview details for the current URL.")
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
        self.edit_friendly_encoder_combo.setToolTip(
            "Choose how edit-friendly MP4 re-encoding selects hardware."
        )
        self.open_folder_after_download_check.setToolTip(
            "Open the selected output folder after downloads finish."
        )
        self.export_diagnostics_button.setToolTip(
            "Export a diagnostics report to your output folder."
        )
        self.about_button.setToolTip("Open app details and keyboard shortcuts.")

        self.start_button.setToolTip(
            "Download the current URL, or the full queue when queue items exist."
        )
        self.add_queue_button.setToolTip("Add the current URL/settings to queue.")
        self.start_queue_button.setToolTip("Start queue download.")
        self.cancel_button.setToolTip("Cancel the current download.")
        self.status_value.setToolTip("Current run status.")

        self.queue_list.setToolTip(
            "Queued downloads. Drag to reorder and click X to remove."
        )
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

    def _set_widget_property(self, widget: QWidget, name: str, value: object) -> None:
        if widget.property(name) == value:
            return
        widget.setProperty(name, value)
        self._refresh_widget_style(widget)
        if widget is getattr(self, "analyze_button", None) and name == "mode":
            self._lock_source_row_control_heights()

    def _refresh_download_sections_state(
        self,
        *,
        url_present: bool,
        has_formats_data: bool,
        is_fetching: bool,
    ) -> None:
        download_state = "ready" if has_formats_data else "staged"
        if is_fetching:
            download_state = "loading"
        staged_widgets: list[QWidget] = []
        for widget in (
            self.output_section,
            self.format_card,
            self.save_card,
            self.run_section,
            self.source_preview_card,
            self.download_result_card,
        ):
            if widget is None or widget in staged_widgets:
                continue
            staged_widgets.append(widget)
            self._set_widget_property(widget, "stage", download_state)

        output_hint = ""
        run_hint = ""

        self.output_stage_hint_label.setText(output_hint)
        self.output_stage_hint_label.setVisible(
            bool(output_hint) and self.height() > (MIN_WINDOW_HEIGHT + 24)
        )
        self.run_stage_hint_label.setText(run_hint)
        self.run_stage_hint_label.setVisible(bool(run_hint))

        source_state = "ready" if has_formats_data else "idle"
        if is_fetching:
            source_state = "loading"
        elif url_present:
            source_state = "primed"
        self._set_widget_property(self.analyze_button, "mode", source_state)
        if is_fetching:
            self.analyze_button.setText("Analyzing...")
        elif has_formats_data:
            self.analyze_button.setText("Refresh formats")
        else:
            self.analyze_button.setText("Analyze URL")
        self._set_source_row_button_widths()
        self._lock_source_row_control_heights()
        self._set_source_row_button_widths()
        self._normalize_input_widths()

    def _refresh_queue_panel_state(self) -> None:
        has_items = self.queue_list.count() > 0
        has_selection = bool(self.queue_list.selectedIndexes())
        editable = not self.queue_active
        self._refresh_queue_empty_state()
        self.queue_stack.setCurrentIndex(
            self._queue_content_index if has_items else self._queue_empty_index
        )
        self.queue_list.set_queue_editable(editable)
        self.queue_remove_button.setEnabled(editable and has_selection)
        self.queue_move_up_button.setEnabled(editable and has_selection)
        self.queue_move_down_button.setEnabled(editable and has_selection)
        self.queue_clear_button.setEnabled(editable and has_items)

    def _refresh_history_panel_state(self) -> None:
        has_items = self.history_list.count() > 0
        has_selection = self.history_list.currentRow() >= 0
        self.history_stack.setCurrentIndex(
            self._history_content_index if has_items else self._history_empty_index
        )
        self.history_open_file_button.setEnabled(has_selection)
        self.history_open_folder_button.setEnabled(has_selection)
        self.history_clear_button.setEnabled(has_items)

    def _refresh_logs_panel_state(self) -> None:
        has_logs = bool(self._log_lines)
        self.logs_stack.setCurrentIndex(self._logs_content_index)
        self.logs_clear_button.setEnabled(has_logs)

    def _set_source_feedback(self, text: str, *, tone: str = "neutral") -> None:
        tone_value = (
            tone
            if tone in {"neutral", "loading", "success", "warning", "error", "hidden"}
            else "neutral"
        )
        message = str(text or "").strip()
        self._status_presenter.last_source_feedback_log = self._last_source_feedback_log
        self._status_presenter.set_source_feedback(
            text,
            tone=tone_value,
            append_log=self._append_log,
        )
        self._last_source_feedback_log = self._status_presenter.last_source_feedback_log
        self._current_source_feedback_message = message
        self._current_source_feedback_tone = tone_value
        self._source_feedback_version += 1
        self._dismissed_source_feedback_version = None
        self.source_feedback_label.setText(
            str(text or "Paste a video or playlist URL, then analyze it to load formats.")
        )
        self._set_widget_property(self.source_feedback_label, "tone", tone_value)
        self._sync_source_feedback_visibility()

    def _can_show_floating_source_feedback_toast(self) -> bool:
        return self.panel_stack.currentIndex() == self._main_page_index

    def _source_feedback_should_clear_toasts(self, tone: str, message: str) -> bool:
        return (
            not bool(message)
            or tone in {"", "neutral", "hidden"}
            or not self._can_show_floating_source_feedback_toast()
        )

    def _source_feedback_uses_toast(self, tone: str, message: str) -> bool:
        return (
            bool(message)
            and tone not in {"", "neutral", "hidden"}
            and self._can_show_floating_source_feedback_toast()
            and self._dismissed_source_feedback_version != self._source_feedback_version
        )

    def _sync_source_feedback_visibility(self) -> None:
        tone = self._current_source_feedback_tone
        message = self._current_source_feedback_message
        visibility_changed = self.source_feedback_label.isVisible()
        self.source_feedback_label.hide()
        if self._source_feedback_should_clear_toasts(tone, message):
            self._last_toasted_source_feedback_version = None
            self._hide_source_feedback_toast(animated=False)
        elif (
            self._source_feedback_uses_toast(tone, message)
            and self._last_toasted_source_feedback_version != self._source_feedback_version
        ):
            self._show_source_feedback_toast(message, tone=tone)
            self._last_toasted_source_feedback_version = self._source_feedback_version
        elif self._source_feedback_toasts:
            self._layout_source_feedback_toast()
        if visibility_changed:
            self._refresh_downloads_page_geometry()

    def _dismiss_source_feedback_toast(
        self,
        toast: _SourceFeedbackToastEntry | bool | None = None,
    ) -> None:
        entry = toast if isinstance(toast, _SourceFeedbackToastEntry) else None
        if entry is None:
            if not self._source_feedback_toasts:
                return
            entry = self._source_feedback_toasts[0]
        if self._source_feedback_toasts and entry is self._source_feedback_toasts[0]:
            self._dismissed_source_feedback_version = self._source_feedback_version
        self._remove_source_feedback_toast(entry, animated=True)

    def _set_metrics_visible(self, visible: bool) -> None:
        progress_visible = True
        visibility_changed = self.progress_bar.isVisible() != progress_visible
        self.progress_bar.setVisible(progress_visible)
        self.metrics_card.setVisible(True)
        self.metrics_strip.setVisible(True)
        self.item_label.setVisible(True)
        self._set_widget_property(
            self.metrics_card,
            "state",
            "active" if bool(visible) else "idle",
        )
        if visibility_changed:
            self._refresh_downloads_page_geometry()

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

    def _sync_output_form_row_heights(
        self,
        control_height: int | None = None,
        *,
        expand_visible_quality_row: bool = False,
    ) -> None:
        if control_height is None:
            control_height = max(
                0,
                self.container_combo.minimumHeight(),
                self.codec_combo.minimumHeight(),
                self.format_combo.minimumHeight(),
            )
        quality_row = None
        if len(getattr(self, "_output_form_rows", [])) >= 3:
            quality_row = self._output_form_rows[2]
        for row in getattr(self, "_output_form_rows", []):
            layout = row.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            target_height = max(control_height, row.minimumSizeHint().height())
            if expand_visible_quality_row and row is quality_row:
                target_height = max(target_height, row.sizeHint().height())
            row.setMinimumHeight(
                target_height
            )
            row.updateGeometry()
        save_layout = self.save_card.layout()
        if save_layout is not None:
            save_layout.invalidate()
            save_layout.activate()
        self.save_card.setMinimumHeight(
            max(
                self.save_card.minimumSizeHint().height(),
                self.save_card.sizeHint().height(),
            )
        )
        self.save_card.updateGeometry()

    def _sync_output_card_heights(self) -> None:
        if (
            self.format_card is self.save_card
            or self.output_layout.indexOf(self.format_card) < 0
            or self.output_layout.indexOf(self.save_card) < 0
        ):
            return
        cards = tuple(
            card
            for card in (self.format_card, self.save_card)
            if card is not None
        )
        if len(cards) < 2:
            return

        for card in cards:
            card.setMinimumHeight(0)
            card.setMaximumHeight(16777215)
            layout = card.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()

        target_height = max(
            max(card.minimumSizeHint().height(), card.sizeHint().height())
            for card in cards
        )
        output_parent = self.output_layout.parentWidget()
        available_height = (
            output_parent.contentsRect().height() if output_parent is not None else 0
        )
        required_height = (
            target_height * len(cards)
        ) + (self.output_layout.spacing() * (len(cards) - 1))
        if available_height < required_height:
            return
        for card in cards:
            card.setMinimumHeight(target_height)
            card.setMaximumHeight(target_height)
            card.updateGeometry()

    def _sync_run_section_split_widths(self) -> None:
        run_split_spacer = self.run_section.findChild(QWidget, "runSplitSpacer")
        if self.run_actions_card.parentWidget() is not self.run_section:
            target_width = (
                max(self.output_section.minimumWidth(), self.output_section.width())
                if self._output_layout_mode != "stacked"
                else 0
            )
            if run_split_spacer is not None:
                run_split_spacer.setMinimumWidth(target_width)
                run_split_spacer.setMaximumWidth(target_width)
            self.run_actions_card.setMinimumWidth(0)
            self.run_actions_card.setMaximumWidth(16777215)
            self.run_activity_card.setMinimumWidth(0)
            self.run_activity_card.setMaximumWidth(16777215)
            if run_split_spacer is not None:
                run_split_spacer.updateGeometry()
            return
        if self._output_layout_mode == "stacked":
            if run_split_spacer is not None:
                run_split_spacer.setMinimumWidth(0)
                run_split_spacer.setMaximumWidth(0)
            self.run_actions_card.setMinimumWidth(0)
            self.run_actions_card.setMaximumWidth(16777215)
            self.run_activity_card.setMinimumWidth(0)
            self.run_activity_card.setMaximumWidth(16777215)
            return

        target_width = max(
            self.output_section.minimumWidth(),
            self.output_section.width(),
        )
        if target_width > 0:
            self.run_actions_card.setMinimumWidth(target_width)
            self.run_actions_card.setMaximumWidth(target_width)
        if run_split_spacer is not None:
            run_split_spacer.setMinimumWidth(0)
            run_split_spacer.setMaximumWidth(0)
        self.run_activity_card.setMinimumWidth(0)
        self.run_activity_card.setMaximumWidth(16777215)
        self.run_actions_card.updateGeometry()
        self.run_activity_card.updateGeometry()

    def _refresh_downloads_page_geometry(self) -> None:
        self.workspace_layout.invalidate()
        self.workspace_layout.activate()
        self.output_layout.invalidate()
        self.output_layout.activate()
        output_width = max(0, self.output_section.contentsRect().width() - 8)
        if output_width > 0:
            self.format_card.setMaximumWidth(output_width)
            self.format_card.updateGeometry()
        refreshed_widgets: list[QWidget] = []
        for widget in (
            self.source_preview_card.parentWidget(),
            self.format_card,
            self.save_card,
            self.output_section,
            self.ready_summary_label.parentWidget(),
            self.main_page,
        ):
            if widget is None or widget in refreshed_widgets:
                continue
            refreshed_widgets.append(widget)
            widget.updateGeometry()
            layout = widget.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
        main_layout = self.main_page.layout()
        if main_layout is not None:
            main_layout.invalidate()
            main_layout.activate()
        self._sync_output_card_heights()
        if main_layout is not None:
            main_layout.invalidate()
            main_layout.activate()
        self._sync_run_section_split_widths()
        if main_layout is not None:
            main_layout.invalidate()
            main_layout.activate()
        self._sync_current_panel_geometry()

    def _queue_deferred_resize_sync(self) -> None:
        self._resize_sync_timer.start(0)

    def _run_deferred_resize_sync(self) -> None:
        self._refresh_downloads_page_geometry()
        for widget in (
            self.main_page,
            self.output_section,
            self.format_card,
            self.save_card,
            self.run_section,
        ):
            layout = widget.layout()
            if layout is not None:
                layout.activate()
        self._layout_mixed_url_overlay()
        self._layout_source_feedback_toast()
        self._refresh_current_item_text()
        self._refresh_download_result_view()
        if self._latest_output_path is not None:
            self._refresh_last_output_text()

    def _sync_current_panel_geometry(self) -> None:
        current = self.panel_stack.currentWidget()
        if current is None:
            return
        current.setGeometry(self.panel_stack.contentsRect())
        layout = current.layout()
        if layout is not None:
            layout.activate()

    def _refresh_ready_summary(self) -> None:
        show_summary = any(
            (
                bool(self._current_mode()),
                bool(self._current_container()),
                bool(self._current_codec()),
                bool(self._selected_format_label()),
            )
        )
        visibility_changed = self.ready_summary_label.isVisible() != show_summary
        self.ready_summary_label.setVisible(show_summary)
        if not show_summary:
            self._refresh_queue_preview_card()
            if visibility_changed:
                self._refresh_downloads_page_geometry()
            return
        container = self._current_container()
        container_text = container.upper() if container else "Container"
        codec_text = self._ready_summary_codec()
        quality_text = self._ready_summary_quality(self._selected_format_label())
        folder_text = self._ready_summary_folder()
        self.ready_summary_label.setText(
            f"{container_text} • {codec_text} • {quality_text} • {folder_text}"
        )
        self._refresh_queue_preview_card()
        if visibility_changed:
            self._refresh_downloads_page_geometry()

    def _workspace_view_index(self, name: str) -> int:
        mapping = {
            "queue": self._queue_view_index,
            "history": self._history_view_index,
        }
        return mapping.get(name, self._queue_view_index)

    def _select_workspace_view(self, name: str) -> None:
        target = name if name in {"queue", "history"} else "queue"
        self._active_workspace_name = target
        self.source_view_stack.setCurrentIndex(self._workspace_view_index(target))
        self.queue_view_button.setChecked(target == "queue")
        self.history_view_button.setChecked(target == "history")
        if self._active_panel_name is None:
            self.downloads_button.setChecked(True)
            self.session_button.setChecked(False)
            self.queue_button.setChecked(False)
            self.history_button.setChecked(False)
            self.settings_button.setChecked(False)
            self.logs_button.setChecked(False)
        self._refresh_top_action_icons()

    def _show_main_workspace(self, name: str = "queue") -> None:
        target = name if name in {"queue", "history"} else "queue"
        window_size = self.size()
        if self.panel_stack.currentIndex() != self._main_page_index:
            self.panel_stack.setCurrentIndex(self._main_page_index)
            self._sync_current_panel_geometry()
            self._animate_widget_fade_in(self.panel_stack.currentWidget())
        self._active_panel_name = None
        self._select_workspace_view(target)
        self._set_mixed_url_alert_visible(bool(self._pending_mixed_url))
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _apply_header_layout(self) -> None:
        self.classic_actions.setVisible(True)
        self.downloads_button.setVisible(True)
        self.session_button.setVisible(True)
        self.queue_button.setVisible(True)
        self.history_button.setVisible(True)
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

    def _apply_window_icon(self) -> None:
        path = Path(__file__).resolve().parent / "assets" / APP_ICON_FILENAME
        if not path.exists():
            return
        icon = QIcon(path.as_posix())
        if icon.isNull():
            return
        # macOS dock identity follows the native QWindow icon once the handle exists.
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        handle = self.windowHandle()
        if handle is not None:
            handle.setIcon(icon)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._normalize_control_sizing()
        self._apply_responsive_layout()
        self._stabilize_source_preview_card_sizing()
        self._refresh_downloads_page_geometry()
        self._apply_window_icon()

    def _set_header_icons_enabled(self, enabled: bool) -> None:
        enabled_flag = bool(enabled)
        if self._header_icons_enabled == enabled_flag:
            return
        self._header_icons_enabled = enabled_flag
        self._refresh_top_action_icons()

    def _register_shortcut(
        self,
        sequence: QKeySequence | str,
        callback,
    ) -> None:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def _install_shortcuts(self) -> None:
        for sequence in ("Ctrl+L", "Meta+L"):
            self._register_shortcut(sequence, self._focus_url_input)
        for sequence in ("Ctrl+,", "Meta+,"):
            self._register_shortcut(sequence, lambda: self._open_panel("settings"))
        self._register_shortcut("F1", self._show_about_dialog)

    def _focus_url_input(self) -> None:
        if self._active_panel_name is not None:
            self._close_panel()
        if self.url_edit.isVisible():
            self.url_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self.url_edit.selectAll()
            return
        self.paste_button.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _show_about_dialog(self) -> None:
        shortcuts = (
            "Cmd/Ctrl+L: Focus source actions\n"
            "Cmd/Ctrl+V: Paste URL when another text field is not active\n"
            "Cmd/Ctrl+,: Open settings\n"
            "F1: About"
        )
        self._effects.dialogs.information(
            self,
            f"About {APP_DISPLAY_NAME}",
            (
                f"{APP_DISPLAY_NAME}\n"
                f"Version {APP_VERSION}\n\n"
                f"{APP_DESCRIPTION}\n\n"
                "Downloads stay on this machine.\n\n"
                f"Shortcuts:\n{shortcuts}"
            ),
        )

    def _focus_widget_accepts_text_input(self) -> bool:
        focus = self.focusWidget()
        if isinstance(focus, QLineEdit):
            return not focus.isReadOnly()
        if isinstance(focus, QPlainTextEdit):
            return not focus.isReadOnly()
        combo = focus if isinstance(focus, QComboBox) else None
        if combo is not None and combo.isEditable():
            line_edit = combo.lineEdit()
            return bool(line_edit and not line_edit.isReadOnly())
        return False

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
            ("session", self.session_button),
            ("settings", self.settings_button),
            ("queue", self.queue_button),
            ("history", self.history_button),
            ("logs", self.logs_button),
        ):
            if self._active_panel_name is not None:
                is_checked = self._active_panel_name == name
            else:
                is_checked = {
                    "downloads": True,
                    "session": False,
                    "queue": False,
                    "history": False,
                    "settings": False,
                    "logs": False,
                }.get(name, False)
            icon = QIcon()
            if self._header_icons_enabled:
                icon = self._panel_icon(
                    name,
                    checked=is_checked,
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
                self.session_button,
                self.settings_button,
                self.queue_button,
                self.history_button,
                self.logs_button,
            ],
            extra_px=12,
            fixed=True,
        )
        sync_selection = getattr(self.classic_actions, "sync_selection", None)
        if callable(sync_selection):
            sync_selection()

    def _configure_top_action_icons(self) -> None:
        self._top_action_icons = {
            "downloads": {
                "normal": self._load_asset_icon("downloads.svg"),
                "active": self._load_asset_icon("downloads-active.svg"),
            },
            "session": {
                "normal": self._load_asset_icon("session.svg"),
                "active": self._load_asset_icon("session-active.svg"),
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
        self, widget: QWidget | None, *, duration_ms: int = PANEL_SWITCH_FADE_MS
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
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._track_animation(anim)
        anim.start()

    def _open_panel(self, name: str) -> None:
        window_size = self.size()
        index = self._panel_name_to_index.get(name)
        if index is None:
            return
        self.panel_stack.setCurrentIndex(index)
        self._sync_current_panel_geometry()
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
        if (
            self._active_panel_name is None
            and self.panel_stack.currentIndex() == self._main_page_index
        ):
            self._select_workspace_view(self._active_workspace_name)
            self._set_mixed_url_alert_visible(bool(self._pending_mixed_url))
            return
        window_size = self.size()
        self.panel_stack.setCurrentIndex(self._main_page_index)
        self._sync_current_panel_geometry()
        self._animate_widget_fade_in(self.panel_stack.currentWidget())
        self._active_panel_name = None
        self._select_workspace_view(self._active_workspace_name)
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

    def _source_feedback_toast_timeout_ms(self, tone: str) -> int:
        if tone == "loading":
            return 2800
        if tone == "success":
            return 3400
        if tone == "warning":
            return 4600
        if tone == "error":
            return 5200
        return 0

    def _source_feedback_toast_title(self, tone: str) -> str:
        if tone == "loading":
            return "Loading formats"
        if tone == "success":
            return "Formats ready"
        if tone == "warning":
            return "Check source"
        if tone == "error":
            return "Could not load formats"
        return APP_DISPLAY_NAME

    def _source_feedback_toast_anchor_rect(self) -> QRect:
        header = getattr(self, "top_actions", None)
        header_widget = header.parentWidget() if header is not None else None
        if header_widget is not None:
            return header_widget.geometry()
        return self.panel_stack.geometry()

    def _source_feedback_toast_entry(
        self,
        parent: QWidget | None = None,
    ) -> _SourceFeedbackToastEntry:
        toast_parent = parent or self._source_feedback_toast_parent or self.centralWidget()
        if toast_parent is None:
            toast_parent = self
        source_toast = QFrame(toast_parent)
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
        timer = QTimer(source_toast)
        timer.setSingleShot(True)
        entry = _SourceFeedbackToastEntry(
            card=source_toast,
            title_label=source_toast_title,
            message_label=source_toast_message,
            dismiss_button=source_toast_dismiss_button,
            timer=timer,
        )
        source_toast_dismiss_button.clicked.connect(
            lambda checked=False, toast=entry: self._dismiss_source_feedback_toast(toast)
        )
        timer.timeout.connect(lambda toast=entry: self._dismiss_source_feedback_toast(toast))
        return entry

    def _sync_source_feedback_toast_refs(self) -> None:
        entry = self._source_feedback_toasts[0] if self._source_feedback_toasts else self._source_feedback_toast_placeholder
        if entry is None:
            return
        self.source_feedback_toast = entry.card
        self.source_feedback_toast_title = entry.title_label
        self.source_feedback_toast_message = entry.message_label
        self.source_feedback_toast_dismiss_button = entry.dismiss_button

    def _source_feedback_toast_target_rects(
        self,
        toasts: list[_SourceFeedbackToastEntry] | None = None,
    ) -> list[QRect]:
        toast_items = list(toasts if toasts is not None else self._source_feedback_toasts)
        if not toast_items:
            return []
        anchor_rect = self._source_feedback_toast_anchor_rect()
        max_width = max(260, min(340, anchor_rect.width() - 36))
        y = anchor_rect.top() + 18
        rects: list[QRect] = []
        for entry in toast_items:
            entry.card.setMaximumWidth(max_width)
            layout = entry.card.layout()
            if layout is not None:
                layout.activate()
            entry.card.adjustSize()
            hint = entry.card.sizeHint()
            width = max(
                entry.card.minimumWidth(),
                min(max_width, hint.width()),
            )
            height = hint.height()
            x = anchor_rect.right() - width - 18
            rects.append(QRect(x, y, width, height))
            y += height + 10
        return rects

    def _source_feedback_toast_target_rect(self) -> QRect:
        rects = self._source_feedback_toast_target_rects(self._source_feedback_toasts[:1])
        return rects[0] if rects else QRect()

    def _source_feedback_toast_hidden_rect(self, target: QRect) -> QRect:
        anchor_rect = self._source_feedback_toast_anchor_rect()
        return QRect(
            anchor_rect.right() + 24,
            target.y(),
            target.width(),
            target.height(),
        )

    def _stop_source_feedback_toast_animation(
        self,
        toast: _SourceFeedbackToastEntry,
    ) -> None:
        if toast.animation is None:
            return
        toast.animation.stop()
        toast.animation.deleteLater()
        toast.animation = None

    def _complete_source_feedback_toast_animation(
        self,
        toast: _SourceFeedbackToastEntry,
        animation: QPropertyAnimation,
    ) -> None:
        if toast.animation is animation:
            toast.animation = None
        animation.deleteLater()

    def _dispose_source_feedback_toast(
        self,
        toast: _SourceFeedbackToastEntry,
    ) -> None:
        self._stop_source_feedback_toast_animation(toast)
        if toast.timer is not None:
            toast.timer.stop()
            toast.timer.deleteLater()
        toast.card.hide()
        if not toast.placeholder:
            toast.card.deleteLater()

    def _complete_source_feedback_toast_exit(
        self,
        toast: _SourceFeedbackToastEntry,
        animation: QPropertyAnimation,
    ) -> None:
        if toast.animation is animation:
            toast.animation = None
        animation.deleteLater()
        self._dispose_source_feedback_toast(toast)

    def _animate_source_feedback_toast(
        self,
        toast: _SourceFeedbackToastEntry,
        *,
        start_rect: QRect,
        end_rect: QRect,
        duration_ms: int,
        easing_curve: QEasingCurve.Type,
        delete_after: bool = False,
    ) -> None:
        self._stop_source_feedback_toast_animation(toast)
        if start_rect == end_rect:
            toast.card.setGeometry(end_rect)
            if delete_after:
                self._dispose_source_feedback_toast(toast)
            return
        anim = QPropertyAnimation(toast.card, b"geometry", self)
        anim.setDuration(duration_ms)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.setEasingCurve(easing_curve)
        if delete_after:
            anim.finished.connect(
                lambda toast=toast, animation=anim: self._complete_source_feedback_toast_exit(
                    toast, animation
                )
            )
        else:
            anim.finished.connect(
                lambda toast=toast, animation=anim: self._complete_source_feedback_toast_animation(
                    toast, animation
                )
            )
        toast.animation = anim
        anim.start()

    def _trim_source_feedback_toasts(self) -> None:
        while len(self._source_feedback_toasts) > 4:
            oldest = self._source_feedback_toasts.pop()
            self._dispose_source_feedback_toast(oldest)

    def _remove_source_feedback_toast(
        self,
        toast: _SourceFeedbackToastEntry,
        *,
        animated: bool,
    ) -> None:
        if toast not in self._source_feedback_toasts:
            return
        self._source_feedback_toasts.remove(toast)
        current_rect = toast.card.geometry()
        self._sync_source_feedback_toast_refs()
        self._reflow_source_feedback_toasts(animated=animated)
        if not animated or not toast.card.isVisible():
            self._dispose_source_feedback_toast(toast)
            return
        self._animate_source_feedback_toast(
            toast,
            start_rect=current_rect,
            end_rect=self._source_feedback_toast_hidden_rect(current_rect),
            duration_ms=220,
            easing_curve=QEasingCurve.Type.InCubic,
            delete_after=True,
        )

    def _reflow_source_feedback_toasts(self, *, animated: bool) -> None:
        if not self._source_feedback_toasts:
            return
        for toast, target in zip(
            self._source_feedback_toasts,
            self._source_feedback_toast_target_rects(),
        ):
            current = toast.card.geometry()
            if not toast.card.isVisible():
                current = self._source_feedback_toast_hidden_rect(target)
                toast.card.setGeometry(current)
                toast.card.show()
            if animated:
                self._animate_source_feedback_toast(
                    toast,
                    start_rect=current,
                    end_rect=target,
                    duration_ms=240,
                    easing_curve=QEasingCurve.Type.OutCubic,
                )
            else:
                self._stop_source_feedback_toast_animation(toast)
                toast.card.setGeometry(target)
        for toast in reversed(self._source_feedback_toasts):
            toast.card.raise_()

    def _layout_source_feedback_toast(self) -> None:
        if not self._source_feedback_toasts:
            return
        self._reflow_source_feedback_toasts(animated=False)

    def _show_source_feedback_toast(self, text: str, *, tone: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            self._hide_source_feedback_toast()
            return
        toast = self._source_feedback_toast_entry()
        toast.title_label.setText(self._source_feedback_toast_title(tone))
        toast.message_label.setText(clean)
        self._set_widget_property(toast.card, "tone", str(tone or "success"))
        self._source_feedback_toasts.insert(0, toast)
        self._trim_source_feedback_toasts()
        self._sync_source_feedback_toast_refs()
        targets = self._source_feedback_toast_target_rects()
        for entry, target in zip(self._source_feedback_toasts, targets):
            current = entry.card.geometry()
            if entry is toast or not entry.card.isVisible():
                current = self._source_feedback_toast_hidden_rect(target)
            entry.card.setGeometry(current)
            entry.card.show()
            self._animate_source_feedback_toast(
                entry,
                start_rect=current,
                end_rect=target,
                duration_ms=280,
                easing_curve=QEasingCurve.Type.OutCubic,
            )
        for entry in reversed(self._source_feedback_toasts):
            entry.card.raise_()
        timeout_ms = self._source_feedback_toast_timeout_ms(tone)
        if timeout_ms > 0 and toast.timer is not None:
            toast.timer.start(timeout_ms)

    def _hide_source_feedback_toast(self, *, animated: bool = True) -> None:
        if not self._source_feedback_toasts:
            return
        toasts = list(self._source_feedback_toasts)
        self._source_feedback_toasts.clear()
        self._sync_source_feedback_toast_refs()
        for toast in toasts:
            if not animated or not toast.card.isVisible():
                self._dispose_source_feedback_toast(toast)
                continue
            current_rect = toast.card.geometry()
            self._animate_source_feedback_toast(
                toast,
                start_rect=current_rect,
                end_rect=self._source_feedback_toast_hidden_rect(current_rect),
                duration_ms=220,
                easing_curve=QEasingCurve.Type.InCubic,
                delete_after=True,
            )

    def _visible_source_feedback_toasts(self) -> list[_SourceFeedbackToastEntry]:
        return [toast for toast in self._source_feedback_toasts if toast.card.isVisible()]

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
        self._sync_format_combo_visibility()

    def _selected_format_label(self) -> str:
        return self.format_combo.currentText().strip()

    def _sync_format_combo_visibility(self) -> None:
        has_quality_options = self.format_combo.count() > 0
        has_formats_data = bool(self._video_labels or self._audio_labels)
        if has_quality_options:
            placeholder_text = "Choose exact format/quality."
        elif has_formats_data:
            placeholder_text = "No exact matches for this filter."
        else:
            placeholder_text = "Analyze a URL to load quality."
        self.format_combo.setPlaceholderText(placeholder_text)

        label_text = "Codec & quality"
        visibility_changed = not self.format_combo.isVisible()
        label_changed = self.codec_label.text() != label_text
        self.format_combo.setVisible(True)
        self.codec_label.setText(label_text)
        if visibility_changed or label_changed:
            self._sync_output_form_row_heights(
                expand_visible_quality_row=True
            )
            self._refresh_downloads_page_geometry()

    def _selected_format_info(self) -> dict | None:
        label = self._selected_format_label()
        if not label:
            return None
        return self._filtered_lookup.get(label)

    def _snapshot_download_options(self) -> DownloadOptions:
        return app_service.build_download_options(
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

    def _run_single_download_worker(
        self,
        *,
        request: DownloadRequest,
        history_title: str,
        history_settings: QueueSettings,
    ) -> None:
        self._run_queue_controller.run_single_download_worker(
            request=request,
            history_title=history_title,
            history_settings=history_settings,
        )

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

    def _queue_remove_row(self, row: int) -> None:
        self._run_queue_controller.on_queue_remove_selected([int(row)])

    def _queue_move_up(self) -> None:
        self._run_queue_controller.on_queue_move_up(self._queue_selection_rows())

    def _queue_move_down(self) -> None:
        self._run_queue_controller.on_queue_move_down(self._queue_selection_rows())

    def _queue_reorder_items(self, item_order: list[int]) -> None:
        self._run_queue_controller.on_queue_reorder([int(row) for row in item_order])

    def _queue_clear(self) -> None:
        self._run_queue_controller.on_queue_clear()

    def _append_workspace_summary_item(
        self,
        list_widget,
        *,
        badge_text: str,
        title: str,
        meta: str,
        status_text: str = "",
        progress_percent: float | None = None,
        tone: str = "default",
        tooltip: str = "",
    ) -> None:
        widget = WorkspaceSummaryWidget(
            badge_text=badge_text,
            title=title,
            meta=meta,
            status_text=status_text,
            progress_percent=progress_percent,
            tone=tone,
        )
        item = QListWidgetItem(list_widget)
        item.setSizeHint(widget.sizeHint())
        if tooltip:
            item.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        list_widget.addItem(item)
        list_widget.setItemWidget(item, widget)

    def _sync_queue_workspace_view(self) -> None:
        target_index = self._queue_workspace_preview_index
        if self.queue_workspace_stack.currentIndex() != target_index:
            self.queue_workspace_stack.setCurrentIndex(target_index)

    def _refresh_queue_panel(self) -> None:
        self.queue_list.clear()
        self.queue_summary_list.clear()
        summary_context = queue_presentation.QueueSummaryContext(
            current_url=self.url_edit.text(),
            current_preview_title=self._preview_title_raw,
            current_item_title=self._current_item_title_tooltip,
            progress_text=self.progress_label.text(),
            speed_text=self.speed_label.text(),
            eta_text=self.eta_label.text(),
        )
        for idx, item in enumerate(self.queue_items, start=1):
            is_active = (
                self.queue_active
                and self.queue_index is not None
                and (idx - 1) == self.queue_index
            )
            text = queue_presentation.build_queue_list_text(
                item,
                idx=idx,
                active=is_active,
            )
            list_item = QListWidgetItem(text)
            list_item.setData(QUEUE_SOURCE_INDEX_ROLE, idx - 1)
            list_item.setToolTip(text)
            self.queue_list.addItem(list_item)
        summary_start = 0
        if self.queue_active and self.queue_index is not None:
            summary_start = max(0, min(int(self.queue_index), len(self.queue_items)))
        for idx, item in enumerate(
            self.queue_items[summary_start:],
            start=summary_start + 1,
        ):
            is_active = (
                self.queue_active
                and self.queue_index is not None
                and (idx - 1) == self.queue_index
            )
            summary = queue_presentation.build_queue_summary_entry(
                item,
                idx=idx,
                active=is_active,
                context=summary_context,
            )
            self._append_workspace_summary_item(
                self.queue_summary_list,
                badge_text=summary.badge_text,
                title=summary.title,
                meta=summary.meta,
                status_text=summary.status_text,
                progress_percent=(self.progress_bar.value() / 10.0) if is_active else None,
                tone=summary.tone,
                tooltip=summary.list_text,
            )
        self._refresh_queue_panel_state()
        has_items = self.queue_summary_list.count() > 0
        self.queue_summary_empty.set_recent_items(
            self._queue_empty_recent_items() if not has_items else []
        )
        self.queue_summary_list.setVisible(has_items)
        self.queue_summary_empty.setVisible(not has_items)
        self._sync_queue_workspace_view()
        self._refresh_queue_preview_card()

    def _on_record_output(
        self,
        output_path_raw: str,
        source_url: str,
        metadata: object = None,
    ) -> None:
        payload = dict(metadata) if isinstance(metadata, dict) else None
        self._record_download_output(Path(output_path_raw), source_url, payload)

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
            mixed_prompt_active=bool(self._pending_mixed_url),
            playlist_items_requested=bool(self._playlist_mode),
            allow_queue_input_context=False,
            audio_containers=AUDIO_CONTAINERS,
            video_containers=VIDEO_CONTAINERS,
        )
        apply_control_state(
            self,
            state,
            pending_mixed_url=self._pending_mixed_url,
        )
        self._sync_format_combo_visibility()
        self._refresh_download_sections_state(
            url_present=url_present,
            has_formats_data=has_formats_data,
            is_fetching=self._is_fetching,
        )

        self._refresh_ready_summary()
        self._refresh_download_result_view()
        self._sync_current_panel_geometry()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.matches(QKeySequence.StandardKey.Paste)
            and not self._focus_widget_accepts_text_input()
        ):
            self._focus_url_input()
            self._paste_url()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._normalize_control_sizing()
        self._apply_responsive_layout()
        self._refresh_downloads_page_geometry()
        self._layout_mixed_url_overlay()
        self._layout_source_feedback_toast()
        self._refresh_current_item_text()
        if self._is_downloading:
            self._set_metrics_visible(True)
        self._refresh_download_result_view()
        if self._latest_output_path is not None:
            self._refresh_last_output_text()
        self._queue_deferred_resize_sync()

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
    _apply_tooltip_delay_style(app)
    app.setApplicationName(APP_REPO_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION_NAME)
    app.setOrganizationDomain(APP_ORGANIZATION_DOMAIN)
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName(APP_BUNDLE_IDENTIFIER)
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
    window._apply_window_icon()
    if owns_app:
        return int(app.exec())
    return 0
