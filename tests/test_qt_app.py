import os
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent, QPoint, QRect, Qt
    from PySide6.QtGui import QCloseEvent, QFontMetrics, QHelpEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QBoxLayout,
        QCheckBox,
        QComboBox,
        QFrame,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QStyle,
        QStyleFactory,
        QWidget,
    )

    from gui.common import download
    from gui.app_meta import (
        APP_DESCRIPTION,
        APP_DISPLAY_NAME,
        APP_PRIVACY_NOTE,
        APP_SHORTCUT_LINES,
        APP_VERSION,
    )
    from gui.core import urls as core_urls
    from gui.qt.app import (
        SOURCE_DETAILS_NONE_INDEX,
        SOURCE_DETAILS_PLAYLIST_INDEX,
        QtYtDlpGui,
        _TooltipBlocker,
        _TooltipDelayProxyStyle,
        _disable_tooltips,
        _apply_tooltip_delay_style,
    )
    from gui.qt.constants import (
        MIN_WINDOW_HEIGHT,
        MIN_WINDOW_WIDTH,
        ROOMY_CONTENT_LAYOUT_MIN_HEIGHT,
        TOOLTIP_WAKE_UP_DELAY_MS,
    )
    from gui.qt import style as qt_style
    from gui.qt.widgets import QUEUE_META_ROLE, QUEUE_TITLE_ROLE

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is required for Qt app tests")
class TestQtApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._load_settings_patch = patch(
            "gui.qt.app.settings_store.load_settings",
            return_value={
                "output_dir": str(Path.home() / "Downloads"),
                "edit_friendly_encoder": "auto",
                "open_folder_after_download": False,
            },
        )
        self._resolve_ffmpeg_patch = patch(
            "gui.qt.window_settings.tooling.resolve_binary",
            return_value=(Path("/usr/local/bin/ffmpeg"), "system"),
        )
        self._available_encoders_patch = patch(
            "gui.qt.window_settings.tooling.available_ffmpeg_encoders",
            return_value={"h264_nvenc", "libx264"},
        )
        self._load_settings_patch.start()
        self._resolve_ffmpeg_patch.start()
        self._available_ffmpeg_encoders = self._available_encoders_patch.start()
        self.window = QtYtDlpGui()

    def tearDown(self) -> None:
        self.window._is_downloading = False
        self.window._close_after_cancel = False
        self.window.close()
        self.window.deleteLater()
        self._load_settings_patch.stop()
        self._resolve_ffmpeg_patch.stop()
        self._available_encoders_patch.stop()

    def _assert_visible_text_widgets_fit(
        self,
        root: QWidget,
        *,
        label: str,
    ) -> None:
        scan_types = (QLabel, QPushButton, QCheckBox, QRadioButton, QComboBox, QLineEdit)
        scanned = 0
        for widget_type in scan_types:
            for widget in root.findChildren(widget_type):
                if not widget.isVisible() or not widget.isVisibleTo(root):
                    continue
                if widget.geometry().isEmpty():
                    continue
                scanned += 1
                with self.subTest(surface=label, widget=widget.objectName() or type(widget).__name__):
                    self.assertGreaterEqual(
                        widget.geometry().height(),
                        widget.minimumSizeHint().height(),
                        f"{label}: {widget.objectName() or type(widget).__name__} is vertically clipped",
                    )
                    if isinstance(widget, (QPushButton, QCheckBox, QRadioButton)):
                        self.assertGreaterEqual(
                            widget.geometry().width(),
                            widget.minimumSizeHint().width(),
                            f"{label}: {widget.objectName() or widget.text()} is horizontally clipped",
                        )
        self.assertGreater(scanned, 0, f"No visible text widgets were scanned for {label}")

    def _assert_url_input_visible_in_source_row(self, *, mode: str) -> None:
        self.window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.window.show()
        QApplication.processEvents()
        QTest.qWait(0)

        self.assertTrue(self.window.url_edit.isVisible(), f"{mode}: url input should be visible")
        self.assertIs(self.window.url_edit.parentWidget(), self.window.source_row)
        self.assertEqual(self.window.source_row.layout().indexOf(self.window.url_edit), 0)

    def _load_ready_preview_with_formats(self, *, queue_ready: bool = False) -> str:
        url = "https://www.youtube.com/watch?v=abc123"
        self.window.url_edit.setText(url)
        self.window.video_radio.setChecked(True)
        self.window._active_fetch_request_id = 15
        self.window._is_fetching = True
        payload = {
            "collections": {
                "video_labels": ["1080p mp4 (avc1)"],
                "video_lookup": {
                    "1080p mp4 (avc1)": {
                        "format_id": "137",
                        "ext": "mp4",
                        "vcodec": "avc1.640028",
                        "acodec": "none",
                    }
                },
                "audio_labels": ["Best audio only"],
                "audio_lookup": {
                    "Best audio only": {
                        "custom_format": "bestaudio/best",
                        "is_audio_only": True,
                        "acodec": "opus",
                    }
                },
                "audio_languages": [],
            },
            "preview_title": "Sample",
            "source_summary": {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "Example Channel",
                "detail_one_text": "Formats ready",
                "detail_two_text": "5m 42s",
                "detail_three_text": "1 video format",
            },
        }
        self.window._on_formats_loaded(
            request_id=15,
            url=url,
            payload=payload,
            error=False,
            is_playlist=False,
        )
        if queue_ready:
            self.window.queue_items = [
                {
                    "url": url,
                    "settings": {
                        "mode": "video",
                        "format_filter": "mp4",
                        "codec_filter": "avc1",
                        "format_label": "1080p mp4 (avc1)",
                    },
                }
            ]
            self.window._refresh_queue_panel()
        QApplication.processEvents()
        return url

    def test_mixed_url_helpers(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.assertTrue(core_urls.is_mixed_url(mixed))
        self.assertEqual(
            core_urls.strip_list_param(mixed),
            "https://www.youtube.com/watch?v=abc123",
        )
        self.assertEqual(
            core_urls.to_playlist_url(mixed),
            "https://www.youtube.com/playlist?list=PLXYZ",
        )

    def test_initial_window_size_matches_minimum(self) -> None:
        self.assertEqual(self.window.width(), MIN_WINDOW_WIDTH)
        self.assertEqual(self.window.height(), MIN_WINDOW_HEIGHT)
        self.assertEqual(self.window.minimumWidth(), MIN_WINDOW_WIDTH)
        self.assertEqual(self.window.minimumHeight(), MIN_WINDOW_HEIGHT)

    def test_tooltip_delay_proxy_style_overrides_wake_up_hint(self) -> None:
        app_style = QApplication.instance().style()
        self.assertIsNotNone(app_style)
        base_style = QStyleFactory.create("Fusion")
        if base_style is None and app_style is not None:
            base_style = QStyleFactory.create(app_style.objectName())
        self.assertIsNotNone(base_style)
        assert base_style is not None
        delayed = _TooltipDelayProxyStyle(base_style, wake_up_delay_ms=1250)
        delayed.setParent(self.window)
        self.assertEqual(
            delayed.styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay),
            1250,
        )

    def test_apply_tooltip_delay_style_uses_configured_wake_up_delay(self) -> None:
        app = QApplication.instance()
        self.assertIsNotNone(app)
        assert app is not None

        current_style = app.style()
        base_style = QStyleFactory.create("Fusion")
        if base_style is None and current_style is not None:
            base_style = QStyleFactory.create(current_style.objectName())
        self.assertIsNotNone(base_style)
        assert base_style is not None

        app.setStyle(base_style)
        _apply_tooltip_delay_style(app)

        delayed_style = app.style()
        self.assertIsInstance(delayed_style, _TooltipDelayProxyStyle)
        self.assertEqual(
            delayed_style.styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay),
            TOOLTIP_WAKE_UP_DELAY_MS,
        )

    def test_disable_tooltips_installs_blocker_and_filters_tooltip_events(self) -> None:
        app = QApplication.instance()
        self.assertIsNotNone(app)
        assert app is not None

        _disable_tooltips(app)
        blocker = app.findChild(_TooltipBlocker, "_tooltipBlocker")
        self.assertIsNotNone(blocker)

        tooltip_event = QHelpEvent(
            QEvent.Type.ToolTip,
            QPoint(4, 4),
            self.window.analyze_button.mapToGlobal(QPoint(4, 4)),
        )
        self.window.analyze_button.setToolTip("Analyze")

        with patch("gui.qt.app.QToolTip.hideText") as hide_text_mock:
            QApplication.sendEvent(self.window.analyze_button, tooltip_event)

        hide_text_mock.assert_called_once_with()

    def test_source_defaults_hide_playlist_items_and_prompt(self) -> None:
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_NONE_INDEX,
        )
        self.assertEqual(self.window.source_details_host.height(), 0)
        self.assertTrue(self.window.mixed_url_overlay.isHidden())

    def test_app_title_and_primary_analyze_action_defaults(self) -> None:
        self.assertEqual(self.window.windowTitle(), APP_DISPLAY_NAME)
        self.assertFalse(self.window.windowIcon().isNull())
        self.assertIsNone(self.window.findChild(QLabel, "titleLabel"))
        self.assertEqual(self.window.analyze_button.text(), "Analyze URL")
        self.assertFalse(self.window.analyze_button.isEnabled())
        self.assertEqual(
            self.window._current_source_feedback_message,
            "Paste a video or playlist URL to load available formats.",
        )

    def test_title_shells_use_rounded_containers(self) -> None:
        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QWidget#topBarShell\s*\{[^}]*border:\s*none;[^}]*border-radius:\s*0px;",
        )
        self.assertRegex(
            stylesheet,
            r"QFrame#panelCard\s*\{[^}]*border-radius:\s*24px;",
        )

    def test_panel_stack_paints_opaque_background_behind_transparent_pages(self) -> None:
        self.assertEqual(self.window.panel_stack.objectName(), "panelStack")

        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QStackedWidget#panelStack\s*\{[^}]*background:\s*#[0-9a-fA-F]{6};[^}]*border:\s*none;",
        )

    def test_output_section_shell_is_transparent_in_all_stages(self) -> None:
        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QWidget#outputSection\s*\{[^}]*background:\s*transparent;[^}]*border:\s*none;[^}]*border-radius:\s*0px;",
        )
        self.assertRegex(
            stylesheet,
            r'QWidget#outputSection\[stage="staged"\]\s*\{[^}]*background:\s*transparent;[^}]*border:\s*none;',
        )
        self.assertRegex(
            stylesheet,
            r'QWidget#outputSection\[stage="loading"\]\s*\{[^}]*background:\s*transparent;[^}]*border:\s*none;',
        )

    def test_output_section_has_no_outer_shell_padding(self) -> None:
        margins = self.window.output_section.layout().contentsMargins()
        self.assertEqual(margins.left(), 0)
        self.assertEqual(margins.top(), 0)
        self.assertEqual(margins.right(), 0)
        self.assertEqual(margins.bottom(), 0)

    def test_output_form_rows_keep_uniform_vertical_spacing(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for height in (MIN_WINDOW_HEIGHT, ROOMY_CONTENT_LAYOUT_MIN_HEIGHT):
            with self.subTest(height=height):
                self.window.resize(MIN_WINDOW_WIDTH, height)
                QApplication.processEvents()

                self.assertEqual(
                    self.window.save_layout.spacing(),
                    self.window.format_layout.spacing(),
                )
                margins = self.window.save_layout.contentsMargins()
                self.assertEqual(margins.left(), 0)
                self.assertEqual(margins.top(), 0)
                self.assertEqual(margins.right(), 0)
                self.assertEqual(margins.bottom(), 0)

                save_index = self.window.format_layout.indexOf(self.window.save_card)
                self.assertGreater(save_index, 0)
                self.assertIs(
                    self.window.format_layout.itemAt(save_index - 1).widget(),
                    self.window.format_row,
                )

    def test_output_bars_keep_uniform_vertical_gaps(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        for height in (MIN_WINDOW_HEIGHT, ROOMY_CONTENT_LAYOUT_MIN_HEIGHT):
            with self.subTest(height=height):
                self.window.resize(MIN_WINDOW_WIDTH, height)
                QApplication.processEvents()

                bars = (
                    self.window.video_radio.parentWidget(),
                    self.window.container_combo,
                    self.window.codec_combo,
                    self.window.format_combo,
                    self.window.filename_edit,
                    self.window.output_dir_edit,
                )
                positions = []
                for widget in bars:
                    self.assertIsNotNone(widget)
                    assert widget is not None
                    top = widget.mapTo(
                        self.window.format_card,
                        widget.rect().topLeft(),
                    ).y()
                    positions.append((top, widget.height()))

                gaps = [
                    next_top - (top + height_px)
                    for (top, height_px), (next_top, _next_height) in zip(
                        positions,
                        positions[1:],
                    )
                ]
                self.assertTrue(gaps)
                self.assertLessEqual(max(gaps) - min(gaps), 1)

    def test_url_input_is_visible_in_source_row(self) -> None:
        self.window.show()
        QApplication.processEvents()
        QTest.qWait(0)

        self.assertFalse(self.window.url_edit.hasFrame())
        self.assertTrue(self.window.url_edit.isVisible())
        self.assertIs(self.window.url_edit.parentWidget(), self.window.source_row)
        self.assertEqual(self.window.source_row.layout().indexOf(self.window.url_edit), 0)
        self.assertEqual(self.window.url_edit.textMargins().left(), 0)

        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QWidget#commandBar QFrame#urlInputShell\s*\{[^}]*background:\s*transparent;[^}]*border:\s*none;[^}]*border-radius:\s*0px;",
        )
        self.assertRegex(
            stylesheet,
            r"QWidget#commandBar QLineEdit#urlInputField\s*\{[^}]*background:\s*#[0-9a-fA-F]{6};[^}]*border:\s*1px solid #[0-9a-fA-F]{6};",
        )
        self.assertRegex(
            stylesheet,
            r"QWidget#commandBar QLineEdit#urlInputField:hover,\s*QWidget#commandBar QLineEdit#urlInputField:focus\s*\{[^}]*border:\s*1px solid #[0-9a-fA-F]{6};",
        )

    def test_source_row_contains_url_input_and_buttons(self) -> None:
        self.window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.window.show()
        QApplication.processEvents()
        QTest.qWait(0)

        self.assertIsNone(self.window.source_row.findChild(QWidget, "urlInputShell"))
        self.assertEqual(self.window.source_row.layout().count(), 3)
        self.assertIs(self.window.source_row.layout().itemAt(0).widget(), self.window.url_edit)
        self.assertIs(self.window.source_row.layout().itemAt(1).widget(), self.window.paste_button)
        self.assertIs(self.window.source_row.layout().itemAt(2).widget(), self.window.analyze_button)

    def test_url_input_is_visible_at_idle(self) -> None:
        self._assert_url_input_visible_in_source_row(mode="idle")

    def test_url_input_stays_visible_when_focused(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setFocus()
        QApplication.processEvents()
        QTest.qWait(0)
        self._assert_url_input_visible_in_source_row(mode="focused")

    def test_stylesheet_gives_fields_inset_surfaces_and_combo_arrows(self) -> None:
        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QLineEdit\s*\{[^}]*qlineargradient",
        )
        self.assertRegex(
            stylesheet,
            r"QComboBox\s*\{[^}]*qlineargradient",
        )
        self.assertRegex(
            stylesheet,
            r'QComboBox::down-arrow\s*\{[^}]*image:\s*url\("/tmp/combo-down-arrow\.svg"\);',
        )
        self.assertRegex(
            stylesheet,
            r"QComboBox::drop-down\s*\{[^}]*width:\s*32px;",
        )

    def test_downloads_state_host_replaces_legacy_source_workspace_shell(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertIsNone(
            self.window.main_page.findChild(QWidget, "legacySourceStateHost")
        )
        self.assertIsNone(self.window.main_page.findChild(QWidget, "sourceSection"))
        self.assertIsNone(self.window.main_page.findChild(QWidget, "sourceViewStack"))
        self.assertIsNone(self.window.main_page.findChild(QWidget, "workspaceTabBar"))

        state_host = self.window.main_page.findChild(QWidget, "downloadsStateHost")
        self.assertIsNotNone(state_host)
        assert state_host is not None
        self.assertFalse(state_host.isVisible())
        self.assertEqual(state_host.width(), 0)
        self.assertEqual(state_host.height(), 0)
        self.assertLess(state_host.geometry().right(), 0)

    def test_queue_empty_state_defaults_to_centered_placeholder(self) -> None:
        self.assertEqual(self.window.queue_stack.currentIndex(), self.window._queue_empty_index)
        self.assertEqual(self.window.queue_empty_state.placeholder_title.text(), "Queue is empty")
        self.assertEqual(
            self.window.queue_empty_state.placeholder_description.text(),
            "Paste a URL above to get started",
        )
        self.assertEqual(
            len(self.window.queue_empty_state.findChildren(QPushButton, "historyAgainButton")),
            0,
        )

    def test_source_row_buttons_are_not_vertically_clipped(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for button in (
            self.window.paste_button,
            self.window.analyze_button,
        ):
            self.assertGreaterEqual(
                button.geometry().height(),
                button.minimumSizeHint().height(),
                f"{button.objectName() or button.text()} is vertically clipped",
            )

    def test_source_row_action_buttons_share_the_same_intrinsic_height(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertEqual(
            self.window.paste_button.minimumSizeHint().height(),
            self.window.analyze_button.minimumSizeHint().height(),
        )

    def test_source_row_keeps_paste_action_narrower_than_analyze(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertLess(
            self.window.paste_button.width(),
            self.window.analyze_button.width(),
        )

    def test_visible_text_widgets_fit_across_download_views_and_overlay(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self._assert_visible_text_widgets_fit(
            self.window.main_page,
            label="downloads summary",
        )
        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.main_page,
            label="downloads preview with feedback",
        )

        self.window._set_preview_title(
            "How did they fit an entire PC in this?? - HP @ CES 2026"
        )
        self.window._set_source_summary(
            {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "ShortCircuit",
                "detail_one_text": "Formats ready",
                "detail_two_text": "5m 32s",
                "detail_three_text": "13 video formats",
            }
        )
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.main_page,
            label="downloads preview with metadata",
        )

        self.window._pending_mixed_url = (
            "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        )
        self.window._update_source_details_visibility()
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.mixed_url_overlay,
            label="mixed url overlay",
        )

    def test_visible_text_widgets_fit_across_secondary_panels(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window._open_panel("settings")
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.panel_stack.currentWidget(),
            label="settings panel",
        )

        self.window._open_panel("queue")
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.panel_stack.currentWidget(),
            label="queue panel empty state",
        )

        self.window.downloads_button.click()
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.run_actions_card,
            label="run actions card",
        )

        self.window._open_panel("logs")
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.panel_stack.currentWidget(),
            label="logs panel default state",
        )

        self.window._append_log("[error] something happened")
        QApplication.processEvents()
        self._assert_visible_text_widgets_fit(
            self.window.panel_stack.currentWidget(),
            label="logs panel filled state",
        )

    def test_switching_modes_does_not_refresh_preview_for_empty_intermediate_state(
        self,
    ) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p"]
        self.window._audio_labels = ["128k"]
        self.window._update_controls_state()
        QApplication.processEvents()

        self.window.video_radio.click()
        QApplication.processEvents()

        refresh_modes: list[str] = []
        original_refresh = self.window._refresh_queue_preview_card

        def wrapped_refresh() -> None:
            refresh_modes.append(self.window._current_mode())
            original_refresh()

        self.window._refresh_queue_preview_card = wrapped_refresh
        try:
            self.window.audio_radio.click()
            QApplication.processEvents()
        finally:
            self.window._refresh_queue_preview_card = original_refresh

        self.assertEqual(refresh_modes, ["audio"])

    def test_switching_modes_avoids_full_geometry_refresh_when_preview_layout_is_stable(
        self,
    ) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p"]
        self.window._audio_labels = ["128k"]
        self.window._update_controls_state()
        QApplication.processEvents()

        self.window.video_radio.click()
        QApplication.processEvents()

        geometry_refreshes = 0
        original_refresh = self.window._refresh_downloads_page_geometry

        def wrapped_refresh() -> None:
            nonlocal geometry_refreshes
            geometry_refreshes += 1
            original_refresh()

        self.window._refresh_downloads_page_geometry = wrapped_refresh
        try:
            self.window.audio_radio.click()
            QApplication.processEvents()
        finally:
            self.window._refresh_downloads_page_geometry = original_refresh

        self.assertEqual(geometry_refreshes, 0)

    def test_switching_modes_with_loaded_preview_avoid_full_geometry_refresh(
        self,
    ) -> None:
        self.window.show()
        QApplication.processEvents()
        self._load_ready_preview_with_formats(queue_ready=True)

        with patch.object(
            self.window,
            "_refresh_downloads_page_geometry",
            wraps=self.window._refresh_downloads_page_geometry,
        ) as geometry_refresh_mock:
            self.window.audio_radio.click()
            QApplication.processEvents()
            self.window.video_radio.click()
            QApplication.processEvents()

        self.assertEqual(geometry_refresh_mock.call_count, 0)


    def test_workspace_defaults_keep_downloads_tab_active(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertTrue(self.window.downloads_button.isChecked())
        self.assertTrue(self.window.downloads_button.isVisible())
        self.assertTrue(self.window.queue_button.isVisible())
        self.assertFalse(self.window.queue_button.isChecked())
        self.assertIsNone(self.window.main_page.findChild(QWidget, "sourceViewStack"))
        self.assertIsNone(self.window.main_page.findChild(QWidget, "workspaceTabBar"))
        self.assertNotIn(
            "Session",
            [
                button.text()
                for button in self.window.classic_actions.findChildren(QPushButton)
            ],
        )

    def test_top_nav_selection_animates_between_downloads_and_queue_tabs(self) -> None:
        self.window.show()
        QApplication.processEvents()

        selection = self.window.classic_actions.findChild(QWidget, "topNavSelection")
        self.assertIsNotNone(selection)
        assert selection is not None
        self.assertTrue(selection.isVisible())

        start_x = selection.geometry().center().x()
        downloads_x = self.window.downloads_button.geometry().center().x()
        target_x = self.window.queue_button.geometry().center().x()
        self.assertLess(abs(start_x - downloads_x), 4)
        self.assertLess(start_x, target_x)

        self.window.queue_button.click()
        QTest.qWait(80)
        QApplication.processEvents()

        mid_x = selection.geometry().center().x()
        self.assertGreater(mid_x, start_x)
        self.assertLess(mid_x, target_x)

        QTest.qWait(260)
        QApplication.processEvents()

        final_x = selection.geometry().center().x()
        self.assertLess(abs(final_x - target_x), 4)
        self.assertTrue(self.window.queue_button.isChecked())

    def test_top_panel_switch_keeps_source_header_geometry_stable(self) -> None:
        self.window.show()
        self.window.resize(900, 760)
        QApplication.processEvents()

        downloads_tab_rect = self.window.downloads_button.geometry()
        queue_tab_rect = self.window.queue_button.geometry()
        source_width = self.window.source_row.parentWidget().width()

        self.window.queue_button.click()
        QApplication.processEvents()

        self.assertEqual(self.window.downloads_button.geometry(), downloads_tab_rect)
        self.assertEqual(self.window.queue_button.geometry(), queue_tab_rect)
        self.assertEqual(self.window.source_row.parentWidget().width(), source_width)
        self.assertEqual(self.window._active_panel_name, "queue")
        self.assertEqual(
            self.window.panel_stack.currentIndex(),
            self.window._panel_name_to_index["queue"],
        )
        self.assertTrue(self.window.queue_button.isChecked())

        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(
            self.window.panel_stack.currentIndex(),
            self.window._main_page_index,
        )
        self.assertTrue(self.window.downloads_button.isChecked())

    def test_convert_check_stays_hidden_for_video_containers(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p"]
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window._update_controls_state()

        mp4_index = self.window.container_combo.findData("mp4")
        webm_index = self.window.container_combo.findData("webm")
        self.assertGreaterEqual(mp4_index, 0)
        self.assertGreaterEqual(webm_index, 0)

        self.window.container_combo.setCurrentIndex(mp4_index)
        self.window._update_controls_state()
        QApplication.processEvents()
        self.assertFalse(self.window.convert_check.isVisible())
        self.assertFalse(self.window.post_process_row.isVisible())

        self.window.container_combo.setCurrentIndex(webm_index)
        self.window._update_controls_state()
        QApplication.processEvents()
        self.assertFalse(self.window.convert_check.isVisible())
        self.assertFalse(self.window.post_process_row.isVisible())

    def test_url_entry_enables_analyze_action_without_auto_fetching(self) -> None:
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")

        self.assertTrue(self.window.analyze_button.isEnabled())
        self.assertEqual(self.window.analyze_button.text(), "Analyze URL")
        self.assertFalse(self.window._fetch_timer.isActive())
        self.assertIn("Analyze URL", self.window._current_source_feedback_message)

    def test_url_entry_does_not_resize_source_row_controls(self) -> None:
        self.window.show()
        QApplication.processEvents()

        source_row = self.window.main_page.findChild(QWidget, "commandBar")
        self.assertIsNotNone(source_row)
        assert source_row is not None
        before = {
            "url": self.window.url_edit.height(),
            "paste": self.window.paste_button.height(),
            "analyze": self.window.analyze_button.height(),
            "row": source_row.height(),
        }

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        QApplication.processEvents()

        self.assertEqual(self.window.url_edit.height(), before["url"])
        self.assertEqual(self.window.paste_button.height(), before["paste"])
        self.assertEqual(self.window.analyze_button.height(), before["analyze"])
        self.assertEqual(source_row.height(), before["row"])

    def test_source_row_buttons_remain_visible_at_min_width(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.window.url_edit.setText(
            "https://www.youtube.com/watch?v="
            "abc1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
        QApplication.processEvents()

        source_rect = self.window.source_row.rect().adjusted(0, 0, -1, -1)
        mapped: list[tuple[QPushButton, QRect]] = []
        for button in (self.window.paste_button, self.window.analyze_button):
            top_left = button.mapTo(self.window.source_row, button.rect().topLeft())
            bottom_right = button.mapTo(
                self.window.source_row, button.rect().bottomRight()
            )
            rect = QRect(top_left, bottom_right).normalized()
            mapped.append((button, rect))
            self.assertTrue(
                source_rect.contains(rect),
                f"{button.text()} is clipped inside the source row",
            )

        overlap = mapped[0][1].intersected(mapped[1][1])
        self.assertFalse(
            overlap.width() > 2 and overlap.height() > 2,
            "Source row action buttons overlap at the minimum window width",
        )

    def test_source_row_controls_keep_visible_gap_at_min_width(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.window.url_edit.setText(
            "https://www.youtube.com/watch?v="
            "abc1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
        QApplication.processEvents()

        def left_edge_in_row(widget: QWidget) -> int:
            return widget.mapTo(self.window.source_row, widget.rect().topLeft()).x()

        def right_edge_in_row(widget: QWidget) -> int:
            return widget.mapTo(self.window.source_row, widget.rect().topRight()).x()

        self.assertGreaterEqual(
            left_edge_in_row(self.window.paste_button)
            - right_edge_in_row(self.window.url_edit),
            6,
        )
        self.assertGreaterEqual(
            left_edge_in_row(self.window.analyze_button)
            - right_edge_in_row(self.window.paste_button),
            6,
        )

    def test_refresh_state_keeps_source_row_controls_separated_at_min_width(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        self.window.url_edit.setText(
            "https://www.youtube.com/watch?v="
            "abc1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )
        self.window._video_labels = ["1080p mp4 (avc1)"]
        self.window._update_controls_state()
        QApplication.processEvents()

        self.assertEqual(self.window.analyze_button.text(), "Refresh formats")

        source_rect = self.window.source_row.rect().adjusted(0, 0, -1, -1)
        self.assertTrue(self.window.url_edit.isVisible())
        mapped: list[tuple[str, QRect]] = []
        for name, widget in (
            ("paste", self.window.paste_button),
            ("analyze", self.window.analyze_button),
        ):
            top_left = widget.mapTo(self.window.source_row, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.source_row, widget.rect().bottomRight()
            )
            rect = QRect(top_left, bottom_right).normalized()
            mapped.append((name, rect))
            self.assertTrue(
                source_rect.contains(rect),
                f"{name} control is clipped inside the source row",
            )

        for (left_name, left_rect), (right_name, right_rect) in zip(mapped, mapped[1:]):
            overlap = left_rect.intersected(right_rect)
            self.assertFalse(
                overlap.width() > 2 and overlap.height() > 2,
                f"{left_name} and {right_name} overlap in refresh state",
            )

    def test_shortening_url_keeps_download_cards_full_width(self) -> None:
        self.window.show()
        QApplication.processEvents()

        widths = [
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/",
            "https://",
            "h",
            "",
        ]
        base_output_width = self.window.output_section.width()
        for url in widths:
            self.window.url_edit.setText(url)
            QApplication.processEvents()
            panel_width = self.window.panel_stack.width()
            self.assertEqual(self.window.main_page.width(), panel_width)
            self.assertEqual(self.window.output_section.width(), base_output_width)
            self.assertLessEqual(self.window.output_section.width(), panel_width)

    def test_geometry_refresh_does_not_shrink_header_or_main_page(self) -> None:
        self.window.show()
        QApplication.processEvents()

        header = self.window.top_actions.parentWidget()
        self.assertIsNotNone(header)
        assert header is not None
        before_header_width = header.width()
        before_main_page_width = self.window.main_page.width()

        self.window._set_preview_title(
            "How did they fit an entire PC in this?? - HP @ CES 2026"
        )
        self.window._set_source_summary(
            {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "ShortCircuit",
                "detail_one_text": "Formats ready",
                "detail_two_text": "5m 32s",
                "detail_three_text": "13 video formats",
            }
        )
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window._refresh_ready_summary()
        QApplication.processEvents()

        self.assertEqual(header.width(), before_header_width)
        self.assertEqual(self.window.main_page.width(), before_main_page_width)
        self.assertEqual(self.window.main_page.width(), self.window.panel_stack.width())

    def test_loaded_formats_shift_analyze_button_into_refresh_state(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p"]
        self.window._update_controls_state()
        QApplication.processEvents()

        self.assertEqual(self.window.analyze_button.text(), "Refresh formats")
        self.assertGreaterEqual(
            self.window.analyze_button.width(),
            self.window.analyze_button.sizeHint().width(),
        )
        self.assertGreaterEqual(
            self.window.analyze_button.height(),
            self.window.analyze_button.sizeHint().height(),
        )

    def test_analyze_button_width_stays_stable_across_source_states(self) -> None:
        self.window.show()
        self.window.resize(1180, 820)
        QApplication.processEvents()

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._update_controls_state()
        QApplication.processEvents()

        baseline_width = self.window.analyze_button.width()
        baseline_left = self.window.analyze_button.mapTo(
            self.window.source_row,
            self.window.analyze_button.rect().topLeft(),
        ).x()
        baseline_url_width = self.window.url_edit.width()

        self.window._video_labels = ["1080p"]
        self.window._update_controls_state()
        QApplication.processEvents()

        self.assertEqual(self.window.analyze_button.text(), "Refresh formats")
        self.assertEqual(self.window.analyze_button.width(), baseline_width)
        self.assertEqual(
            self.window.analyze_button.mapTo(
                self.window.source_row,
                self.window.analyze_button.rect().topLeft(),
            ).x(),
            baseline_left,
        )
        self.assertEqual(self.window.url_edit.width(), baseline_url_width)

        self.window._is_fetching = True
        self.window._update_controls_state()
        QApplication.processEvents()

        self.assertEqual(self.window.analyze_button.text(), "Analyzing...")
        self.assertEqual(self.window.analyze_button.width(), baseline_width)
        self.assertEqual(
            self.window.analyze_button.mapTo(
                self.window.source_row,
                self.window.analyze_button.rect().topLeft(),
            ).x(),
            baseline_left,
        )
        self.assertEqual(self.window.url_edit.width(), baseline_url_width)

    def test_secondary_panels_start_with_empty_states(self) -> None:
        self.assertEqual(self.window.queue_stack.currentIndex(), self.window._queue_empty_index)

        self.window._clear_logs()

        self.assertEqual(
            self.window.logs_stack.currentIndex(),
            self.window._logs_content_index,
        )
        self.assertEqual(self.window.logs_view.toPlainText(), "")
        self.assertFalse(self.window.logs_clear_button.isEnabled())

    def test_source_feedback_routes_messages_to_logs(self) -> None:
        self.window._clear_logs()

        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )
        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )

        source_logs = [line for line in self.window._log_lines if line.startswith("[source]")]
        self.assertEqual(
            source_logs,
            [
                "[source][success] Formats are ready. Choose options and start the download."
            ],
        )

    def test_hidden_source_feedback_resets_dedupe_state(self) -> None:
        self.window._clear_logs()

        message = "URL captured. Loading available formats..."
        self.window._set_source_feedback(message, tone="loading")
        self.window._set_source_feedback("", tone="hidden")
        self.window._set_source_feedback(message, tone="loading")

        source_logs = [
            line for line in self.window._log_lines if line.startswith("[source][loading]")
        ]
        self.assertEqual(
            source_logs,
            [f"[source][loading] {message}", f"[source][loading] {message}"],
        )

    def test_source_feedback_visibility_tracks_current_tone(self) -> None:
        self.window.show()
        QApplication.processEvents()

        loading_message = "Loading available formats..."
        self.window._set_source_feedback(
            loading_message,
            tone="loading",
        )
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()
        self.assertTrue(self.window.source_feedback_toast.isVisible())
        self.assertEqual(self.window.source_feedback_toast_message.text(), loading_message)
        self.assertEqual(self.window.source_feedback_toast_title.text(), "Loading formats")
        self.assertEqual(len(self.window._visible_source_feedback_toasts()), 1)

        message = "Formats are ready. Choose options and start the download."
        self.window._set_source_feedback(
            message,
            tone="success",
        )
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()
        self.assertTrue(self.window.source_feedback_toast.isVisible())
        self.assertEqual(self.window.source_feedback_toast_message.text(), message)
        self.assertEqual(self.window.source_feedback_toast_title.text(), "Formats ready")
        self.assertEqual(
            [toast.title_label.text() for toast in self.window._visible_source_feedback_toasts()],
            ["Formats ready", "Loading formats"],
        )

        self.window._set_source_feedback(
            "URL ready. Click Analyze URL to load formats and preview details.",
            tone="neutral",
        )
        QApplication.processEvents()
        self.assertFalse(self.window.source_feedback_toast.isVisible())
        self.assertEqual(len(self.window._visible_source_feedback_toasts()), 0)

        self.window._set_source_feedback("", tone="hidden")
        self.window._apply_responsive_layout()
        QApplication.processEvents()
        self.assertFalse(self.window.source_feedback_toast.isVisible())

    def test_source_feedback_toasts_stack_newest_first(self) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        loading_message = "Loading available formats..."
        ready_message = "Formats are ready. Choose options and start the download."
        self.window._set_source_feedback(loading_message, tone="loading")
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()

        self.window._set_source_feedback(ready_message, tone="success")
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()

        toasts = self.window._visible_source_feedback_toasts()
        self.assertEqual(len(toasts), 2)
        self.assertEqual(
            [toast.title_label.text() for toast in toasts],
            ["Formats ready", "Loading formats"],
        )
        self.assertEqual(
            [toast.message_label.text() for toast in toasts],
            [ready_message, loading_message],
        )
        self.assertLess(toasts[0].card.geometry().top(), toasts[1].card.geometry().top())

    def test_source_feedback_loading_uses_toast_on_narrow_layouts(self) -> None:
        self.window.show()
        self.window.resize(900, 800)
        QApplication.processEvents()

        message = "Loading available formats..."
        self.window._set_source_feedback(message, tone="loading")
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()

        self.assertTrue(self.window.source_feedback_toast.isVisible())
        self.assertEqual(self.window.source_feedback_toast_message.text(), message)
        self.assertEqual(self.window.source_feedback_toast_title.text(), "Loading formats")

    def test_source_feedback_success_toast_stays_top_right_above_tab_bar_without_shifting_content(
        self,
    ) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        before_row_y = self.window.source_row.geometry().y()
        root = self.window.centralWidget()
        self.assertIsNotNone(root)
        assert root is not None
        root_rect = root.rect()
        panel_rect = self.window.panel_stack.geometry()

        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )
        QApplication.processEvents()
        QTest.qWait(350)
        QApplication.processEvents()
        target_rect = self.window._source_feedback_toast_target_rect()
        toast_rect = self.window.source_feedback_toast.geometry()

        self.assertEqual(self.window.source_row.geometry().y(), before_row_y)
        self.assertTrue(self.window.source_feedback_toast.isVisible())
        self.assertEqual(toast_rect, target_rect)
        self.assertTrue(root_rect.contains(toast_rect))
        self.assertGreater(toast_rect.left(), panel_rect.center().x())
        self.assertLess(toast_rect.top(), panel_rect.top())

    def test_source_feedback_success_toast_auto_hides_after_timeout(self) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        with patch.object(self.window, "_source_feedback_toast_timeout_ms", return_value=40):
            self.window._set_source_feedback(
                "Formats are ready. Choose options and start the download.",
                tone="success",
            )
            QApplication.processEvents()
            self.assertTrue(self.window.source_feedback_toast.isVisible())

            QTest.qWait(700)
            QApplication.processEvents()

        self.assertFalse(self.window.source_feedback_toast.isVisible())

    def test_source_feedback_success_toast_can_be_dismissed_manually(self) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        with patch.object(self.window, "_source_feedback_toast_timeout_ms", return_value=0):
            self.window._set_source_feedback(
                "Formats are ready. Choose options and start the download.",
                tone="success",
            )
            QApplication.processEvents()
            QTest.qWait(350)
            QApplication.processEvents()

            self.assertTrue(self.window.source_feedback_toast.isVisible())
            self.assertTrue(self.window.source_feedback_toast_dismiss_button.isVisible())

            QTest.mouseClick(
                self.window.source_feedback_toast_dismiss_button,
                Qt.MouseButton.LeftButton,
            )
            QApplication.processEvents()
            QTest.qWait(300)
            QApplication.processEvents()
            self.window._apply_responsive_layout()
            QApplication.processEvents()

        self.assertFalse(self.window.source_feedback_toast.isVisible())

    def test_source_feedback_uses_custom_toast_title_when_provided(self) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        with patch.object(self.window, "_source_feedback_toast_timeout_ms", return_value=0):
            self.window._set_source_feedback(
                "Saved as queue item 2. Queue now has 2 items. Open Queue to review, or press Download to start it.",
                tone="success",
                title="Added to queue",
            )
            QApplication.processEvents()
            QTest.qWait(350)
            QApplication.processEvents()

        self.assertTrue(self.window.source_feedback_toast.isVisible())
        self.assertEqual(self.window.source_feedback_toast_title.text(), "Added to queue")
        self.assertEqual(
            self.window.source_feedback_toast_message.text(),
            "Saved as queue item 2. Queue now has 2 items. Open Queue to review, or press Download to start it.",
        )

    def test_about_dialog_uses_app_metadata(self) -> None:
        with patch.object(self.window._effects.dialogs, "information") as info_mock:
            self.window._show_about_dialog()

        info_mock.assert_called_once()
        _parent, title, message = info_mock.call_args.args
        self.assertIn(APP_DISPLAY_NAME, title)
        self.assertIn(APP_DISPLAY_NAME, message)
        self.assertIn(APP_VERSION, message)
        self.assertIn(APP_DESCRIPTION, message)
        self.assertIn(APP_PRIVACY_NOTE, message)
        self.assertIn(APP_SHORTCUT_LINES[0], message)

    def test_load_settings_applies_saved_output_folder(self) -> None:
        with patch(
            "gui.qt.app.settings_store.load_settings",
            return_value={
                "output_dir": "/tmp/custom",
                "open_folder_after_download": False,
            },
        ):
            window = QtYtDlpGui()
        try:
            self.assertEqual(window.output_dir_edit.text().strip(), "/tmp/custom")
        finally:
            window.close()
            window.deleteLater()

    def test_load_settings_applies_edit_friendly_encoder_preference(self) -> None:
        with patch(
            "gui.qt.app.settings_store.load_settings",
            return_value={
                "output_dir": "/tmp/custom",
                "edit_friendly_encoder": "nvidia",
                "open_folder_after_download": False,
            },
        ):
            window = QtYtDlpGui()
        try:
            self.assertEqual(window.edit_friendly_encoder_combo.currentData(), "nvidia")
        finally:
            window.close()
            window.deleteLater()

    def test_open_folder_after_download_prefers_post_download_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            target = Path(output_dir) / "video.mp4"
            target.write_text("x", encoding="utf-8")
            self.window.open_folder_after_download_check.setChecked(True)
            self.window._set_output_dir_text("/tmp/other-folder")
            self.window._set_post_download_output_dir(target.parent)

            with patch.object(self.window._effects.desktop, "open_path") as open_mock:
                self.window._maybe_open_output_folder()

        open_mock.assert_called_once_with(Path(output_dir))

    def test_mixed_url_shows_overlay_alert(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.window.show()
        QApplication.processEvents()
        self.window.url_edit.setText(mixed)
        self.assertEqual(self.window._pending_mixed_url, mixed)
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_NONE_INDEX,
        )
        self.assertEqual(self.window.source_details_host.height(), 0)
        self.assertTrue(self.window.mixed_url_overlay.isVisible())
        self.assertFalse(self.window._fetch_timer.isActive())

    def test_mixed_url_choice_uses_playlist_url(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.window.url_edit.setText(mixed)
        self.window._apply_mixed_url_choice(use_playlist=True)
        self.assertEqual(
            self.window.url_edit.text().strip(),
            "https://www.youtube.com/playlist?list=PLXYZ",
        )
        self.assertEqual(self.window._pending_mixed_url, "")
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_PLAYLIST_INDEX,
        )
        self.assertTrue(self.window.mixed_url_overlay.isHidden())

    def test_mixed_url_choice_uses_single_video_url(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.window.url_edit.setText(mixed)
        self.window._apply_mixed_url_choice(use_playlist=False)
        self.assertEqual(
            self.window.url_edit.text().strip(),
            "https://www.youtube.com/watch?v=abc123",
        )
        self.assertEqual(self.window._pending_mixed_url, "")
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_NONE_INDEX,
        )
        self.assertTrue(self.window.mixed_url_overlay.isHidden())

    def test_playlist_url_shows_playlist_items_without_prompt(self) -> None:
        self.window.url_edit.setText("https://www.youtube.com/playlist?list=PLXYZ")
        self.assertEqual(self.window._pending_mixed_url, "")
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_PLAYLIST_INDEX,
        )

    def test_responsive_output_inspector_reflow_on_resize(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.resize(900, 800)
        QApplication.processEvents()
        self.assertEqual(
            self.window.workspace_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        workspace_rect = self.window.workspace_layout.parentWidget().rect().adjusted(
            0, 0, -1, -1
        )
        self.assertLessEqual(
            self.window.output_section.geometry().right(),
            workspace_rect.right() + 1,
        )

        self.window.resize(1180, 900)
        QApplication.processEvents()
        self.assertEqual(
            self.window.workspace_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.source_row),
            0,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.format_card),
            1,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.save_card),
            -1,
        )
        self.assertIs(
            self.window.save_card.parentWidget(),
            self.window.format_card,
        )
        self.assertEqual(
            self.window.folder_row_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        self.assertEqual(
            self.window.mixed_buttons_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )

        self.window.resize(1500, 820)
        QApplication.processEvents()
        self.assertEqual(
            self.window.workspace_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.source_row),
            0,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.format_card),
            1,
        )
        self.assertEqual(
            self.window.output_layout.indexOf(self.window.save_card),
            -1,
        )
        self.assertEqual(
            self.window.folder_row_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        self.assertEqual(
            self.window.mixed_buttons_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )

    def test_output_form_labels_clear_controls_in_default_and_loaded_states(self) -> None:
        self.window.show()
        QApplication.processEvents()

        def map_rect_to_output(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.output_section, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.output_section, widget.rect().bottomRight()
            )
            return QRect(top_left, bottom_right).normalized()

        self.assertTrue(self.window.format_combo.isVisible())
        self.assertEqual(self.window.codec_label.text(), "Codec")
        self.assertEqual(self.window.format_label.text(), "Quality")
        for label, field in (
            (self.window.content_type_label, self.window.video_radio),
            (self.window.content_type_label, self.window.audio_radio),
            (self.window.container_label, self.window.container_combo),
            (self.window.codec_label, self.window.codec_combo),
            (self.window.format_label, self.window.format_combo),
        ):
            overlap = map_rect_to_output(label).intersected(map_rect_to_output(field))
            self.assertFalse(
                overlap.width() > 2 and overlap.height() > 2,
                f"{label.text()} overlaps {type(field).__name__} in the default layout",
            )

        self.window.format_combo.addItem("1080p")
        self.window._sync_format_combo_visibility()
        QApplication.processEvents()

        self.assertTrue(self.window.format_combo.isVisible())
        overlap = map_rect_to_output(self.window.format_label).intersected(
            map_rect_to_output(self.window.format_combo)
        )
        self.assertFalse(
            overlap.width() > 2 and overlap.height() > 2,
            "Quality label overlaps the quality picker after quality options load",
        )

    def test_audio_mode_marks_codec_as_not_needed(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._audio_labels = ["Best audio only"]
        self.window._audio_lookup = {"Best audio only": {"acodec": "opus"}}
        self.window.audio_radio.setChecked(True)
        self.window._on_mode_change()
        QApplication.processEvents()

        self.assertEqual(self.window.codec_label.text(), "Codec")
        self.assertEqual(
            self.window.codec_combo.toolTip(),
            "No codec selection is needed for audio-only downloads.",
        )
        self.assertEqual(self.window.codec_combo.currentText(), "Auto")
        self.assertEqual(self.window.format_label.text(), "Quality")
        self.assertEqual(
            self.window.format_combo.toolTip(),
            "Best audio is selected automatically for audio-only downloads.",
        )
        self.assertTrue(self.window.format_combo.isVisible())
        self.assertFalse(self.window.format_combo.isEnabled())
        self.assertEqual(self.window.format_combo.currentText(), "Auto")

    def test_output_form_split_layout_uses_right_aligned_label_column(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        self.assertEqual(self.window._output_layout_mode, "split")
        labels = list(self.window._output_form_labels)
        self.assertTrue(labels)
        self.assertEqual(len({label.width() for label in labels}), 1)

        def map_rect_to_format(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.format_card, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.format_card,
                widget.rect().bottomRight(),
            )
            return QRect(top_left, bottom_right).normalized()

        right_edges = [map_rect_to_format(label).right() for label in labels]
        self.assertLessEqual(max(right_edges) - min(right_edges), 2)
        for label in labels:
            self.assertTrue(bool(label.alignment() & Qt.AlignmentFlag.AlignRight))
            self.assertFalse(bool(label.alignment() & Qt.AlignmentFlag.AlignLeft))

    def test_output_form_fields_share_aligned_split_column_edges(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        def map_rect_to_format(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.format_card, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.format_card,
                widget.rect().bottomRight(),
            )
            return QRect(top_left, bottom_right).normalized()

        left_edge_widgets = (
            self.window.container_combo,
            self.window.codec_combo,
            self.window.format_combo,
            self.window.filename_edit,
            self.window.output_dir_edit,
        )
        left_edges = [map_rect_to_format(widget).left() for widget in left_edge_widgets]
        self.assertLessEqual(max(left_edges) - min(left_edges), 2)

        right_edge_widgets = (
            self.window.container_combo,
            self.window.codec_combo,
            self.window.format_combo,
            self.window.filename_edit,
            self.window.browse_button,
        )
        right_edges = [map_rect_to_format(widget).right() for widget in right_edge_widgets]
        self.assertLessEqual(max(right_edges) - min(right_edges), 2)

    def test_mixed_url_choice_preserves_window_size(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1110, 820)
        QApplication.processEvents()
        original = self.window.size()

        self.window.url_edit.setText(mixed)
        self.window._apply_mixed_url_choice(use_playlist=True)
        QApplication.processEvents()
        self.assertEqual(self.window.size(), original)

        self.window.url_edit.setText(mixed)
        self.window._apply_mixed_url_choice(use_playlist=False)
        QApplication.processEvents()
        self.assertEqual(self.window.size(), original)

    def test_mixed_url_choice_buttons_have_width_for_full_text(self) -> None:
        metrics = QFontMetrics(self.window.use_single_video_url_button.font())
        single_needed = metrics.horizontalAdvance(
            self.window.use_single_video_url_button.text()
        )
        playlist_needed = metrics.horizontalAdvance(
            self.window.use_playlist_url_button.text()
        )
        self.assertGreaterEqual(
            self.window.use_single_video_url_button.minimumWidth(), single_needed + 8
        )
        self.assertGreaterEqual(
            self.window.use_playlist_url_button.minimumWidth(), playlist_needed + 8
        )

    def test_output_controls_do_not_overlap_across_sizes(self) -> None:
        self.window.show()
        QApplication.processEvents()

        def map_rect_to_output(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.output_section, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.output_section, widget.rect().bottomRight()
            )
            return QRect(top_left, bottom_right).normalized()

        scan_types = (QLineEdit, QComboBox, QPushButton, QCheckBox, QRadioButton)
        widths = (900, 1000, 1100, 1180, 1320, 1500, 1700)
        heights = (800, 820, 900, 1000)

        for width in widths:
            for height in heights:
                self.window.resize(width, height)
                QApplication.processEvents()
                controls = []
                for control_type in scan_types:
                    controls.extend(
                        widget
                        for widget in self.window.output_section.findChildren(control_type)
                        if widget.isVisible()
                    )
                mapped = [(widget, map_rect_to_output(widget)) for widget in controls]
                for idx, (left_widget, left_rect) in enumerate(mapped):
                    for right_widget, right_rect in mapped[idx + 1 :]:
                        if (
                            left_widget.parentWidget() is right_widget
                            or right_widget.parentWidget() is left_widget
                        ):
                            continue
                        overlap = left_rect.intersected(right_rect)
                        self.assertFalse(
                            overlap.width() > 2 and overlap.height() > 2,
                            (
                                f"Unexpected overlap at {width}x{height}: "
                                f"{type(left_widget).__name__} vs {type(right_widget).__name__}"
                            ),
                        )

    def test_combined_output_inspector_stays_nested_across_resizes(self) -> None:
        self.window.show()
        QApplication.processEvents()

        def map_rect_to_output(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.output_section, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.output_section, widget.rect().bottomRight()
            )
            return QRect(top_left, bottom_right).normalized()

        for width, height in ((900, 760), (900, 800), (950, 800), (1000, 800), (1110, 820)):
            with self.subTest(size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()

                output_rect = self.window.output_section.rect().adjusted(0, 0, -1, -1)
                format_rect = map_rect_to_output(self.window.format_card)
                save_rect = self.window.save_card.geometry().adjusted(0, 0, -1, -1)
                format_inner_rect = self.window.format_card.rect().adjusted(0, 0, -1, -1)

                self.assertTrue(
                    output_rect.contains(format_rect),
                    f"Combined output card drifts outside the output section at {width}x{height}",
                )
                self.assertTrue(
                    format_inner_rect.contains(save_rect),
                    f"Save controls drift outside the combined output card at {width}x{height}",
                )

    def test_rapid_resize_burst_keeps_card_seams_aligned(self) -> None:
        self.window.show()
        QApplication.processEvents()

        def right_edge_in_main(widget: QWidget) -> int:
            return widget.mapTo(self.window.main_page, widget.rect().topRight()).x()

        def left_edge_in_main(widget: QWidget) -> int:
            return widget.mapTo(self.window.main_page, widget.rect().topLeft()).x()

        def map_rect_to_output(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.output_section, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.output_section, widget.rect().bottomRight()
            )
            return QRect(top_left, bottom_right).normalized()

        for width, height in (
            (900, 760),
            (1220, 820),
            (950, 760),
            (1500, 900),
            (900, 800),
            (1700, 960),
            (1110, 820),
        ):
            self.window.resize(width, height)

        QApplication.processEvents()

        output_rect = self.window.output_section.rect().adjusted(0, 0, -1, -1)
        format_rect = map_rect_to_output(self.window.format_card)
        save_rect = self.window.save_card.geometry().adjusted(0, 0, -1, -1)
        format_inner_rect = self.window.format_card.rect().adjusted(0, 0, -1, -1)

        self.assertTrue(
            output_rect.contains(format_rect),
            "Combined output card should stay inside the output section after a rapid resize burst",
        )
        self.assertTrue(
            format_inner_rect.contains(save_rect),
            "Save controls should stay inside the combined output card after a rapid resize burst",
        )
        self.assertLessEqual(
            abs(
                right_edge_in_main(self.window.output_section)
                - right_edge_in_main(self.window.run_actions_card)
            ),
            5,
            "Run actions should stay flush with the output section after a rapid resize burst",
        )
        self.assertLessEqual(
            abs(
                left_edge_in_main(self.window.output_section)
                - left_edge_in_main(self.window.run_actions_card)
            ),
            5,
            "Run actions should stay flush with the output section after a rapid resize burst",
        )

    def test_run_actions_card_stays_aligned_with_output_section_across_resizes(self) -> None:
        self.window.show()
        QApplication.processEvents()

        def right_edge_in_main(widget: QWidget) -> int:
            return widget.mapTo(self.window.main_page, widget.rect().topRight()).x()

        def left_edge_in_main(widget: QWidget) -> int:
            return widget.mapTo(self.window.main_page, widget.rect().topLeft()).x()

        for width, height in ((900, 760), (900, 800), (950, 760), (1110, 820), (1220, 820)):
            with self.subTest(size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()

                self.assertLessEqual(
                    abs(
                        right_edge_in_main(self.window.output_section)
                        - right_edge_in_main(self.window.run_actions_card)
                    ),
                    5,
                    f"Run actions drift away from the output section at {width}x{height}",
                )
                self.assertLessEqual(
                    abs(
                        left_edge_in_main(self.window.output_section)
                        - left_edge_in_main(self.window.run_actions_card)
                    ),
                    5,
                    f"Run actions drift away from the output section at {width}x{height}",
                )

    def test_run_state_host_keeps_activity_card_off_page_after_actions_are_embedded(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertTrue(self.window.downloads_button.isChecked())
        self.assertIs(
            self.window.run_activity_card.parentWidget(),
            self.window.run_state_host,
        )
        self.assertFalse(self.window.run_state_host.isVisible())
        self.assertFalse(self.window.run_activity_card.isVisibleTo(self.window.main_page))
        self.assertEqual(self.window.run_state_host.width(), 0)
        self.assertEqual(self.window.run_state_host.height(), 0)
        self.assertLess(self.window.run_state_host.geometry().right(), 0)

    def test_hidden_run_state_widgets_do_not_overlap_source_row(self) -> None:
        self.window.show()
        QApplication.processEvents()

        row_rect = QRect(
            self.window.source_row.mapTo(
                self.window.main_page,
                self.window.source_row.rect().topLeft(),
            ),
            self.window.source_row.size(),
        )
        for widget in (
            self.window.run_state_host,
            self.window.run_activity_card,
        ):
            with self.subTest(widget=widget.objectName() or type(widget).__name__):
                geom = QRect(
                    widget.mapTo(self.window.main_page, widget.rect().topLeft()),
                    widget.size(),
                )
                self.assertFalse(widget.isVisibleTo(self.window.main_page))
                self.assertFalse(geom.intersects(row_rect))

    def test_output_section_fills_right_column_height(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        def bottom_in_main(widget: QWidget) -> int:
            return widget.mapTo(self.window.main_page, widget.rect().bottomLeft()).y()

        self.assertEqual(
            bottom_in_main(self.window.output_section),
            bottom_in_main(self.window.main_page),
        )

    def test_run_actions_card_tracks_output_width_across_resizes(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for width, height in ((900, 760), (950, 760), (1110, 820), (1220, 820)):
            with self.subTest(size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()

                self.assertLessEqual(
                    abs(self.window.output_section.width() - self.window.run_actions_card.width()),
                    10,
                    f"Right column widths diverged at {width}x{height}",
                )

    def test_min_window_downloading_state_has_no_overlap_or_cutoff(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1180, 900)
        QApplication.processEvents()

        self.window._show_progress_item = True
        self.window._set_metrics_visible(True)
        self.window._set_current_item_display(progress="1/3", title="Example")
        self.window._on_progress_update(
            {
                "status": "downloading",
                "percent": 42.0,
                "speed": "2.0 MiB/s",
                "eta": "0:09",
            }
        )
        QApplication.processEvents()
        self.assertTrue(self.window.metrics_strip.isVisible())
        self.assertTrue(self.window.item_label.isVisible())
        self.assertTrue(self.window.progress_label.isVisible())
        self.assertTrue(self.window.speed_label.isVisible())
        self.assertTrue(self.window.eta_label.isVisible())

        scan_types = (QLineEdit, QComboBox, QPushButton, QCheckBox, QRadioButton)

        for section in (
            self.window.format_card,
            self.window.save_card,
            self.window.run_actions_card,
        ):
            section_rect = section.rect().adjusted(-2, -2, 1, 1)
            controls = []
            for control_type in scan_types:
                controls.extend(
                    widget
                    for widget in section.findChildren(control_type)
                    if widget.isVisible()
                )

            mapped = []
            for widget in controls:
                top_left = widget.mapTo(section, widget.rect().topLeft())
                bottom_right = widget.mapTo(section, widget.rect().bottomRight())
                rect = QRect(top_left, bottom_right).normalized()
                mapped.append((widget, rect))
                self.assertTrue(
                    section_rect.contains(rect),
                    f"{type(widget).__name__} is clipped outside {section.objectName()} in the desktop split layout",
                )

            for idx, (left_widget, left_rect) in enumerate(mapped):
                for right_widget, right_rect in mapped[idx + 1 :]:
                    if (
                        left_widget.parentWidget() is right_widget
                        or right_widget.parentWidget() is left_widget
                    ):
                        continue
                    overlap = left_rect.intersected(right_rect)
                    self.assertFalse(
                        overlap.width() > 2 and overlap.height() > 2,
                        (
                            "Unexpected overlap in the desktop downloading split layout: "
                            f"{type(left_widget).__name__} vs {type(right_widget).__name__}"
                        ),
                    )

        section = self.window.run_activity_card
        section_rect = section.rect().adjusted(0, 0, -1, -1)
        controls = []
        for control_type in scan_types:
            controls.extend(
                widget for widget in section.findChildren(control_type) if widget.isVisible()
            )

        mapped = []
        for widget in controls:
            top_left = widget.mapTo(section, widget.rect().topLeft())
            bottom_right = widget.mapTo(section, widget.rect().bottomRight())
            rect = QRect(top_left, bottom_right).normalized()
            mapped.append((widget, rect))
            self.assertTrue(
                section_rect.contains(rect),
                f"{type(widget).__name__} is clipped outside {section.objectName()} in the run activity card",
            )

        for idx, (left_widget, left_rect) in enumerate(mapped):
            for right_widget, right_rect in mapped[idx + 1 :]:
                if (
                    left_widget.parentWidget() is right_widget
                    or right_widget.parentWidget() is left_widget
                ):
                    continue
                overlap = left_rect.intersected(right_rect)
                self.assertFalse(
                    overlap.width() > 2 and overlap.height() > 2,
                    (
                        "Unexpected overlap in the run activity card layout: "
                        f"{type(left_widget).__name__} vs {type(right_widget).__name__}"
                    ),
                )

    def test_downloads_page_is_not_wrapped_in_scroll_area(self) -> None:
        self.assertIs(self.window.panel_stack.widget(self.window._main_page_index), self.window.main_page)
        self.assertNotIsInstance(self.window.main_page, QScrollArea)
        self.assertEqual(self.window.main_page.findChildren(QScrollArea), [])

    def test_min_window_downloads_view_fits_without_vertical_scroll(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        QApplication.processEvents()

        bottom = self.window.output_section.mapTo(
            self.window.main_page,
            self.window.output_section.rect().bottomLeft(),
        ).y()
        self.assertLessEqual(
            bottom,
            self.window.main_page.height() + 2,
            "Downloads view should fit inside the minimum window height",
        )

    def test_compact_run_actions_trim_button_sizing_and_keep_horizontal_stack(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        for button in (
            self.window.start_button,
            self.window.add_queue_button,
            self.window.cancel_button,
        ):
            self.assertTrue(bool(button.property("compact")))

        self.assertLess(
            self.window.start_button.minimumHeight(),
            self.window.analyze_button.minimumHeight(),
        )
        self.assertEqual(
            self.window.start_button.minimumHeight(),
            self.window.add_queue_button.minimumHeight(),
        )
        self.assertLessEqual(
            abs(
                self.window.start_button.geometry().top()
                - self.window.add_queue_button.geometry().top()
            ),
            2,
        )
        self.assertLessEqual(
            abs(
                self.window.add_queue_button.geometry().top()
                - self.window.cancel_button.geometry().top()
            ),
            2,
        )
        self.assertGreater(
            self.window.add_queue_button.geometry().left(),
            self.window.start_button.geometry().left(),
        )
        self.assertGreater(
            self.window.cancel_button.geometry().left(),
            self.window.add_queue_button.geometry().left(),
        )
        start_left = self.window.start_button.mapTo(
            self.window.run_actions_card,
            self.window.start_button.rect().topLeft(),
        ).x()
        start_top = self.window.start_button.mapTo(
            self.window.run_actions_card,
            self.window.start_button.rect().topLeft(),
        ).y()
        cancel_right = self.window.cancel_button.mapTo(
            self.window.run_actions_card,
            self.window.cancel_button.rect().topRight(),
        ).x()
        cancel_bottom = self.window.cancel_button.mapTo(
            self.window.run_actions_card,
            self.window.cancel_button.rect().bottomLeft(),
        ).y()
        right_gap = self.window.run_actions_card.rect().right() - cancel_right
        bottom_gap = self.window.run_actions_card.rect().bottom() - cancel_bottom
        self.assertLessEqual(start_left, 4)
        self.assertLessEqual(start_top, 4)
        self.assertLessEqual(right_gap, 4)
        self.assertLessEqual(bottom_gap, 4)

        self.window.resize(1220, 900)
        QApplication.processEvents()

        self.assertTrue(bool(self.window.start_button.property("compact")))
        self.assertLess(
            self.window.start_button.minimumHeight(),
            self.window.analyze_button.minimumHeight(),
        )

    def test_run_activity_card_omits_session_stats_cards(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertIsNone(self.window.run_activity_card.findChild(QWidget, "runStatsGrid"))
        self.assertEqual(
            self.window.run_activity_card.findChildren(QWidget, "sessionMetricCard"),
            [],
        )

    def test_run_activity_card_keeps_comfortable_inner_padding_in_compact_layout(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 800)
        QApplication.processEvents()

        activity_layout = self.window.run_activity_card.layout()
        self.assertIsNotNone(activity_layout)
        activity_margins = activity_layout.contentsMargins()
        self.assertGreaterEqual(activity_margins.left(), 8)
        self.assertGreaterEqual(activity_margins.top(), 8)

    def test_combined_output_card_keeps_save_controls_nested_at_compact_or_default_heights(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for width, height in ((1220, 820), (1220, 800), (900, 800)):
            self.window.resize(width, height)
            QApplication.processEvents()
            format_rect = self.window.format_card.rect().adjusted(0, 0, -1, -1)
            save_rect = self.window.save_card.geometry().adjusted(0, 0, -1, -1)
            self.assertTrue(
                format_rect.contains(save_rect),
                f"Save controls drift outside the combined output card at {width}x{height}",
            )
            self.assertGreater(
                save_rect.top(),
                0,
                f"Save controls collapse into the top edge of the combined output card at {width}x{height}",
            )

    def test_combined_output_card_keeps_save_controls_visible_before_and_after_loading_formats(self) -> None:
        self.window.show()
        QApplication.processEvents()

        empty_heights: dict[tuple[int, int], int] = {}
        for width, height in ((1220, 820), (900, 800)):
            with self.subTest(state="empty", size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()
                empty_heights[(width, height)] = self.window.format_card.height()
                self.assertTrue(
                    self.window.format_card.rect()
                    .adjusted(0, 0, -1, -1)
                    .contains(self.window.save_card.geometry().adjusted(0, 0, -1, -1)),
                    f"Save controls should stay inside the combined output card at {width}x{height}",
                )

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        format_label = "1080p 1920x1080 MP4 30fps [1080p] ~78.9 MiB"
        self.window._video_labels = [format_label]
        self.window._video_lookup = {
            format_label: {
                "ext": "mp4",
                "vcodec": "avc1",
                "label": format_label,
            }
        }
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window.container_combo.setCurrentIndex(
            self.window.container_combo.findData("mp4")
        )
        self.window.codec_combo.setCurrentIndex(
            self.window.codec_combo.findData("avc1")
        )
        QApplication.processEvents()

        for width, height in ((1220, 820), (900, 800)):
            with self.subTest(state="loaded", size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()
                self.assertTrue(self.window.format_combo.isVisible())
                self.assertGreaterEqual(
                    self.window.format_card.height(),
                    empty_heights[(width, height)],
                    f"Combined output card should not shrink after quality rows load at {width}x{height}",
                )
                self.assertTrue(
                    self.window.format_card.rect()
                    .adjusted(0, 0, -1, -1)
                    .contains(self.window.save_card.geometry().adjusted(0, 0, -1, -1)),
                    f"Save controls should stay inside the combined output card after formats load at {width}x{height}",
                )

    def test_loaded_formats_keep_spacing_between_quality_and_save_rows(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        format_label = "1080p 1920x1080 MP4 30fps [1080p] ~78.9 MiB"
        self.window._video_labels = [format_label]
        self.window._video_lookup = {
            format_label: {
                "ext": "mp4",
                "vcodec": "avc1",
                "label": format_label,
            }
        }
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window.container_combo.setCurrentIndex(
            self.window.container_combo.findData("mp4")
        )
        self.window.codec_combo.setCurrentIndex(
            self.window.codec_combo.findData("avc1")
        )
        QApplication.processEvents()

        for width, height in (
            (1220, 820),
            (1220, 800),
            (900, 800),
            (900, 760),
            (1500, 900),
            (1700, 960),
        ):
            with self.subTest(size=f"{width}x{height}"):
                self.window.resize(width, height)
                QApplication.processEvents()

                self.assertTrue(self.window.format_combo.isVisible())

                save_rect = self.window.save_card.geometry().adjusted(0, 0, -1, -1)
                self.assertGreaterEqual(
                    save_rect.top()
                    - self.window.format_combo.mapTo(
                        self.window.format_card,
                        self.window.format_combo.rect().bottomLeft(),
                    ).y(),
                    8,
                    f"Loaded formats collapse the spacing between quality and save rows at {width}x{height}",
                )

                folder_bottom = self.window.browse_button.mapTo(
                    self.window.format_card,
                    self.window.browse_button.rect().bottomLeft(),
                ).y()
                self.assertGreaterEqual(
                    self.window.format_card.rect().bottom() - folder_bottom,
                    8,
                    f"Output folder controls sit too close to the combined output card edge at {width}x{height}",
                )

    def test_format_card_expands_when_quality_combo_becomes_visible(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 800)
        QApplication.processEvents()

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p mp4 (avc1)"]
        self.window._video_lookup = {
            "1080p mp4 (avc1)": {
                "ext": "mp4",
                "vcodec": "avc1",
                "label": "1080p mp4 (avc1)",
            }
        }
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window.container_combo.setCurrentIndex(
            self.window.container_combo.findData("mp4")
        )
        self.window.codec_combo.setCurrentIndex(
            self.window.codec_combo.findData("avc1")
        )
        QApplication.processEvents()

        self.assertTrue(self.window.format_combo.isVisible())
        format_rect = QRect(
            self.window.format_combo.mapTo(
                self.window.format_card, self.window.format_combo.rect().topLeft()
            ),
            self.window.format_combo.mapTo(
                self.window.format_card, self.window.format_combo.rect().bottomRight()
            ),
        ).normalized()
        card_rect = self.window.format_card.rect().adjusted(0, 0, -1, -1)

        self.assertTrue(
            card_rect.contains(format_rect),
            "Visible quality selector should remain inside the FORMAT card",
        )

    def test_output_dir_field_resets_to_start_of_path(self) -> None:
        path = "/Users/harshakrishnaswamy/Downloads/example/folder"

        self.window._set_output_dir_text(path)

        self.assertEqual(
            self.window.output_dir_edit.text(),
            path,
        )
        self.assertEqual(self.window.output_dir_edit.toolTip(), path)
        self.assertEqual(self.window.output_dir_edit.cursorPosition(), 0)

    def test_min_width_combined_output_card_keeps_output_folder_controls_clear_and_roomy(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1180, 900)
        QApplication.processEvents()

        card_rect = self.window.format_card.rect().adjusted(0, 0, -1, -1)
        output_rect = QRect(
            self.window.output_dir_edit.mapTo(
                self.window.format_card, self.window.output_dir_edit.rect().topLeft()
            ),
            self.window.output_dir_edit.mapTo(
                self.window.format_card, self.window.output_dir_edit.rect().bottomRight()
            ),
        ).normalized()
        browse_rect = QRect(
            self.window.browse_button.mapTo(
                self.window.format_card, self.window.browse_button.rect().topLeft()
            ),
            self.window.browse_button.mapTo(
                self.window.format_card, self.window.browse_button.rect().bottomRight()
            ),
        ).normalized()

        self.assertTrue(card_rect.contains(output_rect))
        self.assertTrue(card_rect.contains(browse_rect))
        overlap = output_rect.intersected(browse_rect)
        self.assertFalse(
            overlap.width() > 2 and overlap.height() > 2,
            "Output folder field overlaps the browse button in the combined output card",
        )
        self.assertEqual(
            self.window.folder_row_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
            "Desktop split layout should keep the folder row on one line",
        )
        self.assertGreater(
            browse_rect.left(),
            output_rect.right(),
            "Browse button should sit to the right of the output folder field in the combined output card",
        )
        self.assertGreaterEqual(
            self.window.output_dir_edit.width(),
            220,
            "Output folder field should keep enough visible width in the combined output card",
        )

    def test_min_window_top_actions_have_icons_and_no_overlap(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        def map_rect_to_actions(widget: QWidget) -> QRect:
            top_left = widget.mapTo(self.window.top_actions, widget.rect().topLeft())
            bottom_right = widget.mapTo(
                self.window.top_actions, widget.rect().bottomRight()
            )
            return QRect(top_left, bottom_right).normalized()

        controls = [
            self.window.downloads_button,
            self.window.queue_button,
            self.window.logs_button,
            self.window.settings_button,
        ]

        actions_rect = self.window.top_actions.rect()
        visible_controls = [widget for widget in controls if widget.isVisible()]
        self.assertTrue(visible_controls, "No visible controls in top actions")
        mapped = []
        for widget in visible_controls:
            rect = map_rect_to_actions(widget)
            mapped.append((widget, rect))
            self.assertTrue(
                actions_rect.contains(rect),
                f"{type(widget).__name__} is clipped at 900x760",
            )
            if isinstance(widget, QPushButton):
                self.assertFalse(
                    widget.icon().isNull(),
                    f"{widget.text()} icon is missing",
                )

        for idx, (left_widget, left_rect) in enumerate(mapped):
            for right_widget, right_rect in mapped[idx + 1 :]:
                if (
                    left_widget.parentWidget() is right_widget
                    or right_widget.parentWidget() is left_widget
                ):
                    continue
                overlap = left_rect.intersected(right_rect)
                self.assertFalse(
                    overlap.width() > 2 and overlap.height() > 2,
                    (
                        "Unexpected top action overlap: "
                        f"{type(left_widget).__name__} vs {type(right_widget).__name__}"
                    ),
                )

    def test_top_actions_geometry_stays_stable_after_header_refreshes(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        before_width = self.window.top_actions.width()

        self.window._set_logs_alert(True)
        self.window._refresh_top_action_icons()
        self.window._open_panel("queue")
        self.window._close_panel()
        self.window._set_logs_alert(False)
        self.window._refresh_top_action_icons()
        QApplication.processEvents()

        self.assertEqual(self.window.top_actions.width(), before_width)

        actions_rect = self.window.top_actions.rect().adjusted(0, 0, -1, -1)
        for button in (
            self.window.downloads_button,
            self.window.queue_button,
            self.window.logs_button,
            self.window.settings_button,
        ):
            if not button.isVisible():
                continue
            top_left = button.mapTo(self.window.top_actions, button.rect().topLeft())
            bottom_right = button.mapTo(
                self.window.top_actions, button.rect().bottomRight()
            )
            rect = QRect(top_left, bottom_right).normalized()
            self.assertTrue(
                actions_rect.contains(rect),
                f"{button.text()} shifted outside the top actions rail",
            )

    def test_top_nav_selection_card_tracks_visible_section_and_hides_for_settings(self) -> None:
        self.window.show()
        QApplication.processEvents()

        selection = self.window.classic_actions.findChild(QWidget, "topNavSelection")
        self.assertIsNotNone(selection)
        assert selection is not None
        self.assertTrue(selection.isVisible())

        initial_center = selection.geometry().center()
        downloads_center = self.window.downloads_button.geometry().center()
        self.assertLess(abs(initial_center.x() - downloads_center.x()), 4)

        self.window.logs_button.click()
        QTest.qWait(260)
        QApplication.processEvents()

        logs_center = self.window.logs_button.geometry().center()
        selection_center = selection.geometry().center()
        self.assertLess(abs(selection_center.x() - logs_center.x()), 4)
        self.assertTrue(self.window.logs_button.isChecked())

        self.window.settings_button.click()
        QTest.qWait(260)
        QApplication.processEvents()

        self.assertFalse(selection.isVisible())
        self.assertTrue(self.window.settings_button.isChecked())

    def test_top_nav_selection_card_animates_between_sections(self) -> None:
        self.window.show()
        QApplication.processEvents()

        selection = self.window.classic_actions.findChild(QWidget, "topNavSelection")
        self.assertIsNotNone(selection)
        assert selection is not None

        start_x = selection.geometry().center().x()
        target_x = self.window.logs_button.geometry().center().x()
        self.assertLess(start_x, target_x)

        self.window.logs_button.click()
        QTest.qWait(40)
        QApplication.processEvents()

        mid_x = selection.geometry().center().x()
        self.assertGreater(mid_x, start_x)
        self.assertLess(mid_x, target_x)

        QTest.qWait(260)
        QApplication.processEvents()

        final_x = selection.geometry().center().x()
        self.assertLess(abs(final_x - target_x), 4)

    def test_content_mode_selection_card_tracks_checked_mode(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        mode_row = self.window.video_radio.parentWidget()
        self.assertIsNotNone(mode_row)
        assert mode_row is not None

        selection = mode_row.findChild(QWidget, "contentModeSelection")
        self.assertIsNotNone(selection)
        assert selection is not None
        self.assertTrue(selection.isVisible())
        self.assertLess(selection.width(), self.window.video_radio.width())
        self.assertLess(selection.height(), self.window.video_radio.height())

        initial_center = selection.geometry().center()
        video_center = self.window.video_radio.geometry().center()
        self.assertLess(abs(initial_center.x() - video_center.x()), 4)
        self.assertLess(abs(initial_center.y() - video_center.y()), 4)

        self.window.audio_radio.setChecked(True)
        QTest.qWait(260)
        QApplication.processEvents()

        audio_center = self.window.audio_radio.geometry().center()
        selection_center = selection.geometry().center()
        self.assertLess(abs(selection_center.x() - audio_center.x()), 4)
        self.assertLess(abs(selection_center.y() - audio_center.y()), 4)
        self.assertTrue(self.window.audio_radio.isChecked())

    def test_content_mode_buttons_are_vertically_centered_in_segment(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        mode_row = self.window.video_radio.parentWidget()
        self.assertIsNotNone(mode_row)
        assert mode_row is not None

        for button in (self.window.video_radio, self.window.audio_radio):
            with self.subTest(button=button.text()):
                top_gap = button.geometry().top()
                bottom_gap = mode_row.height() - (button.geometry().bottom() + 1)
                self.assertLessEqual(abs(top_gap - bottom_gap), 1)

        self.assertLessEqual(
            abs(self.window.video_radio.width() - self.window.audio_radio.width()),
            1,
        )

    def test_output_fields_share_uniform_height(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        for height in (MIN_WINDOW_HEIGHT, ROOMY_CONTENT_LAYOUT_MIN_HEIGHT):
            with self.subTest(height=height):
                self.window.resize(MIN_WINDOW_WIDTH, height)
                QApplication.processEvents()

                controls = (
                    self.window.container_combo,
                    self.window.codec_combo,
                    self.window.format_combo,
                    self.window.filename_edit,
                    self.window.output_dir_edit,
                    self.window.browse_button,
                )
                control_heights = [control.height() for control in controls if control.isVisible()]
                self.assertTrue(control_heights)
                self.assertLessEqual(max(control_heights) - min(control_heights), 1)

    def test_content_mode_control_is_more_compact_than_other_output_fields(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        mode_row = self.window.video_radio.parentWidget()
        self.assertIsNotNone(mode_row)
        assert mode_row is not None

        for height in (MIN_WINDOW_HEIGHT, ROOMY_CONTENT_LAYOUT_MIN_HEIGHT):
            with self.subTest(height=height):
                self.window.resize(MIN_WINDOW_WIDTH, height)
                QApplication.processEvents()

                self.assertLess(mode_row.height(), self.window.container_combo.height())

    def test_content_mode_control_stays_left_aligned_within_its_field_host(self) -> None:
        self.window.show()
        self.window.video_radio.setChecked(True)
        QApplication.processEvents()

        mode_row = self.window.video_radio.parentWidget()
        self.assertIsNotNone(mode_row)
        assert mode_row is not None

        block_layout = self.window.content_type_row.layout()
        self.assertIsNotNone(block_layout)
        assert block_layout is not None

        row = block_layout.itemAt(0).widget()
        self.assertIsNotNone(row)
        assert row is not None

        row_layout = row.layout()
        self.assertIsNotNone(row_layout)
        assert row_layout is not None

        field_host = row_layout.itemAt(1).widget()
        self.assertIsNotNone(field_host)
        assert field_host is not None

        self.assertLess(mode_row.width(), field_host.width())
        mode_row_left = mode_row.mapToGlobal(mode_row.rect().topLeft()).x()
        field_host_left = field_host.mapToGlobal(field_host.rect().topLeft()).x()
        self.assertLessEqual(
            abs(mode_row_left - field_host_left),
            2,
        )

    def test_classic_top_actions_remove_session_and_keep_settings_separate_on_right(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        self.assertTrue(self.window.downloads_button.isVisible())
        self.assertTrue(self.window.queue_button.isVisible())
        self.assertTrue(self.window.logs_button.isVisible())
        self.assertTrue(self.window.settings_button.isVisible())
        self.assertNotIn(
            "Session",
            [
                button.text()
                for button in self.window.classic_actions.findChildren(QPushButton)
            ],
        )
        self.assertNotIn(
            self.window.settings_button,
            self.window.classic_actions.findChildren(QPushButton),
        )

        x_positions = {
            button.text(): button.mapTo(
                self.window.top_actions, button.rect().topLeft()
            ).x()
            for button in (
                self.window.downloads_button,
                self.window.queue_button,
                self.window.logs_button,
            )
            if button.isVisible()
        }
        self.assertEqual(
            sorted(x_positions, key=x_positions.get),
            ["Downloads", "Queue", "Logs"],
        )
        settings_x = self.window.settings_button.mapTo(
            self.window.top_actions, self.window.settings_button.rect().topLeft()
        ).x()
        self.assertGreater(settings_x, x_positions["Logs"])

    def test_downloads_button_returns_to_main_view(self) -> None:
        self.window._open_panel("queue")
        self.assertEqual(self.window._active_panel_name, "queue")
        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(self.window.panel_stack.currentIndex(), self.window._main_page_index)
        self.assertTrue(self.window.downloads_button.isChecked())

    def test_queue_labels_use_title_case_and_panel_has_no_remove_button(self) -> None:
        self.window._open_panel("queue")
        QApplication.processEvents()

        queue_panel = self.window.panel_stack.currentWidget()
        self.assertIsNotNone(queue_panel)
        assert queue_panel is not None
        self.assertIsNone(queue_panel.findChild(QFrame, "panelCard"))
        self.assertFalse(
            any(
                button.text() in {"Remove", "Move up", "Move down", "Clear"}
                for button in queue_panel.findChildren(QPushButton)
            )
        )
        self.assertIn(
            "Download Queue",
            [
                label.text()
                for label in queue_panel.findChildren(QLabel)
                if label.text()
            ],
        )

    def test_panels_do_not_render_header_subtitles(self) -> None:
        for panel_name in ("queue", "logs", "settings"):
            with self.subTest(panel=panel_name):
                self.window._open_panel(panel_name)
                QApplication.processEvents()

                panel = self.window.panel_stack.currentWidget()
                self.assertIsNotNone(panel)
                assert panel is not None
                self.assertEqual(panel.findChildren(QLabel, "panelHeaderSubtitle"), [])

    def test_session_button_is_removed_from_top_actions(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertNotIn("session", self.window._panel_name_to_index)
        self.assertNotIn("history", self.window._panel_name_to_index)
        self.assertNotIn(
            "Session",
            [
                button.text()
                for button in self.window.classic_actions.findChildren(QPushButton)
            ],
        )

    def test_settings_button_opens_preferences_panel_without_outer_card(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.settings_button.click()
        QApplication.processEvents()

        self.assertEqual(self.window._active_panel_name, "settings")
        self.assertEqual(
            self.window.panel_stack.currentIndex(),
            self.window._panel_name_to_index["settings"],
        )
        self.assertTrue(self.window.settings_button.isChecked())
        settings_panel = self.window.panel_stack.currentWidget()
        self.assertIsNotNone(settings_panel)
        self.assertIsNone(settings_panel.findChild(QFrame, "panelCard"))
        form_card = settings_panel.findChild(QFrame, "panelFormCard")
        self.assertIsNotNone(form_card)
        assert form_card is not None
        margins = form_card.layout().contentsMargins()
        self.assertEqual((margins.left(), margins.top(), margins.right(), margins.bottom()), (0, 0, 0, 0))

    def test_settings_cards_remove_outer_layout_padding(self) -> None:
        self.window._open_panel("settings")
        QApplication.processEvents()

        settings_panel = self.window.panel_stack.currentWidget()
        self.assertIsNotNone(settings_panel)
        assert settings_panel is not None

        cards = settings_panel.findChildren(QFrame, "settingsRowCard")
        app_card = settings_panel.findChild(QFrame, "settingsAppCard")
        if app_card is not None:
            cards.append(app_card)

        self.assertGreaterEqual(len(cards), 3)
        for card in cards:
            with self.subTest(card=card.objectName()):
                layout = card.layout()
                self.assertIsNotNone(layout)
                assert layout is not None
                margins = layout.contentsMargins()
                self.assertEqual(
                    (margins.left(), margins.top(), margins.right(), margins.bottom()),
                    (0, 0, 0, 0),
                )

    def test_settings_cards_use_transparent_cardless_styling(self) -> None:
        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QFrame#settingsRowCard, QFrame#settingsAppCard\s*\{[^}]*background:\s*transparent;[^}]*border:\s*none;[^}]*border-radius:\s*0px;",
        )

    def test_settings_panel_shows_only_basic_app_details_and_no_about_button(self) -> None:
        self.window._open_panel("settings")
        QApplication.processEvents()

        settings_panel = self.window.panel_stack.currentWidget()
        self.assertIsNotNone(settings_panel)
        assert settings_panel is not None

        self.assertFalse(
            any(
                button.text() == "About"
                for button in settings_panel.findChildren(QPushButton)
            )
        )

        label_text = [
            label.text()
            for label in settings_panel.findChildren(QLabel)
            if label.text().strip()
        ]
        self.assertIn(APP_DISPLAY_NAME, label_text)
        self.assertIn(f"Version {APP_VERSION}", label_text)
        self.assertNotIn(APP_DESCRIPTION, label_text)
        self.assertNotIn(APP_PRIVACY_NOTE, label_text)
        self.assertNotIn("Shortcuts:", label_text)
        self.assertNotIn("\n".join(APP_SHORTCUT_LINES), label_text)
        self.assertIsNone(settings_panel.findChild(QLabel, "settingsAppIcon"))

    def test_settings_app_footer_is_bottom_centered_without_app_heading(self) -> None:
        self.window.show()
        self.window.resize(900, 760)
        self.window._open_panel("settings")
        QApplication.processEvents()

        settings_panel = self.window.panel_stack.currentWidget()
        self.assertIsNotNone(settings_panel)
        assert settings_panel is not None

        form_card = settings_panel.findChild(QFrame, "panelFormCard")
        app_card = settings_panel.findChild(QFrame, "settingsAppCard")
        self.assertIsNotNone(form_card)
        self.assertIsNotNone(app_card)
        assert form_card is not None
        assert app_card is not None

        self.assertIsNone(app_card.findChild(QLabel, "settingsRowTitle"))

        app_rect = QRect(
            app_card.mapTo(form_card, app_card.rect().topLeft()),
            app_card.size(),
        )
        form_rect = form_card.rect()
        self.assertLessEqual(
            abs(app_rect.center().x() - form_rect.center().x()),
            4,
        )
        self.assertLessEqual(
            abs(app_rect.bottom() - form_rect.bottom()),
            4,
        )

    def test_downloads_button_is_noop_when_main_view_is_already_active(self) -> None:
        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(
            self.window.panel_stack.currentIndex(), self.window._main_page_index
        )

        before = len(self.window._active_animations)
        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(
            self.window.panel_stack.currentIndex(), self.window._main_page_index
        )
        self.assertTrue(self.window.downloads_button.isChecked())
        self.assertEqual(len(self.window._active_animations), before)

    def test_panel_switch_does_not_start_transition_animation(self) -> None:
        before = len(self.window._active_animations)
        self.window._open_panel("queue")
        QApplication.processEvents()

        self.assertEqual(len(self.window._active_animations), before)

    def test_on_url_changed_invalidates_fetch_and_resets_selection_state(self) -> None:
        self.window.video_radio.setChecked(True)
        mp4_index = self.window.container_combo.findData("mp4")
        self.assertGreaterEqual(mp4_index, 0)
        self.window.container_combo.setCurrentIndex(mp4_index)
        codec_index = self.window.codec_combo.findData("avc1")
        self.assertGreaterEqual(codec_index, 0)
        self.window.codec_combo.setCurrentIndex(codec_index)

        self.window._is_fetching = True
        self.window._fetch_request_seq = 7
        self.window._active_fetch_request_id = 7

        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")

        self.assertFalse(self.window._is_fetching)
        self.assertEqual(self.window._active_fetch_request_id, 8)
        self.assertEqual(self.window._current_mode(), "")
        self.assertEqual(self.window._current_container(), "")
        self.assertEqual(self.window._current_codec(), "")
        self.assertEqual(self.window.format_combo.count(), 0)

    def test_formats_error_sets_specific_status_and_resets_preview_tooltip(self) -> None:
        url = "https://www.youtube.com/watch?v=abc123"
        self.window.url_edit.blockSignals(True)
        self.window.url_edit.setText(url)
        self.window.url_edit.blockSignals(False)
        self.window._active_fetch_request_id = 42
        self.window._is_fetching = True
        self.window._set_preview_title("Existing title")

        with patch.object(self.window, "_show_feedback_popup"):
            self.window._on_formats_loaded(
                request_id=42,
                url=url,
                payload={},
                error=True,
                is_playlist=False,
        )

        self.assertFalse(self.window._is_fetching)
        self.assertTrue(
            self.window.status_value.text().startswith("Could not fetch formats")
        )

    def test_fetching_state_keeps_format_controls_disabled_until_ready(self) -> None:
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._is_fetching = True
        self.window.video_radio.setChecked(True)
        self.window._update_controls_state()

        self.assertFalse(self.window.video_radio.isEnabled())
        self.assertFalse(self.window.container_combo.isEnabled())
        self.assertFalse(self.window.start_button.isEnabled())

    def test_combo_popups_open_on_first_show_after_formats_loaded(self) -> None:
        self.window.show()
        QApplication.processEvents()
        url = "https://www.youtube.com/watch?v=abc123"
        self.window.url_edit.setText(url)
        self.window.video_radio.setChecked(True)
        self.window._active_fetch_request_id = 15
        self.window._is_fetching = True

        payload = {
            "collections": {
                "video_labels": ["1080p mp4 (avc1)"],
                "video_lookup": {
                    "1080p mp4 (avc1)": {
                        "format_id": "137",
                        "ext": "mp4",
                        "vcodec": "avc1.640028",
                        "acodec": "none",
                    }
                },
                "audio_labels": [],
                "audio_lookup": {},
                "audio_languages": [],
            },
            "preview_title": "Sample",
            "source_summary": {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "Example Channel",
                "detail_one_text": "Formats ready",
                "detail_two_text": "5m 42s",
                "detail_three_text": "1 video format",
            },
        }
        self.window._on_formats_loaded(
            request_id=15,
            url=url,
            payload=payload,
            error=False,
            is_playlist=False,
        )
        mp4_index = self.window.container_combo.findData("mp4")
        self.assertGreaterEqual(mp4_index, 0)
        self.window.container_combo.setCurrentIndex(mp4_index)
        avc1_index = self.window.codec_combo.findData("avc1")
        self.assertGreaterEqual(avc1_index, 0)
        self.window.codec_combo.setCurrentIndex(avc1_index)
        QApplication.processEvents()
        self.assertGreater(self.window.format_combo.count(), 0)

        for combo in (
            self.window.container_combo,
            self.window.codec_combo,
            self.window.format_combo,
        ):
            self.assertTrue(combo.isEnabled())
            combo.showPopup()
            QApplication.processEvents()
            self.assertTrue(combo.view().window().isVisible())
            combo.hidePopup()
            QApplication.processEvents()

    def test_combo_popups_expand_to_full_option_count(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        QApplication.processEvents()

        combos = (
            self.window.container_combo,
            self.window.codec_combo,
        )
        for combo in combos:
            self.assertGreater(combo.count(), 0)
            combo.showPopup()
            QApplication.processEvents()
            self.assertEqual(combo.maxVisibleItems(), combo.count())
            self.assertEqual(
                combo.view().verticalScrollBarPolicy(),
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )
            combo.hidePopup()
            QApplication.processEvents()

    def test_settings_combo_popup_uses_custom_surface_styling(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window._open_panel("settings")
        QApplication.processEvents()

        combo = self.window.edit_friendly_encoder_combo
        combo.showPopup()
        QApplication.processEvents()

        self.assertTrue(combo.view().window().isVisible())
        popup_stylesheet = combo.view().window().styleSheet()
        self.assertIn("QListView#nativeComboView", popup_stylesheet)
        self.assertIn("background: #272724;", popup_stylesheet)
        self.assertIn("border-radius: 20px;", popup_stylesheet)

        combo.hidePopup()
        QApplication.processEvents()

    def test_stylesheet_uses_one_shared_combo_box_shape(self) -> None:
        stylesheet = qt_style.build_stylesheet("/tmp/combo-down-arrow.svg")
        self.assertRegex(
            stylesheet,
            r"QComboBox\s*\{[^}]*border-radius:\s*16px;",
        )

    def test_settings_encoder_combo_matches_dropdown_box_height(self) -> None:
        self.window.show()
        QApplication.processEvents()

        downloads_height = self.window.container_combo.height()
        self.window._open_panel("settings")
        QApplication.processEvents()

        self.assertEqual(self.window.edit_friendly_encoder_combo.height(), downloads_height)

    def test_settings_encoder_combo_disables_unavailable_encoders(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window._open_panel("settings")
        QApplication.processEvents()

        combo = self.window.edit_friendly_encoder_combo
        model = combo.model()

        self.assertFalse(model.item(combo.findData("apple")).isEnabled())
        self.assertTrue(model.item(combo.findData("nvidia")).isEnabled())
        self.assertFalse(model.item(combo.findData("amd")).isEnabled())
        self.assertFalse(model.item(combo.findData("intel")).isEnabled())
        self.assertTrue(model.item(combo.findData("cpu")).isEnabled())

    def test_add_to_queue_shows_counted_success_feedback(self) -> None:
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()
        self._load_ready_preview_with_formats(queue_ready=True)
        self.window._on_mode_change()
        QApplication.processEvents()
        mp4_index = self.window.container_combo.findData("mp4")
        self.assertGreaterEqual(mp4_index, 0)
        self.window.container_combo.setCurrentIndex(mp4_index)
        avc1_index = self.window.codec_combo.findData("avc1")
        self.assertGreaterEqual(avc1_index, 0)
        self.window.codec_combo.setCurrentIndex(avc1_index)
        self.assertGreater(self.window.format_combo.count(), 0)
        self.window.format_combo.setCurrentIndex(0)
        QApplication.processEvents()
        self.assertTrue(self.window.add_queue_button.isEnabled())

        with patch.object(self.window, "_source_feedback_toast_timeout_ms", return_value=0):
            QTest.mouseClick(self.window.add_queue_button, Qt.MouseButton.LeftButton)
            QApplication.processEvents()
            QTest.qWait(350)
            QApplication.processEvents()

        self.assertEqual(len(self.window.queue_items), 2)
        self.assertEqual(self.window.status_value.text(), "Added to queue as item 2")
        self.assertEqual(self.window.source_feedback_toast_title.text(), "Added to queue")
        self.assertEqual(
            self.window.source_feedback_toast_message.text(),
            "Saved as queue item 2. Queue now has 2 items. Open Queue to review, or press Download to start it.",
        )

    def test_close_event_while_downloading_requests_cancel(self) -> None:
        self.window._is_downloading = True
        self.window._cancel_requested = False
        self.window._cancel_event = threading.Event()

        event = QCloseEvent()
        with patch.object(self.window._effects.dialogs, "question", return_value=True):
            self.window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertTrue(self.window._close_after_cancel)
        self.assertTrue(self.window._cancel_requested)
        self.assertIsNotNone(self.window._cancel_event)
        self.assertTrue(self.window._cancel_event.is_set())

    def test_on_download_done_closes_after_cancel(self) -> None:
        self.window._is_downloading = True
        self.window._close_after_cancel = True

        with patch("gui.qt.app.QTimer.singleShot", side_effect=lambda _ms, cb: cb()):
            with patch.object(self.window, "close") as close_mock:
                self.window._on_download_done(download.DOWNLOAD_CANCELLED)

        close_mock.assert_called_once()
        self.assertFalse(self.window._close_after_cancel)

    def test_on_download_done_resets_progress_details(self) -> None:
        self.window._is_downloading = True
        self.window.progress_bar.setValue(724)
        self.window.progress_label.setText("Progress: 92.4%")
        self.window.speed_label.setText("Speed: 3.5 MiB/s")
        self.window.eta_label.setText("ETA: 00:09")
        self.window.item_label.setText("Item: 1/5 - example.mp4")

        self.window._on_download_done(download.DOWNLOAD_SUCCESS)

        self.assertEqual(self.window.progress_bar.value(), 0)
        self.assertEqual(self.window.progress_label.text(), "Progress: -")
        self.assertEqual(self.window.speed_label.text(), "Speed: -")
        self.assertEqual(self.window.eta_label.text(), "ETA: -")
        self.assertEqual(self.window.item_label.text(), "Item: -")

    def test_finished_progress_update_does_not_force_full_bar(self) -> None:
        self.window.progress_bar.setValue(250)
        self.window.progress_label.setText("Progress: 25.0%")
        self.window.eta_label.setText("ETA: 1:00")

        self.window._on_progress_update({"status": "finished"})

        self.assertEqual(self.window.progress_bar.value(), 250)
        self.assertEqual(self.window.progress_label.text(), "Progress: 25.0%")
        self.assertEqual(self.window.eta_label.text(), "ETA: Finalizing")

    def test_queue_progress_update_uses_overall_queue_percent(self) -> None:
        self.window.queue_items = [
            {"url": "https://example.com/watch?v=one", "settings": {}},
            {"url": "https://example.com/watch?v=two", "settings": {}},
            {"url": "https://example.com/watch?v=three", "settings": {}},
        ]
        self.window.queue_active = True
        self.window.queue_index = 1
        self.window._show_progress_item = True

        self.window._on_progress_update(
            {
                "status": "item",
                "item": "2/3 Example",
            }
        )
        self.window._on_progress_update(
            {
                "status": "downloading",
                "percent": 50.0,
                "speed": "2.0 MiB/s",
                "eta": "0:09",
            }
        )

        self.assertEqual(self.window.progress_label.text(), "Progress: 50.0%")
        self.assertEqual(self.window.item_label.text(), "Item: 2/3 - Example")

    def test_prepare_next_queue_item_progress_keeps_completed_queue_share(self) -> None:
        self.window.queue_items = [
            {"url": "https://example.com/watch?v=one", "settings": {}},
            {"url": "https://example.com/watch?v=two", "settings": {}},
            {"url": "https://example.com/watch?v=three", "settings": {}},
        ]
        self.window.queue_active = True
        self.window.queue_index = 2
        self.window.speed_label.setText("Speed: 5.0 MiB/s")
        self.window.eta_label.setText("ETA: 0:01")

        self.window._prepare_next_queue_item_progress()

        self.assertEqual(self.window.progress_label.text(), "Progress: 66.7%")
        self.assertEqual(self.window.speed_label.text(), "Speed: -")
        self.assertEqual(self.window.eta_label.text(), "ETA: -")

    def test_progress_bar_stays_in_metrics_card_when_idle(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window._reset_progress_summary()
        QApplication.processEvents()

        self.assertIs(self.window.progress_bar.parentWidget(), self.window.metrics_card)
        self.assertTrue(self.window.progress_bar.isVisible())
        self.assertEqual(self.window.progress_bar.value(), 0)

    def test_item_progress_update_splits_index_and_title(self) -> None:
        self.window.show()
        self.window.resize(1700, 760)
        QApplication.processEvents()
        self.window._show_progress_item = True
        self.window._on_progress_update(
            {
                "status": "item",
                "item": "41/169 #41 Festival Plaza Mission Complete! - Pokemon",
            }
        )
        self.assertEqual(
            self.window.item_label.text(),
            "Item: 41/169 - #41 Festival Plaza Mission Complete! - Pokemon",
        )

    def test_item_progress_update_accepts_title_only(self) -> None:
        self.window._show_progress_item = True
        self.window._on_progress_update(
            {
                "status": "item",
                "item": "Single Video Title",
            }
        )
        self.assertEqual(self.window.item_label.text(), "Item: Single Video Title")

    def test_item_label_elides_long_title_with_three_dots(self) -> None:
        self.window.show()
        self.window.resize(900, 760)
        QApplication.processEvents()
        self.window._show_progress_item = True
        long_title = "Very long title for progress display " * 40
        self.window._set_current_item_display(progress="1/999", title=long_title)
        QApplication.processEvents()

        shown = self.window.item_label.text()
        self.assertTrue(shown.startswith("Item: 1/999 - "))
        self.assertTrue(shown.endswith("..."))
        self.assertNotIn("…", shown)
        self.assertEqual(self.window.item_label.toolTip(), long_title)

    def test_metrics_strip_keeps_progress_speed_and_eta_fully_visible(self) -> None:
        self.window.show()
        self.window.resize(900, 760)
        QApplication.processEvents()

        self.window._on_progress_update(
            {
                "status": "downloading",
                "percent": 37.1,
                "speed": "71.37 MiB/s",
                "eta": "0:00",
            }
        )
        self.window._set_current_item_display(
            progress="-",
            title="How did this get so long that it must truncate",
        )
        QApplication.processEvents()

        for label in (
            self.window.progress_label,
            self.window.speed_label,
            self.window.eta_label,
        ):
            self.assertGreaterEqual(
                label.width(),
                label.sizeHint().width(),
                f"{label.text()} is horizontally clipped",
            )
        shown_item = self.window.item_label.text()
        self.assertTrue(
            shown_item == "Item: How did this get so long that it must truncate"
            or shown_item.endswith("..."),
            shown_item,
        )

    def test_metrics_strip_label_widths_stay_fixed_during_progress_updates(self) -> None:
        self.window.show()
        self.window.resize(900, 760)
        QApplication.processEvents()

        initial_widths = (
            self.window.progress_label.width(),
            self.window.speed_label.width(),
            self.window.eta_label.width(),
        )

        self.window._on_progress_update(
            {
                "status": "downloading",
                "percent": 100.0,
                "speed": "9999.99 MiB/s",
                "eta": "99:59:59",
                "playlist_eta": "999:59:59",
            }
        )
        QApplication.processEvents()

        self.assertEqual(
            (
                self.window.progress_label.width(),
                self.window.speed_label.width(),
                self.window.eta_label.width(),
            ),
            initial_widths,
        )

    def test_attention_log_shows_logs_alert_icon(self) -> None:
        self.assertFalse(self.window._logs_alert_active)
        self.window._append_log("[error] network timeout")

        self.assertTrue(self.window._logs_alert_active)
        self.assertFalse(self.window.logs_button.icon().isNull())

    def test_opening_logs_clears_logs_alert_icon(self) -> None:
        self.window._append_log("[error] could not fetch formats")
        self.assertTrue(self.window._logs_alert_active)
        self.window._open_panel("logs")

        self.assertFalse(self.window._logs_alert_active)
        self.assertFalse(self.window.logs_button.icon().isNull())

    def test_queue_list_supports_drag_reordering(self) -> None:
        self.window.queue_items = [
            {"url": "a", "settings": {}},
            {"url": "b", "settings": {}},
            {"url": "c", "settings": {}},
        ]
        self.window._refresh_queue_panel()

        self.assertEqual(
            self.window.queue_list.dragDropMode(),
            QAbstractItemView.DragDropMode.InternalMove,
        )

        self.window.queue_list.items_reordered.emit([2, 0, 1])

        self.assertEqual(
            [item.get("url") for item in self.window.queue_items],
            ["c", "a", "b"],
        )

        self.window.queue_active = True
        self.window._refresh_queue_panel_state()

        self.assertEqual(
            self.window.queue_list.dragDropMode(),
            QAbstractItemView.DragDropMode.NoDragDrop,
        )

    def test_queue_reorder_preserves_queue_list_scroll_position(self) -> None:
        self.window.show()
        self.window.resize(900, 620)
        self.window._open_panel("queue")
        self.window.queue_items = [
            {"url": f"https://example.com/watch?v={idx}", "settings": {}}
            for idx in range(30)
        ]
        self.window._refresh_queue_panel()
        QApplication.processEvents()

        scrollbar = self.window.queue_list.verticalScrollBar()
        self.assertIsNotNone(scrollbar)
        assert scrollbar is not None
        self.assertGreater(scrollbar.maximum(), 0)

        preserved_value = max(1, scrollbar.maximum() // 2)
        scrollbar.setValue(preserved_value)
        QApplication.processEvents()

        reordered = list(range(1, len(self.window.queue_items))) + [0]
        self.window.queue_list.items_reordered.emit(reordered)
        QApplication.processEvents()

        self.assertEqual(self.window.queue_list.verticalScrollBar().value(), preserved_value)
        self.assertEqual(
            [item.get("url") for item in self.window.queue_items[:3]],
            [
                "https://example.com/watch?v=1",
                "https://example.com/watch?v=2",
                "https://example.com/watch?v=3",
            ],
        )

    def test_queue_list_expands_edge_autoscroll_margin_for_dragging(self) -> None:
        self.assertTrue(self.window.queue_list.hasAutoScroll())
        self.assertGreaterEqual(self.window.queue_list.autoScrollMargin(), 48)

    def test_queue_list_inline_remove_button_deletes_clicked_item(self) -> None:
        self.window.queue_items = [
            {"url": "a", "settings": {}},
            {"url": "b", "settings": {}},
            {"url": "c", "settings": {}},
        ]
        self.window._refresh_queue_panel()
        self.window.show()
        self.window._open_panel("queue")
        QApplication.processEvents()

        remove_rect = self.window.queue_list.remove_button_rect(1)
        self.assertFalse(remove_rect.isNull())

        QTest.mouseClick(
            self.window.queue_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=remove_rect.center(),
        )
        QApplication.processEvents()

        self.assertEqual(
            [item.get("url") for item in self.window.queue_items],
            ["a", "c"],
        )

    def test_queue_list_stores_title_and_settings_metadata(self) -> None:
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=abc",
                "title": "Example queue title",
                "settings": {
                    "mode": "video",
                    "format_filter": "mp4",
                    "codec_filter": "avc1",
                    "format_label": "1080p",
                    "custom_filename": "edited-name",
                },
            }
        ]
        self.window._refresh_queue_panel()

        item = self.window.queue_list.item(0)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.data(QUEUE_TITLE_ROLE), "Example queue title")
        self.assertEqual(
            item.data(QUEUE_META_ROLE),
            "Video · MP4 · AVC1 · 1080p · Save as edited-name",
        )
        self.assertIn("https://example.com/watch?v=abc", item.toolTip())

    def test_queue_list_edit_button_loads_item_into_form_and_updates_it(self) -> None:
        url = self._load_ready_preview_with_formats()
        self.window.queue_items = [
            {
                "url": url,
                "title": "Stored queue title",
                "settings": {
                    "mode": "video",
                    "format_filter": "mp4",
                    "codec_filter": "avc1",
                    "format_label": "1080p mp4 (avc1)",
                    "output_dir": "/tmp/queue-edit",
                    "custom_filename": "queued-name",
                },
            }
        ]
        self.window._refresh_queue_panel()
        self.window.show()
        self.window._open_panel("queue")
        QApplication.processEvents()

        edit_rect = self.window.queue_list.edit_button_rect(0)
        self.assertFalse(edit_rect.isNull())

        QTest.mouseClick(
            self.window.queue_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=edit_rect.center(),
        )
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(self.window.panel_stack.currentIndex(), self.window._main_page_index)
        self.assertEqual(self.window.add_queue_button.text(), "Update Queue Item")
        self.assertEqual(self.window.url_edit.text(), url)
        self.assertTrue(self.window.video_radio.isChecked())
        self.assertEqual(self.window.container_combo.currentData(), "mp4")
        self.assertEqual(self.window.codec_combo.currentData(), "avc1")
        self.assertEqual(self.window.format_combo.currentText(), "1080p mp4 (avc1)")
        self.assertEqual(self.window.filename_edit.text(), "queued-name")
        self.assertEqual(self.window.output_dir_edit.text(), "/tmp/queue-edit")

        self.window.filename_edit.setText("updated-name")
        self.window._on_add_to_queue()
        QApplication.processEvents()

        self.assertEqual(len(self.window.queue_items), 1)
        self.assertEqual(
            self.window.queue_items[0]["settings"]["custom_filename"],
            "updated-name",
        )
        self.assertEqual(self.window.queue_items[0]["title"], "Sample")
        self.assertEqual(self.window.add_queue_button.text(), "Add to queue")

    def test_run_action_buttons_keep_geometry_when_queue_edit_label_changes(self) -> None:
        url = self._load_ready_preview_with_formats()
        self.window.queue_items = [
            {
                "url": url,
                "title": "Stored queue title",
                "settings": {
                    "mode": "video",
                    "format_filter": "mp4",
                    "codec_filter": "avc1",
                    "format_label": "1080p mp4 (avc1)",
                    "output_dir": "/tmp/queue-edit",
                    "custom_filename": "queued-name",
                },
            }
        ]
        self.window._refresh_queue_panel()
        self.window.show()
        self.window.resize(1220, 820)
        QApplication.processEvents()

        def snapshot() -> dict[str, tuple[int, int]]:
            return {
                "start": (
                    self.window.start_button.width(),
                    self.window.start_button.mapTo(
                        self.window.run_actions_card,
                        self.window.start_button.rect().topLeft(),
                    ).x(),
                ),
                "add_queue": (
                    self.window.add_queue_button.width(),
                    self.window.add_queue_button.mapTo(
                        self.window.run_actions_card,
                        self.window.add_queue_button.rect().topLeft(),
                    ).x(),
                ),
                "cancel": (
                    self.window.cancel_button.width(),
                    self.window.cancel_button.mapTo(
                        self.window.run_actions_card,
                        self.window.cancel_button.rect().topLeft(),
                    ).x(),
                ),
            }

        baseline = snapshot()

        self.window._open_panel("queue")
        QApplication.processEvents()

        edit_rect = self.window.queue_list.edit_button_rect(0)
        self.assertFalse(edit_rect.isNull())
        QTest.mouseClick(
            self.window.queue_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=edit_rect.center(),
        )
        QApplication.processEvents()

        self.assertEqual(self.window.add_queue_button.text(), "Update Queue Item")
        self.assertEqual(snapshot(), baseline)

        self.window._on_add_to_queue()
        QApplication.processEvents()

        self.assertEqual(self.window.add_queue_button.text(), "Add to queue")
        self.assertEqual(snapshot(), baseline)

    def test_start_queue_download_sets_queue_run_state_and_starts_next_item(self) -> None:
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=1",
                "settings": {
                    "mode": "audio",
                    "format_filter": "mp3",
                    "format_label": "High",
                },
            }
        ]

        with patch.object(
            self.window._run_queue_controller, "start_next_queue_item"
        ) as start_next:
            self.window._start_queue_download()

        self.assertTrue(self.window.queue_active)
        self.assertEqual(self.window.queue_index, 0)
        self.assertTrue(self.window._is_downloading)
        self.assertTrue(self.window._show_progress_item)
        self.assertFalse(self.window._cancel_requested)
        self.assertIsNotNone(self.window._cancel_event)
        self.assertEqual(self.window.status_value.text(), "Downloading queue...")
        start_next.assert_called_once()

    def test_start_button_is_enabled_for_queue_only_context(self) -> None:
        self.window.url_edit.clear()
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=1",
                "settings": {
                    "mode": "audio",
                    "format_filter": "mp3",
                    "format_label": "High",
                },
            }
        ]

        self.window._update_controls_state()

        self.assertTrue(self.window.start_button.isEnabled())

    def test_start_button_uses_queue_when_items_exist(self) -> None:
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=1",
                "settings": {
                    "mode": "audio",
                    "format_filter": "mp3",
                    "format_label": "High",
                },
            }
        ]

        with patch.object(self.window._run_queue_controller, "start_queue_download") as start_queue:
            self.window._on_start()

        start_queue.assert_called_once_with()

    def test_start_queue_download_invalid_settings_shows_error(self) -> None:
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=1",
                "settings": {
                    "mode": "video",
                    "format_filter": "mp4",
                    "format_label": "1080p",
                },
            }
        ]

        with patch.object(self.window._effects.dialogs, "critical") as critical_mock:
            self.window._start_queue_download()

        self.assertFalse(self.window.queue_active)
        self.assertFalse(self.window._is_downloading)
        critical_mock.assert_called_once()

    def test_on_queue_item_done_finishes_when_last_item_completes(self) -> None:
        self.window.queue_items = [
            {
                "url": "https://example.com/watch?v=1",
                "settings": {
                    "mode": "audio",
                    "format_filter": "mp3",
                    "format_label": "High",
                },
            }
        ]
        self.window.queue_active = True
        self.window.queue_index = 0
        self.window._queue_failed_items = 0
        self.window._cancel_requested = False

        with patch.object(self.window._run_queue_controller, "finish_queue") as finish_mock:
            self.window._on_queue_item_done(had_error=False, cancelled=False)

        finish_mock.assert_called_once_with(cancelled=False)

    def test_run_queue_download_worker_runs_download_request(self) -> None:
        settings = {
            "mode": "audio",
            "format_filter": "mp3",
            "format_label": "High",
        }
        request = {
            "url": "https://example.com/watch?v=1",
            "output_dir": Path("/tmp"),
            "fmt_info": {},
            "fmt_label": "High",
            "format_filter": "mp3",
            "convert_to_mp4": False,
            "playlist_enabled": False,
            "playlist_items": None,
            "network_timeout_s": 20,
            "network_retries": 1,
            "retry_backoff_s": 1.5,
            "concurrent_fragments": 2,
            "subtitle_languages": [],
            "write_subtitles": False,
            "embed_subtitles": False,
            "audio_language": "",
            "custom_filename": "",
            "edit_friendly_encoder": "auto",
        }

        with patch.object(
            self.window._run_queue_controller,
            "resolve_format_for_url",
            return_value={"title": "Example"},
        ) as resolve_mock:
            with patch(
                "gui.qt.controllers.app_service.build_queue_download_request",
                return_value=request,
            ) as request_mock:
                with patch(
                    "gui.qt.controllers.app_service.run_download_request",
                    return_value=download.DOWNLOAD_SUCCESS,
                ) as run_mock:
                    self.window._run_queue_download_worker(
                        url="https://example.com/watch?v=1",
                        settings=settings,
                        index=1,
                        total=1,
                        default_output_dir="/tmp",
                    )

        resolve_mock.assert_called_once()
        request_mock.assert_called_once()
        run_mock.assert_called_once()

    def test_finish_queue_cancelled_resets_flags(self) -> None:
        self.window.queue_active = True
        self.window.queue_index = 1
        self.window._queue_failed_items = 2
        self.window._queue_started_ts = time.time() - 5
        self.window._is_downloading = True
        self.window._show_progress_item = True
        self.window._cancel_requested = True
        self.window._cancel_event = threading.Event()
        self.window._set_post_download_output_dir(Path("/tmp"))

        with patch.object(self.window, "_maybe_open_output_folder") as open_folder_mock:
            self.window._finish_queue(cancelled=True)

        self.assertFalse(self.window.queue_active)
        self.assertIsNone(self.window.queue_index)
        self.assertFalse(self.window._is_downloading)
        self.assertFalse(self.window._show_progress_item)
        self.assertFalse(self.window._cancel_requested)
        self.assertIsNone(self.window._cancel_event)
        self.assertEqual(self.window.status_value.text(), "Queue cancelled")
        self.assertIsNone(self.window._post_download_output_dir)
        open_folder_mock.assert_not_called()

    def test_export_diagnostics_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.window.output_dir_edit.setText(tmp_dir)
            self.window.url_edit.setText("https://example.com/watch?v=abc123")
            self.window._log_lines = ["line one", "line two"]

            with patch.object(self.window._effects.dialogs, "information") as info_mock:
                self.window._export_diagnostics()

            outputs = list(Path(tmp_dir).glob("yt-dlp-gui-diagnostics-*.txt"))
            self.assertEqual(len(outputs), 1)
            payload = outputs[0].read_text(encoding="utf-8")
            self.assertIn("[settings]", payload)
            self.assertIn("[logs]", payload)
            self.assertIn("line one", payload)
            self.assertTrue(any(line.startswith("[diag] exported ") for line in self.window._log_lines))
            self.assertEqual(self.window.status_value.text(), "Diagnostics exported")
            info_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
