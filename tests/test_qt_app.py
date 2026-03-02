import os
import threading
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
        QMessageBox,
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

    def test_source_feedback_reserves_height_for_hidden_tone(self) -> None:
        reserved_height = self.window.source_feedback_label.minimumHeight()
        self.assertGreater(reserved_height, 0)

        self.window._set_source_feedback("", tone="hidden")
        self.assertEqual(self.window.source_feedback_label.text(), "")
        self.assertEqual(self.window.source_feedback_label.property("tone"), "hidden")
        self.assertEqual(self.window.source_feedback_label.minimumHeight(), reserved_height)

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
            if isinstance(widget, QPushButton) and widget is not self.window.downloads_button:
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
        with patch(
            "gui.qt.app.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
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


if __name__ == "__main__":
    unittest.main()
