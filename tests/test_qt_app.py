import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QCloseEvent, QFontMetrics
    from PySide6.QtWidgets import (
        QApplication,
        QBoxLayout,
        QCheckBox,
        QComboBox,
        QLineEdit,
        QPushButton,
        QRadioButton,
        QWidget,
    )

    from gui.common import download
    from gui.core import urls as core_urls
    from gui.qt.app import (
        PREVIEW_TITLE_TOOLTIP_DEFAULT,
        SOURCE_DETAILS_NONE_INDEX,
        SOURCE_DETAILS_PLAYLIST_INDEX,
        QtYtDlpGui,
    )

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is required for Qt app tests")
class TestQtApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = QtYtDlpGui()

    def tearDown(self) -> None:
        self.window._is_downloading = False
        self.window._close_after_cancel = False
        self.window.close()
        self.window.deleteLater()

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

    def test_source_defaults_hide_playlist_items_and_prompt(self) -> None:
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_NONE_INDEX,
        )
        self.assertEqual(self.window.source_details_host.height(), 0)
        self.assertTrue(self.window.mixed_url_overlay.isHidden())

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

    def test_load_settings_always_defaults_output_folder_to_downloads(self) -> None:
        with patch(
            "gui.qt.app.settings_store.load_settings",
            return_value={
                "output_dir": "/tmp/custom",
                "subtitle_languages": "",
                "write_subtitles": False,
                "network_timeout": "20",
                "network_retries": "1",
                "retry_backoff": "1.5",
                "concurrent_fragments": "4",
                "open_folder_after_download": False,
            },
        ):
            window = QtYtDlpGui()
        try:
            self.assertEqual(
                window.output_dir_edit.text().strip(),
                str(Path.home() / "Downloads"),
            )
        finally:
            window.close()
            window.deleteLater()

    def test_load_settings_applies_edit_friendly_encoder_preference(self) -> None:
        with patch(
            "gui.qt.app.settings_store.load_settings",
            return_value={
                "output_dir": "/tmp/custom",
                "subtitle_languages": "",
                "write_subtitles": False,
                "network_timeout": "20",
                "network_retries": "1",
                "retry_backoff": "1.5",
                "concurrent_fragments": "4",
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

    def test_responsive_output_cards_reflow_on_resize(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.resize(1180, 900)
        QApplication.processEvents()
        mid_index = self.window.output_layout.indexOf(self.window.save_card)
        mid_row, mid_col, _, _ = self.window.output_layout.getItemPosition(
            mid_index
        )
        self.assertEqual((mid_row, mid_col), (0, 1))
        self.assertEqual(
            self.window.mixed_buttons_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )

        self.window.resize(1500, 820)
        QApplication.processEvents()
        wide_index = self.window.output_layout.indexOf(self.window.save_card)
        wide_row, wide_col, _, _ = self.window.output_layout.getItemPosition(wide_index)
        self.assertEqual((wide_row, wide_col), (0, 1))
        self.assertEqual(
            self.window.mixed_buttons_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )

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
        heights = (760, 820, 900, 1000)

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

    def test_min_window_downloading_state_has_no_overlap_or_cutoff(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
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
        run_section = self.window.main_page.findChild(QWidget, "runSection")
        self.assertIsNotNone(run_section)
        assert run_section is not None

        for section in (self.window.output_section, run_section):
            section_rect = section.rect().adjusted(0, 0, -1, -1)
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
                    f"{type(widget).__name__} is clipped outside {section.objectName()} at 900x760",
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
                            "Unexpected overlap in minimum downloading layout: "
                            f"{type(left_widget).__name__} vs {type(right_widget).__name__}"
                        ),
                    )

    def test_min_window_downloads_view_fits_without_vertical_scroll(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        scrollbar = self.window.main_scroll.verticalScrollBar()
        run_section = self.window.main_page.findChild(QWidget, "runSection")
        self.assertIsNotNone(run_section)
        assert run_section is not None

        bottom = run_section.mapTo(
            self.window.main_scroll.viewport(),
            run_section.rect().bottomLeft(),
        ).y()

        self.assertEqual(scrollbar.maximum(), 0)
        self.assertLessEqual(
            bottom,
            self.window.main_scroll.viewport().height() + 2,
            "Downloads view should fit inside the minimum window height",
        )

    def test_output_dir_field_resets_to_start_of_path(self) -> None:
        path = "/Users/harshakrishnaswamy/Downloads/example/folder"

        self.window._set_output_dir_text(path)

        self.assertEqual(self.window.output_dir_edit.text(), path)
        self.assertEqual(self.window.output_dir_edit.cursorPosition(), 0)

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
            self.window.history_button,
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

    def test_classic_top_actions_keep_settings_rightmost(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        buttons = (
            self.window.downloads_button,
            self.window.queue_button,
            self.window.history_button,
            self.window.logs_button,
            self.window.settings_button,
        )
        self.assertTrue(all(button.isVisible() for button in buttons))

        x_positions = {
            button.text(): button.mapTo(
                self.window.top_actions, button.rect().topLeft()
            ).x()
            for button in buttons
        }
        settings_x = x_positions["Settings"]
        self.assertGreater(settings_x, x_positions["Downloads"])
        self.assertGreater(settings_x, x_positions["Queue"])
        self.assertGreater(settings_x, x_positions["History"])
        self.assertGreater(settings_x, x_positions["Logs"])

    def test_downloads_button_returns_to_main_view(self) -> None:
        self.window._open_panel("queue")
        self.assertEqual(self.window._active_panel_name, "queue")
        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(self.window.panel_stack.currentIndex(), self.window._main_page_index)
        self.assertTrue(self.window.downloads_button.isChecked())

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
        self.assertEqual(self.window.preview_value.text(), "-")
        self.assertEqual(
            self.window.preview_value.toolTip(),
            PREVIEW_TITLE_TOOLTIP_DEFAULT,
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

    def test_download_result_defaults_to_download_info_mode(self) -> None:
        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(self.window.download_result_title.text(), "Download info:")
        self.assertEqual(self.window.download_result_card.property("state"), "info")
        self.assertFalse(self.window.copy_output_path_button.isEnabled())
        self.assertEqual(self.window.download_result_path.text(), "-")

    def test_record_output_updates_latest_download_card(self) -> None:
        output_path = Path("/tmp/test-video.mp4")

        self.window._record_download_output(output_path, "https://example.com/video")

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(self.window.download_result_title.text(), "Latest:")
        self.assertEqual(self.window.download_result_card.property("state"), "latest")
        self.assertTrue(self.window.download_result_path.text().endswith(".mp4"))
        self.assertEqual(
            self.window.download_result_path.toolTip(),
            str(output_path),
        )
        self.assertTrue(self.window.copy_output_path_button.isEnabled())

    def test_record_output_while_downloading_defers_latest_actions_until_done(self) -> None:
        output_path = Path("/tmp/test-video.mp4")
        self.window._is_downloading = True
        self.window._update_controls_state()

        self.window._record_download_output(output_path, "https://example.com/video")

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(self.window.download_result_title.text(), "Download info:")
        self.assertEqual(self.window.download_result_card.property("state"), "info")
        self.assertFalse(self.window.copy_output_path_button.isEnabled())
        self.assertEqual(self.window.download_result_path.toolTip(), str(output_path))

        self.window._on_download_done(download.DOWNLOAD_SUCCESS)

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(self.window.download_result_title.text(), "Latest:")
        self.assertEqual(self.window.download_result_card.property("state"), "latest")
        self.assertTrue(self.window.copy_output_path_button.isEnabled())

    def test_clearing_latest_output_resets_download_card(self) -> None:
        output_path = Path("/tmp/test-video.mp4")
        self.window._record_download_output(output_path, "https://example.com/video")
        self.assertFalse(self.window.download_result_card.isHidden())

        self.window._clear_last_output_path()

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(self.window.download_result_title.text(), "Download info:")
        self.assertEqual(self.window.download_result_card.property("state"), "info")
        self.assertEqual(self.window.download_result_path.text(), "-")
        self.assertFalse(self.window.copy_output_path_button.isEnabled())

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
        self.window._set_last_output_path(Path("/tmp/test-video.mp4"))

        with patch.object(self.window, "_maybe_open_output_folder") as open_folder_mock:
            self.window._finish_queue(cancelled=True)

        self.assertFalse(self.window.queue_active)
        self.assertIsNone(self.window.queue_index)
        self.assertFalse(self.window._is_downloading)
        self.assertFalse(self.window._show_progress_item)
        self.assertFalse(self.window._cancel_requested)
        self.assertIsNone(self.window._cancel_event)
        self.assertEqual(self.window.status_value.text(), "Queue cancelled")
        self.assertIsNone(self.window._latest_output_path)
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
