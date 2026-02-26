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
        SOURCE_DETAILS_PROMPT_INDEX,
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
                "ui_layout": "Simple",
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

    def test_mixed_url_shows_inline_alert(self) -> None:
        mixed = "https://www.youtube.com/watch?v=abc123&list=PLXYZ&index=3"
        self.window.url_edit.setText(mixed)
        self.assertEqual(self.window._pending_mixed_url, mixed)
        self.assertEqual(
            self.window.source_details_stack.currentIndex(),
            SOURCE_DETAILS_PROMPT_INDEX,
        )
        self.assertGreater(self.window.source_details_host.height(), 0)
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
            QBoxLayout.Direction.TopToBottom,
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
            self.window.use_single_video_url_button.minimumWidth(), single_needed + 30
        )
        self.assertGreaterEqual(
            self.window.use_playlist_url_button.minimumWidth(), playlist_needed + 30
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

        self.window._on_formats_loaded(
            request_id=42,
            url=url,
            payload={},
            error=True,
            is_playlist=False,
        )

        self.assertFalse(self.window._is_fetching)
        self.assertEqual(self.window.status_value.text(), "Could not fetch formats")
        self.assertEqual(self.window.preview_value.text(), "-")
        self.assertEqual(
            self.window.preview_value.toolTip(),
            PREVIEW_TITLE_TOOLTIP_DEFAULT,
        )

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

    def test_on_download_done_resets_progress_details(self) -> None:
        self.window._is_downloading = True
        self.window.progress_bar.setValue(724)
        self.window.progress_label.setText("Progress: 92.4%")
        self.window.speed_label.setText("Speed: 3.5 MiB/s")
        self.window.eta_label.setText("ETA: 00:09")
        self.window.item_label.setText("Current item: 1/5\nTitle: example.mp4")

        self.window._on_download_done(download.DOWNLOAD_SUCCESS)

        self.assertEqual(self.window.progress_bar.value(), 0)
        self.assertEqual(self.window.progress_label.text(), "Progress: -")
        self.assertEqual(self.window.speed_label.text(), "Speed: -")
        self.assertEqual(self.window.eta_label.text(), "ETA: -")
        self.assertEqual(self.window.item_label.text(), "Current item: -\nTitle: -")

    def test_finished_progress_update_does_not_force_full_bar(self) -> None:
        self.window.progress_bar.setValue(250)
        self.window.progress_label.setText("Progress: 25.0%")
        self.window.eta_label.setText("ETA: 1:00")

        self.window._on_progress_update({"status": "finished"})

        self.assertEqual(self.window.progress_bar.value(), 250)
        self.assertEqual(self.window.progress_label.text(), "Progress: 25.0%")
        self.assertEqual(self.window.eta_label.text(), "ETA: Finalizing...")

    def test_item_progress_update_splits_index_and_title(self) -> None:
        self.window._show_progress_item = True
        self.window._on_progress_update(
            {
                "status": "item",
                "item": "41/169 #41 Festival Plaza Mission Complete! - Pokemon",
            }
        )
        self.assertEqual(
            self.window.item_label.text(),
            "Current item: 41/169\nTitle: #41 Festival Plaza Mission Complete! - Pokemon",
        )

    def test_attention_log_shows_logs_alert_icon(self) -> None:
        self.window._append_log("[error] network timeout")

        self.assertFalse(self.window.logs_button.icon().isNull())
        logs_idx = self.window.simple_panel_selector.findText("Logs")
        self.assertGreaterEqual(logs_idx, 0)
        self.assertFalse(self.window.simple_panel_selector.itemIcon(logs_idx).isNull())

    def test_opening_logs_clears_logs_alert_icon(self) -> None:
        self.window._append_log("[error] could not fetch formats")
        self.window._open_panel("logs")

        self.assertTrue(self.window.logs_button.icon().isNull())
        logs_idx = self.window.simple_panel_selector.findText("Logs")
        self.assertGreaterEqual(logs_idx, 0)
        self.assertTrue(self.window.simple_panel_selector.itemIcon(logs_idx).isNull())


if __name__ == "__main__":
    unittest.main()
