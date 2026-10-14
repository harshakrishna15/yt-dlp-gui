from __future__ import annotations

import signal
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QSignalBlocker,
    QRect,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QListView,
    QMainWindow,
    QPlainTextEdit,
    QProxyStyle,
    QPushButton,
    QStyle,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..common import settings_store
from ..common import format_pipeline
from ..app_meta import (
    APP_BUNDLE_IDENTIFIER,
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_ICON_FILENAME,
    APP_ORGANIZATION_DOMAIN,
    APP_ORGANIZATION_NAME,
    APP_PRIVACY_NOTE,
    APP_REPO_NAME,
    APP_SHORTCUT_LINES,
    APP_VERSION,
)
from .assets_manifest import asset_path
from .icon_assets import load_icon_asset, style_asset_path
from . import style as qt_style
from .constants import (
    AUDIO_CONTAINERS,
    CODECS,
    DEFAULT_AUDIO_CONTAINER,
    DEFAULT_VIDEO_CONTAINER,
    DEFAULT_VIDEO_CODEC,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FETCH_DEBOUNCE_MS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    OUTPUT_CARD_STACK_GAP,
    ROOMY_CONTENT_LAYOUT_MIN_HEIGHT,
    SOURCE_DETAILS_NONE_INDEX,
    SOURCE_DETAILS_PLAYLIST_INDEX,
    TOOLTIP_WAKE_UP_DELAY_MS,
    TOP_ACTION_ICON_PX,
    VIDEO_CONTAINERS,
)
from .controllers import (
    RunQueueController,
    RunQueueState,
    SourceController,
    SourceState,
)
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
from .widgets import (
    build_form_scroll,
    QUEUE_META_ROLE,
    QUEUE_COMPLETED_ROLE,
    QUEUE_STATUS_ROLE,
    QUEUE_SOURCE_INDEX_ROLE,
    QUEUE_TITLE_ROLE,
    StableSizeHintButton,
    _NativeComboBox,
    _QtSignals,
)
from ..common.types import DownloadOptions, DownloadRequest, QueueItem, QueueSettings


@dataclass(frozen=True)
class _ResponsiveLayoutProfile:
    output_mode: str
    workspace_direction: QBoxLayout.Direction
    compact_content: bool



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


class _TooltipBlocker(QObject):
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is not None and event.type() == QEvent.Type.ToolTip:
            if watched is not None and watched.property("allowToolTip"):
                return False
            QToolTip.hideText()
            event.accept()
            return True
        return super().eventFilter(watched, event)


def _disable_tooltips(app: QApplication) -> None:
    blocker_name = "_tooltipBlocker"
    if app.findChild(_TooltipBlocker, blocker_name) is not None:
        return
    blocker = _TooltipBlocker(app)
    blocker.setObjectName(blocker_name)
    app.installEventFilter(blocker)


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
        app = QApplication.instance()
        if app is not None:
            app.styleHints().setColorScheme(Qt.ColorScheme.Light)
            _disable_tooltips(app)
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self._native_combos: list[_NativeComboBox] = []
        self._active_animations: list[QPropertyAnimation] = []
        self._shortcuts: list[QShortcut] = []
        self._progress_anim: QPropertyAnimation | None = None
        self._advanced_anim: QVariantAnimation | None = None
        self._feedback_dismissed = False
        self._feedback_action = ""
        self._feedback_output_dir: Path | None = None
        self._logs_alert_active = False
        self._header_icons_enabled = True
        self._legacy_log_alert_icon = self._build_alert_dot_icon()
        self._top_action_icons: dict[str, dict[str, QIcon]] = {}
        self._output_layout_mode: str | None = None
        self._source_row_control_height = 0
        self._effects = effects or build_qt_side_effect_ports()
        self._source_state = SourceState()
        self._run_queue_state = RunQueueState()
        self._yt_dlp_update_in_progress = False
        self._yt_dlp_binary_source = ""
        self._tool_checks_pending = True
        self._tool_checks_started = False
        self._close_after_tool_checks = False

        self._signals = _QtSignals()
        self._signals.formats_loaded.connect(self._on_formats_loaded)
        self._signals.tool_checks_done.connect(self._on_tool_checks_done)
        self._signals.analysis_progress.connect(
            lambda request_id, url, text: self._source_controller.on_analysis_progress(
                request_id, url, text
            )
        )
        self._signals.progress.connect(self._queue_progress_update)
        self._signals.log.connect(self._append_log)
        self._signals.download_done.connect(self._on_download_done)
        self._signals.queue_item_done.connect(self._on_queue_item_done)
        self._signals.yt_dlp_update_done.connect(self._on_yt_dlp_update_done)
        self._signals.yt_dlp_update_progress.connect(self._on_yt_dlp_update_progress)
        self._signals.app_data_cleanup_done.connect(self._on_app_data_cleanup_done)

        self._fetch_timer = QTimer(self)
        self._fetch_timer.setInterval(FETCH_DEBOUNCE_MS)
        self._fetch_timer.setSingleShot(True)
        self._fetch_timer.timeout.connect(self._start_fetch_formats)
        self._analysis_timer = QTimer(self)
        self._analysis_timer.setInterval(500)
        self._analysis_timer.timeout.connect(self._update_analysis_elapsed)
        self._progress_update_timer = QTimer(self)
        self._progress_update_timer.setInterval(100)
        self._progress_update_timer.setSingleShot(True)
        self._progress_update_timer.timeout.connect(self._flush_progress_updates)
        self._pending_progress: dict | None = None
        self._log_update_timer = QTimer(self)
        self._log_update_timer.setInterval(100)
        self._log_update_timer.setSingleShot(True)
        self._log_update_timer.timeout.connect(self._flush_log_updates)
        self._resize_sync_timer = QTimer(self)
        self._resize_sync_timer.setSingleShot(True)
        self._resize_sync_timer.timeout.connect(self._run_deferred_resize_sync)
        self._resize_profile_key: tuple | None = None

        self.queue_empty_state = None

        self._log_lines: list[str] = []
        self._pending_log_lines: list[str] = []
        self._logs_view_dirty = False
        self._last_error_log = ""
        self._last_source_feedback_log: tuple[str, str] | None = None
        self._current_source_feedback_message = ""
        self._current_source_feedback_tone = "neutral"
        self._current_source_feedback_title = ""
        self._status_presenter = StatusPresenter()
        self._active_panel_name: str | None = None
        self._applying_user_settings = False
        self._post_download_output_dir: Path | None = None
        self._pending_queue_edit_settings: QueueSettings | None = None
        self._source_summary_data: dict[str, object] = {}
        self._preview_title_raw = ""
        self._ready_summary_full_text = ""
        self._activity_stage = ""
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
        self._apply_window_icon()

        self._build_ui()
        self._update_source_details_visibility()
        self._set_preview_title("")
        self._set_source_summary(None)
        self._set_mode_unselected()
        self._reset_progress_summary()
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
            on_advanced_toggled=self._set_advanced_expanded,
            on_use_single_video_url=lambda: self._apply_mixed_url_choice(
                use_playlist=False
            ),
            on_use_playlist_url=lambda: self._apply_mixed_url_choice(use_playlist=True),
            run=RunSectionCallbacks(
                on_start=self._on_start,
                on_add_to_queue=self._on_add_to_queue,
                on_cancel=self._on_cancel,
            ),
        )
        ui = MainUiBuilder.build(
            window=self,
            register_native_combo=self._register_native_combo,
            callbacks=callbacks,
        )
        self.setCentralWidget(ui.root)
        self._bind_ui_refs(ui)
        self.content_column = ui.content_column
        self.form_scroll = ui.downloads.form_scroll
        self.media_summary = ui.downloads.media_summary
        self.media_title = ui.downloads.media_title
        self.media_detail = ui.downloads.media_detail
        self.source_hint = ui.downloads.source_hint
        # The activity belongs to the window, outside every page's scroll area.
        self.output_layout.removeWidget(self.metrics_card)
        self.run_actions_layout.removeWidget(self.cancel_button)
        activity_layout = self.metrics_card.layout()
        while activity_layout.count():
            activity_layout.takeAt(0)
        self.item_label.setParent(self.metrics_card)
        activity_layout.addWidget(self.item_label)
        activity_row = QWidget(self.metrics_card)
        row_layout = QHBoxLayout(activity_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)
        row_layout.addWidget(self.progress_bar, 1)
        row_layout.addWidget(self.metrics_strip)
        row_layout.addWidget(self.cancel_button)
        activity_layout.addWidget(activity_row)
        ui.content_column.layout().addWidget(self.metrics_card)
        self.progress_bar.setAccessibleName("Download progress")
        self.item_label.setTextFormat(Qt.TextFormat.PlainText)
        self._sync_source_details_height()
        self._set_output_form_label_width(min_width=112)

        settings_panel = self._build_settings_panel()
        queue_panel = self._build_queue_panel()
        logs_panel = self._build_logs_panel()

        self._panel_name_to_index = {
            "settings": self.panel_stack.addWidget(build_form_scroll(settings_panel, self.panel_stack)),
            "queue": self.panel_stack.addWidget(queue_panel),
            "logs": self.panel_stack.addWidget(logs_panel),
        }
        self._panel_buttons = {
            "downloads": self.downloads_button,
            "settings": self.settings_button,
            "queue": self.queue_button,
        }
        self._configure_top_action_icons()

        self.downloads_button.clicked.connect(
            lambda _checked: self._show_main_workspace()
        )
        self.settings_button.clicked.connect(
            lambda _checked: self._toggle_panel("settings")
        )
        self.queue_button.clicked.connect(lambda _checked: self._toggle_panel("queue"))
        self.logs_button.clicked.connect(lambda _checked: self._toggle_panel("logs"))
        self._set_main_workspace_selection()

        combo_arrow_path = style_asset_path(
            "combo-down-arrow.svg",
            size=QSize(10, 6),
        )
        self.setPalette(qt_style.light_palette())
        QApplication.instance().setPalette(qt_style.light_palette())
        self.setStyleSheet(qt_style.build_stylesheet(combo_arrow_path))
        self._normalize_control_sizing()
        self._set_logs_alert(False)
        self._install_tooltips()
        self._install_shortcuts()
        self._apply_responsive_layout()
        self._refresh_queue_panel()
        self._refresh_logs_panel_state()
        self._set_source_feedback(
            "Paste a video or playlist URL to load available formats.",
            tone="neutral",
        )

    def _bind_ui_refs(self, ui: UiRefs) -> None:
        self._ui = ui
        self.panel_stack = ui.panel_stack

        top = ui.top_bar
        self.top_actions = top.header
        self.classic_actions = top.classic_actions
        self.downloads_button = top.downloads_button
        self.queue_button = top.queue_button
        self.settings_button = top.settings_button

        mixed = ui.mixed_url
        self.mixed_url_overlay = mixed.overlay
        self.mixed_url_overlay_layout = mixed.overlay_layout
        self.mixed_url_alert = mixed.alert
        self.mixed_url_alert_label = mixed.alert_label
        self.mixed_buttons_layout = mixed.buttons_layout
        self.use_single_video_url_button = mixed.use_single_video_url_button
        self.use_playlist_url_button = mixed.use_playlist_url_button

        feedback = ui.feedback
        self.feedback_row = feedback.row
        self.feedback_message = feedback.message_label
        self.feedback_action_button = feedback.action_button
        self.feedback_dismiss_button = feedback.dismiss_button
        self.analysis_progress_bar = feedback.progress_bar
        self.analysis_elapsed_label = feedback.elapsed_label
        self.feedback_action_button.clicked.connect(self._activate_feedback_action)
        self.feedback_dismiss_button.clicked.connect(self._dismiss_feedback)

        downloads = ui.downloads
        self.main_page = downloads.main_page
        self._main_page_index = downloads.main_page_index
        self.workspace_layout = downloads.workspace_layout
        self.source_row = downloads.source_row
        self.url_edit = downloads.url_edit
        self.paste_button = downloads.paste_button
        self.analyze_button = downloads.analyze_button
        self.source_details_host = downloads.source_details_host
        self.source_details_stack = downloads.source_details_stack
        self.source_details_empty = downloads.source_details_empty
        self.playlist_items_panel = downloads.playlist_items_panel
        self.playlist_items_edit = downloads.playlist_items_edit
        self.source_details_label = downloads.source_details_label
        self.output_section = downloads.output_section
        self.output_layout = downloads.output_layout
        self.format_card = downloads.format_card
        self.format_layout = downloads.format_layout
        self.mode_row_layout = downloads.mode_row_layout
        self.video_radio = downloads.video_radio
        self.audio_radio = downloads.audio_radio
        self.content_type_label = downloads.content_type_label
        self.content_type_row = downloads.content_type_row
        self.playlist_length_group = downloads.playlist_length_group
        self.playlist_length_edit = downloads.playlist_length_edit
        self.container_combo = downloads.container_combo
        self.convert_check = downloads.convert_check
        self.container_label = downloads.container_label
        self.post_process_label = downloads.post_process_label
        self.post_process_row = downloads.post_process_row
        self.codec_combo = downloads.codec_combo
        self.codec_label = downloads.codec_label
        self.format_combo = downloads.format_combo
        self.format_label = downloads.format_label
        self._output_form_labels = list(downloads.output_form_labels)
        self._output_form_rows = list(downloads.output_form_rows)
        self.format_row = downloads.format_row
        self.save_card = downloads.save_card
        self.save_layout = downloads.save_layout
        self.filename_edit = downloads.filename_edit
        self.file_name_label = downloads.file_name_label
        self.folder_row_layout = downloads.folder_row_layout
        self.output_dir_edit = downloads.output_dir_edit
        self.output_dir_label = downloads.output_dir_label
        self.advanced_toggle = downloads.advanced_toggle
        self.advanced_panel = downloads.advanced_panel
        self.advanced_summary = downloads.advanced_summary
        self.browse_button = downloads.browse_button
        self.output_folder_label = downloads.output_folder_label
        self.progress_bar = downloads.progress_bar
        self.metrics_card = downloads.metrics_card
        self.metrics_strip = downloads.metrics_strip
        self.progress_label = downloads.progress_label
        self.speed_label = downloads.speed_label
        self.eta_label = downloads.eta_label
        self.item_label = downloads.item_label

        run = downloads.run
        self.run_state_host = run.state_host
        self.run_activity_card = run.activity_card
        self.run_actions_card = run.actions_card
        self.run_actions_shell_layout = run.actions_shell_layout
        self.run_actions_layout = run.actions_layout
        self.status_value = run.status_value
        self.start_button = run.start_button
        self.add_queue_button = run.add_queue_button
        self.cancel_button = run.cancel_button

        self.playlist_items_edit.textChanged.connect(
            lambda _text: self._sync_playlist_length_from_items()
        )
        self.playlist_length_edit.textChanged.connect(self._on_playlist_length_changed)
        self.output_dir_edit.textChanged.connect(self._refresh_output_folder_display)
        self.filename_edit.textChanged.connect(self._refresh_advanced_summary)
        tab_order = (
            self.url_edit, self.paste_button, self.analyze_button,
            self.video_radio, self.audio_radio, self.format_combo,
            self.browse_button, self.advanced_toggle, self.container_combo,
            self.codec_combo, self.convert_check, self.filename_edit,
            self.start_button, self.add_queue_button, self.cancel_button,
        )
        for previous, following in zip(tab_order, tab_order[1:]):
            QWidget.setTabOrder(previous, following)

    def _set_advanced_expanded(self, expanded: bool) -> None:
        if self._advanced_anim is not None:
            self._advanced_anim.stop()
            self._advanced_anim.deleteLater()
            self._advanced_anim = None
        focused = self.focusWidget()
        if not expanded and focused is not None and self.advanced_panel.isAncestorOf(focused):
            self.advanced_toggle.setFocus()
        self.advanced_panel.set_focus_enabled(expanded)
        self.advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._sync_output_form_row_heights()
        target = 1.0 if expanded else 0.0
        start = self.advanced_panel.reveal_progress
        animate = (
            self.main_page.isVisible()
            and os.environ.get("YT_DLP_GUI_REDUCE_MOTION") != "1"
            and bool(self.style().styleHint(QStyle.StyleHint.SH_Widget_Animate, None, self))
        )
        if not animate or start == target:
            self._apply_advanced_reveal(target)
            return
        anim = QVariantAnimation(self)
        anim.setDuration(max(80, round(220 * abs(target - start))))
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(self._apply_advanced_reveal)
        anim.finished.connect(self._finish_advanced_animation)
        self._advanced_anim = anim
        anim.start()

    def _finish_advanced_animation(self) -> None:
        if self._advanced_anim is not None:
            self._advanced_anim.deleteLater()
            self._advanced_anim = None
        self._apply_advanced_reveal(1.0 if self.advanced_toggle.isChecked() else 0.0)

    def _apply_advanced_reveal(self, progress: float) -> None:
        self.advanced_panel.set_reveal_progress(
            progress, top_spacing=self.format_layout.spacing()
        )
        # Layout changes already invalidate the affected regions. Disabling and
        # re-enabling updates here schedules a full-page repaint on every frame.
        self.advanced_panel.parentWidget().layout().activate()
        self.format_layout.activate()
        self.output_layout.activate()

    def _refresh_advanced_summary(self) -> None:
        mode = self._current_mode()
        container = self._current_container()
        codec = self._current_codec()
        default_container = DEFAULT_AUDIO_CONTAINER if mode == "audio" else DEFAULT_VIDEO_CONTAINER
        custom = bool(
            (container and container != default_container)
            or (mode == "video" and codec and codec != DEFAULT_VIDEO_CODEC)
            or self.filename_edit.text().strip()
            or self.convert_check.isChecked()
        )
        details = []
        if custom:
            if container:
                details.append(container.upper())
            if mode == "video" and codec:
                details.append({"avc1": "H.264", "av01": "AV1"}.get(codec, codec))
            if self.convert_check.isChecked():
                details.append("Convert to MP4")
            if self.filename_edit.text().strip():
                details.append(f"Filename: {self.filename_edit.text().strip()}")
        summary = " | ".join(details)
        self.advanced_summary.setText(summary)
        self.advanced_summary.setToolTip(summary)
        self.advanced_summary.setVisible(bool(summary))

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
            scrollbar.sizeHint().width()
            if scroll_needed and scrollbar is not None
            else 0
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
            label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

    def _set_output_form_label_width(self, *, min_width: int = 96) -> None:
        for label in getattr(self, "_output_form_labels", []):
            self._unlock_widget_width(label)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _set_uniform_button_width(
        self,
        buttons: list[QPushButton],
        *,
        extra_px: int = 28,
        fixed: bool = False,
        sample_texts_by_button: dict[QPushButton, tuple[str, ...]] | None = None,
    ) -> None:
        live = [btn for btn in buttons if btn is not None]
        if not live:
            return
        width_samples = sample_texts_by_button or {}
        width = 0
        for button in live:
            samples = tuple(
                dict.fromkeys((button.text(), *width_samples.get(button, ())))
            )
            icon_width = 0
            if not button.icon().isNull():
                icon_size = button.iconSize()
                icon_width = max(icon_size.width(), icon_size.height()) + 8
            intrinsic_hint_width = self._button_intrinsic_size_hint_width(button)
            current_text_width = self._button_text_width(button, button.text())
            padding_width = max(
                extra_px,
                intrinsic_hint_width - current_text_width - icon_width,
            )
            text_width = max(self._button_text_width(button, text) for text in samples)
            width = max(
                width,
                intrinsic_hint_width,
                text_width + icon_width + padding_width,
            )
        for button in live:
            if isinstance(button, StableSizeHintButton):
                button.set_stable_width(width)
            if fixed:
                button.setFixedWidth(width)
            else:
                button.setMinimumWidth(width)

    def _button_intrinsic_size_hint_width(self, button: QPushButton) -> int:
        stable_width: int | None = None
        if isinstance(button, StableSizeHintButton):
            stable_width = button.stable_width()
            button.set_stable_width(None)
        button.ensurePolished()
        try:
            return max(button.minimumSizeHint().width(), button.sizeHint().width())
        finally:
            button.updateGeometry()
            if isinstance(button, StableSizeHintButton):
                button.set_stable_width(stable_width)

    def _button_text_width(self, button: QPushButton, text: str) -> int:
        metrics = button.fontMetrics()
        return max(
            metrics.horizontalAdvance(text),
            metrics.boundingRect(text).width(),
            metrics.tightBoundingRect(text).width(),
        )

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

    def _set_widget_width_bounds(
        self,
        widget: QWidget,
        *,
        minimum: int,
        maximum: int,
    ) -> None:
        min_width = max(0, int(minimum))
        max_width = max(min_width, int(maximum))
        widget.setMinimumWidth(min_width)
        widget.setMaximumWidth(max_width)

    def _set_widget_height_bounds(
        self,
        widget: QWidget,
        *,
        minimum: int,
        maximum: int,
    ) -> None:
        min_height = max(0, int(minimum))
        max_height = max(min_height, int(maximum))
        widget.setMinimumHeight(min_height)
        widget.setMaximumHeight(max_height)

    def _lock_widget_width(self, widget: QWidget, width: int) -> None:
        target = max(0, int(width))
        self._set_widget_width_bounds(widget, minimum=target, maximum=target)

    def _unlock_widget_width(self, widget: QWidget) -> None:
        self._set_widget_width_bounds(widget, minimum=0, maximum=16777215)

    def _set_widget_fixed_height(self, widget: QWidget, height: int) -> None:
        target = max(0, int(height))
        self._set_widget_height_bounds(widget, minimum=target, maximum=target)

    def _unlock_widget_height(self, widget: QWidget) -> None:
        self._set_widget_height_bounds(widget, minimum=0, maximum=16777215)


    def _responsive_layout_profile(self) -> _ResponsiveLayoutProfile:
        stacked = self.width() < 860
        return _ResponsiveLayoutProfile(
            output_mode="stacked" if stacked else "split",
            workspace_direction=QBoxLayout.Direction.TopToBottom if stacked else QBoxLayout.Direction.LeftToRight,
            compact_content=self.height() < ROOMY_CONTENT_LAYOUT_MIN_HEIGHT,
        )




    def _source_row_button_width_samples(self) -> dict[QPushButton, tuple[str, ...]]:
        return {
            self.analyze_button: (
                "Analyze URL",
                "Analyzing...",
                "Refresh formats",
            ),
        }

    def _run_action_button_width_samples(self) -> dict[QPushButton, tuple[str, ...]]:
        return {
            self.add_queue_button: (
                "Add to Queue",
                "Update Queue Item",
            ),
        }

    def _set_run_action_button_widths(self) -> None:
        samples_by_button = self._run_action_button_width_samples()
        for button in (self.add_queue_button, self.cancel_button, self.start_button):
            samples = samples_by_button.get(button, (button.text(),))
            # Use consistent padding for every label, including the queue-edit state.
            text_width = max(self._button_text_width(button, text) for text in samples)
            width = max(96, text_width + (26 if button.icon().isNull() else 52))
            if isinstance(button, StableSizeHintButton):
                button.set_stable_width(width)
            button.setFixedWidth(width)
        primary_width = max(140, self._button_text_width(self.start_button, "Download") + 52)
        if isinstance(self.start_button, StableSizeHintButton):
            self.start_button.set_stable_width(primary_width)
        self.start_button.setFixedWidth(primary_width)

    def _set_source_row_button_widths(self) -> None:
        samples = self._source_row_button_width_samples()
        for button in (self.paste_button, self.analyze_button):
            # Reserve the heaviest text state so primary/quiet transitions do
            # not shift the URL field or neighboring controls.
            font = QFont(button.font())
            font.setWeight(QFont.Weight.DemiBold)
            metrics = QFontMetrics(font)
            width = max(64, max(metrics.horizontalAdvance(text)
                               for text in samples.get(button, (button.text(),))) + (26 if button.icon().isNull() else 52))
            if isinstance(button, StableSizeHintButton):
                button.set_stable_width(width)
            button.setFixedWidth(width)


    def _normalize_control_sizing(self) -> None:
        height = max(qt_style.CONTROL_HEIGHT, self.fontMetrics().height() + 16)
        for control in (self.url_edit, self.playlist_items_edit, self.playlist_length_edit,
                        self.filename_edit, self.container_combo, self.codec_combo,
                        self.format_combo, self.edit_friendly_encoder_combo):
            target = max(height, control.fontMetrics().height() + 16)
            control.setMinimumHeight(target)
            control.setMaximumHeight(target)
        for button in self.findChildren(QPushButton):
            compact = bool(button.property("inlineControl"))
            target = (max(qt_style.INLINE_HEIGHT, button.fontMetrics().height() + 8)
                      if compact else max(height, button.fontMetrics().height() + 16))
            button.setMinimumHeight(target)
            button.setMaximumHeight(target)
        for button in (self.video_radio, self.audio_radio):
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setFixedHeight(max(height - 6, button.fontMetrics().height() + 8))
        mode_row = self.video_radio.parentWidget()
        mode_width = max(b.sizeHint().width() for b in (self.video_radio, self.audio_radio))
        for button in (self.video_radio, self.audio_radio):
            button.setFixedWidth(mode_width)
        mode_row.setFixedSize(mode_row.layout().sizeHint())
        self._unlock_widget_width(self.playlist_length_group)
        for button in (self.use_single_video_url_button, self.use_playlist_url_button):
            button.setMinimumWidth(button.fontMetrics().horizontalAdvance(button.text()) + 32)
        self.browse_button.setMinimumWidth(self.browse_button.sizeHint().width())
        self.settings_button.setMinimumWidth(0)
        self.settings_button.setMaximumWidth(16777215)
        for button in (self.downloads_button, self.queue_button, self.settings_button):
            button.setFixedWidth(qt_style.SIDEBAR_WIDTH - 24)
        url_height = max(qt_style.URL_CONTROL_HEIGHT, height,
                         *(c.fontMetrics().height() + 16 for c in
                           (self.url_edit, self.paste_button, self.analyze_button)))
        for control in (self.url_edit, self.paste_button, self.analyze_button):
            control.setFixedHeight(url_height)
        self.advanced_toggle.setMinimumHeight(qt_style.INLINE_HEIGHT)
        self._source_row_control_height = url_height
        self._lock_source_row_control_heights()
        self._set_source_row_button_widths()
        self._set_run_action_button_widths()
        self._set_output_form_label_width(min_width=112)
        self._normalize_input_widths()
        self._sync_output_form_row_heights(height)

    def _stabilize_source_preview_card_sizing(self) -> None:
        return

    def _prime_hidden_source_layout_geometry(self) -> None:
        return

    def _lock_source_row_control_heights(self) -> None:
        height = self._source_row_control_height
        if height:
            for widget in (self.url_edit, self.paste_button, self.analyze_button):
                widget.setFixedHeight(height)
            margins = self.source_row.layout().contentsMargins()
            self.source_row.setFixedHeight(height + margins.top() + margins.bottom() + 2)


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
            shell_extra_width += shell_layout.spacing() * max(
                0, shell_layout.count() - 1
            )
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
        for widget in (self.url_edit, self.playlist_items_edit, self.filename_edit,
                       self.container_combo, self.codec_combo, self.format_combo):
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)

    def _set_output_layout_mode(self, profile: _ResponsiveLayoutProfile) -> None:
        self._output_layout_mode = profile.output_mode
        self.workspace_layout.setDirection(profile.workspace_direction)
        self.workspace_layout.setSpacing(16)
        self.output_layout.setSpacing(24)
        self.format_layout.setSpacing(12)
        self.save_layout.setSpacing(12)
        self.format_layout.setContentsMargins(0, 0, 2, 0)
        self.save_layout.setContentsMargins(0, 0, 0, 0)
        self._set_output_form_label_width(min_width=112)
        self.mode_row_layout.setSpacing(8)
        self.folder_row_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.folder_row_layout.setSpacing(12)

    def _set_run_section_layout_mode(self, profile: _ResponsiveLayoutProfile) -> None:
        self.run_actions_shell_layout.setContentsMargins(0, 0, 0, 0)
        self.run_actions_layout.setHorizontalSpacing(12)
        self.run_actions_layout.removeWidget(self.cancel_button)
        self.run_actions_shell_layout.setSpacing(qt_style.SPACE_LG)
        self.run_actions_layout.removeWidget(self.start_button)
        self.run_actions_layout.removeWidget(self.add_queue_button)
        self.run_actions_layout.addWidget(self.add_queue_button, 0, 1)
        self.run_actions_layout.addWidget(self.start_button, 0, 2)
        for column in range(4):
            self.run_actions_layout.setColumnStretch(column, 1 if column == 0 else 0)
        self.metrics_card.layout().setContentsMargins(0, 12, 0, 0)
        self.metrics_card.layout().setSpacing(8)
        self.metrics_strip.layout().setSpacing(12)

    def _apply_responsive_layout(self) -> None:
        profile = self._responsive_layout_profile()
        self._set_output_layout_mode(profile)
        self._set_run_section_layout_mode(profile)
        self._sync_source_feedback_visibility()
        self.mixed_buttons_layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self._sync_source_details_height()

    def _install_tooltips(self) -> None:
        self.downloads_button.setToolTip("Open the downloads workspace.")
        self.settings_button.setToolTip("Open settings.")
        self.queue_button.setToolTip("Open the download queue window.")
        self.logs_button.setToolTip("Open logs view.")

        self.url_edit.setToolTip("Paste a video or playlist URL.")
        self.paste_button.setToolTip("Paste URL from clipboard.")
        self.analyze_button.setToolTip(
            "Load formats and preview details for the current URL."
        )
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
        self.playlist_length_edit.setToolTip(
            "Playlist items to download. Examples: 2-5, 7, 10-, or 1-5,7."
        )

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
            "Choose how edit-friendly MP4 re-encoding selects hardware. "
            "Automatic mode prefers the GPU detected on this computer, and "
            "falls back to CPU encoding when needed."
        )
        self.open_folder_after_download_check.setToolTip(
            "Open the selected output folder after downloads finish."
        )
        self.yt_dlp_update_button.setToolTip(
            "Check for and install the latest stable yt-dlp release."
        )
        self.export_diagnostics_button.setToolTip(
            "Export a diagnostics report to your output folder."
        )

        self.start_button.setToolTip(
            "Download the currently analyzed link."
        )
        self.add_queue_button.setToolTip("Add the current URL/settings to queue.")
        self.cancel_button.setToolTip("Cancel the current download.")
        self.status_value.setToolTip("Current run status.")

        self.queue_list.setToolTip(
            "Queued downloads. Drag to reorder and click the close icon to remove."
        )

        self.logs_view.setToolTip("Download logs.")
        self.logs_export_button.setToolTip("Export logs to your output folder.")
        self.logs_clear_button.setToolTip("Clear logs.")

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
        ):
            if widget is None or widget in staged_widgets:
                continue
            staged_widgets.append(widget)
            self._set_widget_property(widget, "stage", download_state)
        ready = has_formats_data and not is_fetching
        focused = self.focusWidget()
        if not ready and focused is not None and (
                self.format_card.isAncestorOf(focused) or self.run_actions_card.isAncestorOf(focused)):
            self.url_edit.setFocus()
        self.format_card.setVisible(ready)
        self.run_actions_card.setVisible(ready)
        self.media_summary.setVisible(ready and bool(self._preview_title_raw))
        self.source_hint.setVisible(not ready)
        self._set_widget_property(self.main_page, "presentation", download_state)

        source_state = "ready" if has_formats_data else "idle"
        if is_fetching:
            source_state = "loading"
        elif url_present and not has_formats_data:
            source_state = "primed"
        self._set_widget_property(self.analyze_button, "mode", source_state)
        self._set_widget_property(self.analyze_button, "uiRole", "secondary" if has_formats_data or is_fetching else "primary")
        if is_fetching:
            self.analyze_button.setText("Analyzing...")
        elif has_formats_data:
            self.analyze_button.setText("Refresh formats")
        else:
            self.analyze_button.setText("Analyze URL")
        self.analyze_button.setIcon(load_icon_asset(
            "refresh.svg" if has_formats_data or is_fetching else "analyze-action.svg", size=QSize(18, 18)))
        self._set_source_row_button_widths()
        self._lock_source_row_control_heights()
        self._set_source_row_button_widths()
        self._normalize_input_widths()

    def _refresh_queue_panel_state(self) -> None:
        count = len(self.queue_items)
        self.queue_button.setText(f"Queue ({count if count < 100 else '99+'})")
        self.queue_button.setAccessibleName(f"Queue, {count} items")
        has_items = bool(count)
        idle = not (self._is_downloading or self._is_fetching or self._tool_checks_pending
                    or self._yt_dlp_update_in_progress or getattr(self, "_app_data_cleanup_in_progress", False))
        editable = not (self.queue_active or self._is_downloading)
        self.queue_stack.setCurrentIndex(self._queue_content_index if has_items else self._queue_empty_index)
        self.queue_list.set_queue_editable(editable)
        self.queue_clear_button.setVisible(has_items)
        self.queue_clear_button.setEnabled(editable and has_items)
        self.queue_retry_button.setVisible(has_items)
        self.queue_retry_button.setEnabled(idle and any(i.get("status") == "failed" for i in self.queue_items))
        self.queue_start_button.setVisible(has_items)
        self.queue_start_button.setEnabled(idle and not self._pending_mixed_url
            and any(i.get("status") != "completed" for i in self.queue_items))
        self.queue_undo_row.setVisible(self._run_queue_state.cleared_queue is not None)
        self.queue_undo_button.setEnabled(idle)

    def _refresh_logs_panel_state(self) -> None:
        has_logs = bool(self._log_lines)
        self.logs_stack.setCurrentIndex(self._logs_content_index if has_logs else self._logs_empty_index)
        self.logs_export_button.setEnabled(has_logs)
        self.logs_clear_button.setEnabled(has_logs)

    def _set_source_feedback(
        self,
        text: str,
        *,
        tone: str = "neutral",
        title: str | None = None,
        action: str | None = None,
    ) -> None:
        tone_value = (
            tone
            if tone in {"neutral", "loading", "success", "warning", "error", "hidden"}
            else "neutral"
        )
        message = str(text or "").strip()
        self._status_presenter.last_source_feedback_log = self._last_source_feedback_log
        self._status_presenter.set_source_feedback(
            text, tone=tone_value, append_log=self._append_log,
        )
        self._last_source_feedback_log = self._status_presenter.last_source_feedback_log
        self._current_source_feedback_message = message
        self._current_source_feedback_tone = tone_value
        self._current_source_feedback_title = str(title or "").strip()
        self._feedback_dismissed = False
        self._feedback_action = action if action is not None else (
            "details" if tone_value in {"warning", "error"} else ""
        )
        self._feedback_output_dir = (
            self._post_download_output_dir if action == "folder" else None
        )
        self.feedback_message.setText(message)
        self.feedback_message.setToolTip(message)
        self._set_widget_property(self.feedback_row, "tone", tone_value)
        self._refresh_widget_style(self.feedback_message)
        self._sync_source_feedback_visibility()

    def _sync_source_feedback_visibility(self) -> None:
        fetching = self._is_fetching
        location = "global" if self._active_panel_name is not None else (
            "actions" if self._feedback_action == "queue" and not fetching else "source")
        if getattr(self, "_feedback_location", None) != location:
            current_parent = self.feedback_row.parentWidget()
            if current_parent is not None and current_parent.layout() is not None:
                current_parent.layout().removeWidget(self.feedback_row)
            if location == "global":
                self.feedback_row.setParent(self.content_column)
                self.content_column.layout().insertWidget(1, self.feedback_row)
            else:
                self.feedback_row.setParent(self.source_row.parentWidget())
                index = 2 if location == "source" else max(0, self.output_layout.count() - 1)
                self.output_layout.insertWidget(index, self.feedback_row)
            self._feedback_location = location
        self.analysis_progress_bar.setVisible(fetching)
        self.analysis_elapsed_label.setVisible(fetching)
        self.feedback_dismiss_button.setVisible(not fetching)
        self.feedback_action_button.setEnabled(not (fetching and self._source_state.cancel_requested))
        if fetching:
            self.feedback_action_button.setText("Cancel analysis")
            self.feedback_action_button.show()
            self._update_analysis_elapsed()
            if not self._analysis_timer.isActive():
                self._analysis_timer.start()
        else:
            self._analysis_timer.stop()
            self.feedback_action_button.setText(
                self._reveal_action_label() if self._feedback_action == "file" else
                "Open folder" if self._feedback_action == "folder" else "View queue" if self._feedback_action == "queue" else "View details"
            )
            self.feedback_action_button.setVisible(
                bool(self._feedback_action)
                and (self._feedback_action != "folder" or self._feedback_output_dir is not None)
            )
        visible = (
            bool(self._current_source_feedback_message)
            and self._current_source_feedback_tone in {"success", "warning", "error"}
            and not self._feedback_dismissed
            and self._current_source_feedback_message != "Formats ready."
            and self._active_panel_name != "logs"
            and not self._is_downloading
        )
        self.feedback_row.setVisible(fetching or visible)

    def _update_analysis_elapsed(self) -> None:
        started_at = self._source_state.started_at
        seconds = max(0, int(time.monotonic() - started_at)) if started_at is not None else 0
        self.analysis_elapsed_label.setText(f"Elapsed {seconds}s")

    def _dismiss_feedback(self) -> None:
        self._feedback_dismissed = True
        self._sync_source_feedback_visibility()

    def _activate_feedback_action(self) -> None:
        if self._is_fetching:
            self._source_controller.cancel_fetch_formats()
        elif self._feedback_action == "queue":
            self._open_panel("queue")
        elif self._feedback_action == "details":
            self._open_panel("logs")
        elif self._feedback_action == "file":
            self._reveal_download(self._run_queue_state.last_output_path)
        elif self._feedback_action == "folder" and self._feedback_output_dir is not None:
            folder = self._feedback_output_dir
            if folder.is_dir():
                self._effects.desktop.open_path(folder)
            else:
                self._set_source_feedback(
                    "Download folder is no longer available.", tone="error",
                )

    def _set_metrics_visible(self, visible: bool) -> None:
        self.metrics_card.setVisible(visible)
        self.progress_bar.setVisible(visible)
        self.metrics_strip.setVisible(visible)
        self.item_label.setVisible(visible)
        self._set_widget_property(self.metrics_card, "state", "active" if visible else "idle")
        self._sync_activity_metrics()

    def _sync_activity_metrics(self) -> None:
        for label in (self.progress_label, self.speed_label, self.eta_label):
            value = label.text().split(":", 1)[-1].strip()
            label.setVisible(bool(value and value != "-"))

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
        compact_row = getattr(self, "content_type_row", None)
        quality_row = getattr(self, "format_row", None)
        for row in getattr(self, "_output_form_rows", []):
            row.setMinimumHeight(0)
            # Font/style changes invalidate inner field hosts before their
            # containing rows. Measure from the leaves to avoid stale hints.
            for child in reversed(row.findChildren(QWidget)):
                child_layout = child.layout()
                if child_layout is not None:
                    child_layout.invalidate()
                    child_layout.activate()
            layout = row.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            if row is compact_row:
                target_height = max(
                    row.minimumSizeHint().height(), row.sizeHint().height()
                )
            else:
                target_height = max(control_height, row.minimumSizeHint().height(), row.sizeHint().height())
            if expand_visible_quality_row and row is quality_row:
                target_height = max(target_height, row.sizeHint().height())
            row.setMinimumHeight(target_height)
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
        self.advanced_panel.sync_content_geometry()

    def _sync_output_card_heights(self) -> None:
        # Forms use their natural height and scroll; never force nested sections
        # to equal heights or grow the top-level window.
        for card in (self.format_card, self.save_card):
            card.setMinimumHeight(0)
            card.setMaximumHeight(16777215)

    def _sync_run_section_split_widths(self) -> None:
        self._unlock_widget_width(self.run_actions_card)


    def _sync_output_stack_widths(self) -> None:
        self._unlock_widget_width(self.format_card)
        self._unlock_widget_width(self.metrics_card)

    def _refresh_downloads_page_geometry(self) -> None:
        self.advanced_panel.set_reveal_progress(
            self.advanced_panel.reveal_progress, top_spacing=self.format_layout.spacing()
        )
        self.workspace_layout.activate()
        self.output_layout.activate()
        self._sync_output_stack_widths()
        refreshed_widgets: list[QWidget] = []
        for widget in (
            self.format_card,
            self.metrics_card,
            self.save_card,
            self.output_section,
            self.main_page,
        ):
            if widget is None or widget in refreshed_widgets:
                continue
            refreshed_widgets.append(widget)
            widget.updateGeometry()
            layout = widget.layout()
            if layout is not None:
                layout.activate()
        main_layout = self.main_page.layout()
        self._sync_output_card_heights()
        self._sync_run_section_split_widths()
        if main_layout is not None:
            main_layout.activate()
        self._sync_current_panel_geometry()

    def _queue_deferred_resize_sync(self) -> None:
        if not self._resize_sync_timer.isActive():
            self._resize_sync_timer.start(0)

    def _run_deferred_resize_sync(self) -> None:
        key = (
            self._responsive_layout_profile(), self.font().toString(),
            self.logicalDpiX(), self.logicalDpiY(), self.devicePixelRatioF(),
        )
        if key != self._resize_profile_key:
            self._normalize_control_sizing()
            self._apply_responsive_layout()
            self._resize_profile_key = key
        else:
            self._normalize_input_widths()
        self._refresh_downloads_page_geometry()
        self._layout_mixed_url_overlay()
        self._refresh_current_item_text()

    def _sync_current_panel_geometry(self) -> None:
        current = self.panel_stack.currentWidget()
        if current is None:
            return
        current.setGeometry(self.panel_stack.contentsRect())
        layout = current.layout()
        if layout is not None:
            layout.activate()

    def _refresh_ready_summary(self) -> None:
        self._ready_summary_full_text = ""
        self._refresh_queue_preview_card()

    def _refresh_ready_summary_text(self, full_text: str | None = None) -> None:
        if full_text is not None:
            self._ready_summary_full_text = str(full_text or "")
        return

    def _panel_checked(self, name: str) -> bool:
        if self._active_panel_name is None:
            return name == "downloads"
        if name == "settings":
            return self._active_panel_name in {"settings", "logs"}
        return self._active_panel_name == name

    def _apply_panel_selection(self, active_panel: str | None) -> None:
        self._active_panel_name = active_panel
        for panel_name, button in self._panel_buttons.items():
            button.setChecked(self._panel_checked(panel_name))
        self._refresh_top_action_icons()

    def _set_main_workspace_selection(self) -> None:
        self._apply_panel_selection(None)

    def _show_main_workspace(self) -> None:
        window_size = self.size()
        if self.panel_stack.currentIndex() != self._main_page_index:
            self.panel_stack.setCurrentIndex(self._main_page_index)
            self._sync_current_panel_geometry()
        self._set_main_workspace_selection()
        self._sync_source_feedback_visibility()
        self._set_mixed_url_alert_visible(bool(self._pending_mixed_url))
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _apply_header_layout(self) -> None:
        self.classic_actions.setVisible(True)
        self.downloads_button.setVisible(True)
        self.queue_button.setVisible(True)
        self._refresh_top_action_icons()

    def _toggle_panel(self, name: str) -> None:
        if self._active_panel_name == name:
            self._apply_panel_selection(name)
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
        icon = load_icon_asset(
            filename,
            size=QSize(TOP_ACTION_ICON_PX, TOP_ACTION_ICON_PX),
        )
        if icon.isNull():
            return self._legacy_log_alert_icon
        return icon

    def _apply_window_icon(self) -> None:
        path = asset_path(APP_ICON_FILENAME)
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
        self._refresh_downloads_page_geometry()
        self._apply_window_icon()
        QTimer.singleShot(0, self._start_tool_checks)

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
        shortcuts = "\n".join(APP_SHORTCUT_LINES)
        self._effects.dialogs.information(
            self,
            f"About {APP_DISPLAY_NAME}",
            (
                f"{APP_DISPLAY_NAME}\n"
                f"Version {APP_VERSION}\n\n"
                f"{APP_DESCRIPTION}\n\n"
                f"{APP_PRIVACY_NOTE}\n\n"
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
            ("settings", self.settings_button),
            ("queue", self.queue_button),
            ("logs", self.logs_button),
        ):
            is_checked = self._panel_checked(name) or (name == "settings" and self._active_panel_name == "logs")
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

        for button in (self.downloads_button, self.queue_button, self.settings_button):
            button.setFixedWidth(qt_style.SIDEBAR_WIDTH - 24)

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
            "logs": {
                "normal": self._load_asset_icon("logs.svg"),
                "active": self._load_asset_icon("logs-active.svg"),
                "alert": self._load_asset_icon("logs-alert.svg"),
            },
        }
        self._refresh_top_action_icons()
        for button, icon in ((self.start_button, "download-action.svg"),
                             (self.queue_start_button, "play-action.svg"),
                             (self.analyze_button, "analyze-action.svg"),
                             (self.add_queue_button, "add.svg")):
            button.setIcon(load_icon_asset(icon, size=QSize(18, 18)))
            button.setIconSize(QSize(18, 18))

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

    def _open_panel(self, name: str) -> None:
        window_size = self.size()
        index = self._panel_name_to_index.get(name)
        if index is None:
            return
        if name == "settings":
            self._sync_yt_dlp_update_button()
        self.panel_stack.setCurrentIndex(index)
        self._sync_current_panel_geometry()
        if name == "logs" and self._logs_alert_active:
            self._logs_alert_active = False
        self._apply_panel_selection(name)
        if name == "logs":
            self._flush_log_updates()
        self._sync_source_feedback_visibility()
        self._set_mixed_url_alert_visible(False)
        if self.isVisible() and self.size() != window_size:
            self.resize(window_size)

    def _close_panel(self) -> None:
        if (
            self._active_panel_name is None
            and self.panel_stack.currentIndex() == self._main_page_index
        ):
            self._set_main_workspace_selection()
            self._set_mixed_url_alert_visible(bool(self._pending_mixed_url))
            return
        window_size = self.size()
        self.panel_stack.setCurrentIndex(self._main_page_index)
        self._sync_current_panel_geometry()
        self._set_main_workspace_selection()
        self._sync_source_feedback_visibility()
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


    def _set_playlist_items_visible(self, visible: bool) -> None:
        if bool(visible):
            self.source_details_label.setText("Playlist items")
            self.source_details_stack.setCurrentIndex(SOURCE_DETAILS_PLAYLIST_INDEX)
        else:
            self.source_details_label.setText("")
            if (
                self.source_details_stack.currentIndex()
                == SOURCE_DETAILS_PLAYLIST_INDEX
            ):
                self.source_details_stack.setCurrentIndex(SOURCE_DETAILS_NONE_INDEX)
        self._sync_source_details_height()

    def _set_playlist_length_visible(self, visible: bool) -> None:
        self.playlist_length_group.setVisible(bool(visible))
        self._sync_output_form_row_heights()

    def _sync_playlist_length_from_items(self) -> None:
        next_value = self.playlist_items_edit.text().strip()
        if self.playlist_length_edit.text() == next_value:
            return
        previously_blocked = self.playlist_length_edit.blockSignals(True)
        self.playlist_length_edit.setText(next_value)
        self.playlist_length_edit.blockSignals(previously_blocked)

    def _on_playlist_length_changed(self, text: str) -> None:
        clean_text = str(text or "").strip()
        if self.playlist_items_edit.text().strip() == clean_text:
            return
        self.playlist_items_edit.setText(clean_text)

    def _sync_source_details_height(self) -> None:
        current = self.source_details_stack.currentWidget()
        if current is None:
            self._set_widget_fixed_height(self.source_details_host, 0)
            self._set_widget_fixed_height(self.source_details_stack, 0)
            return
        if self.source_details_stack.currentIndex() == SOURCE_DETAILS_NONE_INDEX:
            target = 0
        else:
            target = max(
                0, current.sizeHint().height(), current.minimumSizeHint().height()
            )
        self._set_widget_fixed_height(self.source_details_host, target)
        self._set_widget_fixed_height(self.source_details_stack, target)

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
        playlist_controls_visible = bool(self._playlist_mode) and (not prompt_visible)
        self._set_mixed_url_alert_visible(prompt_visible)
        self._set_playlist_items_visible(playlist_controls_visible)
        self._set_playlist_length_visible(playlist_controls_visible)
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

    def _editing_queue_index(self) -> int | None:
        return self._run_queue_state.editing_queue_index

    def _refresh_queue_edit_action(self) -> None:
        editing = self._editing_queue_index() is not None
        playlist_selected = self._playlist_mode or core_urls.is_playlist_url(
            self.url_edit.text().strip()
        )
        button_text = "Update Queue Item" if editing else "Add to Queue"
        if editing:
            tooltip = "Save changes back to the selected queue item."
        elif playlist_selected:
            tooltip = (
                "This URL is being treated as a playlist, so it cannot be added "
                "to the queue."
            )
        else:
            tooltip = "Add the current URL/settings to queue."
        if self.add_queue_button.text() != button_text:
            self.add_queue_button.setText(button_text)
            self._set_run_action_button_widths()
            self._sync_run_section_split_widths()
        self.add_queue_button.setToolTip(tooltip)

    def _clear_queue_item_edit_mode(self) -> None:
        self._run_queue_state.editing_queue_index = None
        self._pending_queue_edit_settings = None
        self._refresh_queue_edit_action()
        self._sync_run_section_split_widths()

    def _set_combo_current_data(self, combo: QComboBox, value: str) -> None:
        target = str(value or "").strip()
        if not target:
            if combo.count() > 0:
                combo.setCurrentIndex(0)
            return
        idx = combo.findData(target)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_combo_current_text(self, combo: QComboBox, value: str) -> None:
        target = str(value or "").strip()
        if not target:
            return
        idx = combo.findText(target)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _apply_queue_edit_settings_to_form(
        self,
        settings: QueueSettings,
        *,
        apply_format_label: bool,
    ) -> None:
        self._set_output_dir_text(
            str(settings.get("output_dir") or self._default_output_dir())
        )
        self.playlist_items_edit.setText(str(settings.get("playlist_items") or ""))
        self.filename_edit.setText(str(settings.get("custom_filename") or ""))
        encoder_value = str(settings.get("edit_friendly_encoder") or "auto")
        encoder_index = self.edit_friendly_encoder_combo.findData(encoder_value)
        if encoder_index < 0:
            encoder_index = self.edit_friendly_encoder_combo.findData("auto")
        if encoder_index >= 0:
            self.edit_friendly_encoder_combo.setCurrentIndex(encoder_index)

        mode = str(settings.get("mode") or "").strip().lower()
        self._set_mode_unselected()
        if mode == "audio":
            self.audio_radio.setChecked(True)
        elif mode == "video":
            self.video_radio.setChecked(True)

        self._set_combo_current_data(
            self.container_combo,
            str(settings.get("format_filter") or "").strip().lower(),
        )
        self._set_combo_current_data(
            self.codec_combo,
            str(settings.get("codec_filter") or "").strip().lower(),
        )
        if apply_format_label:
            self._set_combo_current_text(
                self.format_combo,
                str(settings.get("format_label") or "").strip(),
            )
            self._pending_queue_edit_settings = None
        else:
            self._pending_queue_edit_settings = dict(settings)

    def _apply_pending_queue_edit_settings(self) -> None:
        settings = self._pending_queue_edit_settings
        if not isinstance(settings, dict):
            return
        self._set_combo_current_text(
            self.format_combo,
            str(settings.get("format_label") or "").strip(),
        )
        self._pending_queue_edit_settings = None

    def _edit_queue_item(self, row: int, item: QueueItem) -> None:
        url = core_urls.strip_url_whitespace(str(item.get("url") or ""))
        settings = dict(item.get("settings") or {})
        same_url_loaded = (
            url
            and core_urls.strip_url_whitespace(self.url_edit.text()) == url
            and bool(self._video_labels or self._audio_labels)
            and not self._is_fetching
        )

        self._show_main_workspace()
        if core_urls.strip_url_whitespace(self.url_edit.text()) != url:
            self.url_edit.setText(url)
        elif not same_url_loaded:
            self._on_url_changed()

        self._apply_queue_edit_settings_to_form(
            settings,
            apply_format_label=same_url_loaded,
        )
        self._refresh_queue_edit_action()
        self._set_status(
            f"Editing queue item {int(row) + 1}. Update settings and click Update Queue Item."
        )
        self._set_source_feedback(
            "Queue item loaded into the main form. Update the settings, then save the changes back to the queue.",
            tone="neutral",
            title="Editing queue item",
        )
        self._sync_run_section_split_widths()
        if not same_url_loaded and url:
            self._start_fetch_formats()

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
        was_blocked = combo.blockSignals(True)
        combo.clear()
        for label, value in items:
            combo.addItem(label, value)
        if keep_current and current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(was_blocked)

    def _on_mode_change(self) -> None:
        mode = self._current_mode()
        with QSignalBlocker(self.container_combo), QSignalBlocker(self.codec_combo):
            if mode == "audio":
                items = [
                    ("Select container", ""),
                    *[(c.upper(), c) for c in AUDIO_CONTAINERS],
                ]
                self._set_combo_items(self.container_combo, items)
                if not self._current_container():
                    self._set_combo_current_data(self.container_combo, DEFAULT_AUDIO_CONTAINER)
                self.codec_combo.setCurrentIndex(0)
            elif mode == "video":
                items = [
                    ("Select container", ""),
                    *[(c.upper(), c) for c in VIDEO_CONTAINERS],
                ]
                self._set_combo_items(self.container_combo, items)
                if not self._current_container():
                    self._set_combo_current_data(self.container_combo, DEFAULT_VIDEO_CONTAINER)
                if not self._current_codec():
                    self._set_combo_current_data(self.codec_combo, DEFAULT_VIDEO_CODEC)
            else:
                self._set_combo_items(
                    self.container_combo, [("Select container", "")], keep_current=False
                )
                self.codec_combo.setCurrentIndex(0)
        self._apply_mode_formats()
        self._update_controls_state()

    def _apply_output_defaults(self) -> None:
        if not self._current_mode():
            if self._video_labels:
                self.video_radio.setChecked(True)
            elif self._audio_labels:
                self.audio_radio.setChecked(True)

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
        if mode == "audio":
            self.format_combo.addItem("Auto")
            self.format_combo.setCurrentIndex(0)
        else:
            for label in self._filtered_labels:
                self.format_combo.addItem(label)
            if current and current in self._filtered_labels:
                self.format_combo.setCurrentText(current)
            elif self._filtered_labels:
                self.format_combo.setCurrentIndex(0)
        self.format_combo.blockSignals(False)
        self._sync_format_combo_visibility()

    def _selected_format_label(self) -> str:
        label = self.format_combo.currentText().strip()
        if label and not (self._current_mode() == "audio" and label == "Auto"):
            return label
        if self._current_mode() != "audio":
            return ""
        if format_pipeline.BEST_AUDIO_LABEL in self._filtered_lookup:
            return format_pipeline.BEST_AUDIO_LABEL
        if self._filtered_labels:
            return str(self._filtered_labels[0] or "").strip()
        if format_pipeline.BEST_AUDIO_LABEL in self._audio_lookup:
            return format_pipeline.BEST_AUDIO_LABEL
        if self._audio_labels:
            return str(self._audio_labels[0] or "").strip()
        return format_pipeline.BEST_AUDIO_LABEL

    def _sync_format_combo_visibility(self) -> None:
        has_quality_options = self.format_combo.count() > 0
        has_formats_data = bool(self._video_labels or self._audio_labels)
        mode = self._current_mode()
        if has_quality_options:
            placeholder_text = "Choose exact format/quality."
        elif has_formats_data:
            placeholder_text = "No exact matches for this filter."
        else:
            placeholder_text = "Analyze a URL to load quality."
        self.format_combo.setPlaceholderText(placeholder_text)

        if mode == "audio":
            codec_label_text = "Codec"
            codec_tooltip = "No codec selection is needed for audio-only downloads."
            format_label_text = "Quality"
            format_tooltip = (
                "Best audio is selected automatically for audio-only downloads."
            )
            format_visible = True
            codec_prompt_text = "Auto"
        else:
            codec_label_text = "Codec"
            codec_tooltip = "Choose preferred video codec."
            format_label_text = "Quality"
            format_tooltip = "Choose exact format/quality."
            format_visible = True
            codec_prompt_text = "Select codec"

        visibility_changed = self.format_combo.isVisible() != format_visible
        label_changed = (
            self.codec_label.text() != codec_label_text
            or self.format_label.text() != format_label_text
        )
        if (
            self.codec_combo.count() > 0
            and self.codec_combo.itemText(0) != codec_prompt_text
        ):
            self.codec_combo.setItemText(0, codec_prompt_text)
        self.format_combo.setVisible(format_visible)
        self.codec_label.setText(codec_label_text)
        self.codec_combo.setToolTip(codec_tooltip)
        self.format_label.setText(format_label_text)
        self.format_combo.setToolTip(format_tooltip)
        if visibility_changed or label_changed:
            self._sync_output_form_row_heights(
                expand_visible_quality_row=format_visible
            )
            self._refresh_downloads_page_geometry()

    def _selected_format_info(self) -> dict | None:
        label = self._selected_format_label()
        if not label:
            return (
                dict(format_pipeline.BEST_AUDIO_INFO)
                if self._current_mode() == "audio"
                else None
            )
        info = self._filtered_lookup.get(label)
        if info is not None:
            return info
        if self._current_mode() == "audio":
            return self._audio_lookup.get(label) or dict(
                format_pipeline.BEST_AUDIO_INFO
            )
        return None

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
    ) -> None:
        self._run_queue_controller.run_single_download_worker(
            request=request,
        )

    def _on_download_done(self, result: str) -> None:
        self._flush_progress_updates()
        self._run_queue_controller.on_download_done(result)
        self._flush_log_updates()

    def _maybe_close_after_cancel(self) -> None:
        if self._is_downloading or not self._close_after_cancel:
            return
        self._close_after_cancel = False
        QTimer.singleShot(0, self.close)

    def _on_cancel(self) -> None:
        self._discard_pending_progress()
        self._run_queue_controller.on_cancel()

    def _on_add_to_queue(self) -> None:
        self._run_queue_controller.on_add_to_queue()

    def _start_queue_download(self) -> None:
        self._run_queue_controller.start_queue_download()

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
        self._flush_progress_updates()
        self._run_queue_controller.on_queue_item_done(had_error, cancelled)
        self._flush_log_updates()

    def _finish_queue(self, *, cancelled: bool = False) -> None:
        self._run_queue_controller.finish_queue(cancelled=cancelled)

    def _queue_edit_row(self, row: int) -> None:
        self._run_queue_controller.on_queue_edit_item(int(row))

    def _queue_remove_row(self, row: int) -> None:
        self._run_queue_controller.on_queue_remove_selected([int(row)])

    def _queue_reorder_items(self, item_order: list[int]) -> None:
        self._run_queue_controller.on_queue_reorder([int(row) for row in item_order])

    def _sync_queue_workspace_view(self) -> None:
        return

    def _list_scroll_value(self, list_widget: QListView) -> int:
        scrollbar = list_widget.verticalScrollBar()
        return int(scrollbar.value()) if scrollbar is not None else 0

    def _restore_list_scroll_value(
        self,
        list_widget: QListView,
        value: int,
    ) -> None:
        scrollbar = list_widget.verticalScrollBar()
        if scrollbar is None:
            return
        clamped = max(
            int(scrollbar.minimum()),
            min(int(value), int(scrollbar.maximum())),
        )
        scrollbar.setValue(clamped)

    def _refresh_queue_panel(self) -> None:
        queue_list_scroll = self._list_scroll_value(self.queue_list)
        with QSignalBlocker(self.queue_list):
            while self.queue_list.count() > len(self.queue_items):
                self.queue_list.takeItem(self.queue_list.count() - 1)
            while self.queue_list.count() < len(self.queue_items):
                self.queue_list.addItem(QListWidgetItem())
            for row in range(len(self.queue_items)):
                self._update_queue_row(row)
            editing_index = self._editing_queue_index()
            if editing_index is not None and 0 <= editing_index < self.queue_list.count():
                self.queue_list.setCurrentRow(int(editing_index))
        self._refresh_queue_panel_state()
        self._restore_list_scroll_value(self.queue_list, queue_list_scroll)

    def _update_queue_row(self, row: int) -> None:
        if not 0 <= row < len(self.queue_items):
            return
        list_item = self.queue_list.item(row)
        if list_item is None:
            return
        context = queue_presentation.QueueSummaryContext(
            current_url=self.url_edit.text(),
            current_preview_title=self._preview_title_raw,
            current_item_title=self._current_item_title_tooltip,
        )
        entry = queue_presentation.build_queue_list_entry(
            self.queue_items[row], idx=row + 1,
            active=self.queue_active and self.queue_index == row, context=context,
        )
        if list_item.text() != entry.title:
            list_item.setText(entry.title)
        for role, value in (
            (QUEUE_COMPLETED_ROLE, self.queue_items[row].get("status") == "completed" and bool(self.queue_items[row].get("output_path"))),
            (QUEUE_STATUS_ROLE, "downloading" if self.queue_active and self.queue_index == row else self.queue_items[row].get("status", "queued")),
            (QUEUE_SOURCE_INDEX_ROLE, row),
            (QUEUE_TITLE_ROLE, entry.title),
            (QUEUE_META_ROLE, entry.meta),
        ):
            if list_item.data(role) != value:
                list_item.setData(role, value)
        if list_item.toolTip() != entry.tooltip:
            list_item.setToolTip(entry.tooltip)

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
            queue_ready=any(item.get("status") != "completed" for item in self.queue_items),
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
        self.cancel_button.setVisible(self._is_downloading)
        self.metrics_card.setVisible(self._is_downloading)
        if self._tool_checks_pending:
            self.analyze_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.edit_friendly_encoder_combo.setEnabled(False)
        if self._yt_dlp_update_in_progress:
            for control in (
                self.analyze_button,
                self.start_button,
                self.add_queue_button,
                self.url_edit,
            ):
                control.setEnabled(False)
        self._refresh_queue_edit_action()
        self._sync_format_combo_visibility()
        self._refresh_download_sections_state(
            url_present=url_present,
            has_formats_data=has_formats_data,
            is_fetching=self._is_fetching,
        )
        if hasattr(self, "yt_dlp_update_button"):
            self._sync_yt_dlp_update_button()
        self.remove_app_data_button.setEnabled(self._app_data_cleanup_allowed())
        self._refresh_queue_panel_state()

        self._refresh_ready_summary()
        self._refresh_advanced_summary()
        self._sync_source_feedback_visibility()
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
        self._queue_deferred_resize_sync()

    def closeEvent(self, event: QCloseEvent) -> None:
        if getattr(self, "_app_data_cleanup_in_progress", False):
            event.ignore()
            return
        self._save_user_settings()
        if self._tool_checks_pending and self._tool_checks_started:
            self._close_after_tool_checks = True
            event.ignore()
            return
        self._tool_checks_pending = False
        if self._yt_dlp_update_in_progress:
            self._effects.dialogs.information(
                self,
                "yt-dlp update in progress",
                "Wait for the yt-dlp update to finish before closing the app.",
            )
            event.ignore()
            return
        if self._source_state.pending_fetches:
            self._source_state.close_after_fetch = True
            self._source_controller.cancel_fetch_formats()
            event.ignore()
            return
        self._analysis_timer.stop()
        if not self._is_downloading:
            self._source_controller.clear_metadata_cache()
            self._discard_pending_progress()
            self._log_update_timer.stop()
            event.accept()
            return
        if self._cancel_requested:
            force_quit = self._effects.dialogs.question(
                self,
                "Cancellation in progress",
                ("A download is still shutting down.\n\n" "Force close now?"),
                default_yes=False,
            )
            if force_quit:
                self._source_controller.clear_metadata_cache()
                self._discard_pending_progress()
                self._log_update_timer.stop()
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

    window = QtYtDlpGui()
    # Let normal window shutdown cancel and reap any analysis worker.
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, lambda _sig, _frame: window.close())
        sigint_pump = QTimer()
        sigint_pump.setInterval(100)
        sigint_pump.timeout.connect(lambda: None)
        sigint_pump.start()

    setattr(window, "_sigint_pump", sigint_pump)
    window.show()
    window._apply_window_icon()
    if owns_app:
        return int(app.exec())
    return 0
