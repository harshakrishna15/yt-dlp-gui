import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEasingCurve, QRect, Qt
    from PySide6.QtGui import QCloseEvent, QFontMetrics
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QBoxLayout,
        QCheckBox,
        QComboBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QWidget,
    )

    from gui.common import download
    from gui.app_meta import APP_DISPLAY_NAME, APP_VERSION
    from gui.core import urls as core_urls
    from gui.qt.app import (
        PREVIEW_TITLE_TOOLTIP_DEFAULT,
        SOURCE_DETAILS_NONE_INDEX,
        SOURCE_DETAILS_PLAYLIST_INDEX,
        QtYtDlpGui,
    )
    from gui.qt.constants import PANEL_SWITCH_FADE_MS

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

    def test_app_title_and_primary_analyze_action_defaults(self) -> None:
        self.assertEqual(self.window.windowTitle(), APP_DISPLAY_NAME)
        self.assertFalse(self.window.windowIcon().isNull())
        self.assertEqual(self.window.analyze_button.text(), "Analyze URL")
        self.assertFalse(self.window.analyze_button.isEnabled())
        self.assertEqual(
            self.window.source_feedback_label.text(),
            "Paste a video or playlist URL to load available formats.",
        )

    def test_source_preview_defaults_to_placeholder_copy(self) -> None:
        self.assertEqual(self.window.source_preview_badge.text(), "URL")
        self.assertEqual(self.window.preview_title_label.text(), "Source preview")
        self.assertEqual(
            self.window.source_preview_placeholder.text(),
            "Analyze a URL to load source details.",
        )
        self.assertEqual(self.window.source_preview_detail_one.text(), "")

    def test_source_preview_copy_is_not_vertically_clipped(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for label in (
            self.window.preview_title_label,
            self.window.source_preview_placeholder,
            self.window.source_preview_subtitle,
        ):
            self.assertGreaterEqual(
                label.geometry().height(),
                label.sizeHint().height(),
                f"{label.objectName()} is vertically clipped at the default window size",
            )

    def test_ready_summary_stays_hidden_until_output_choices_exist(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.assertFalse(self.window.ready_summary_label.isVisible())

        self.window.video_radio.setChecked(True)
        self.window._on_mode_change()
        self.window._refresh_ready_summary()
        QApplication.processEvents()

        self.assertTrue(self.window.ready_summary_label.isVisible())

    def test_workspace_tabs_switch_source_stack_and_toolbar_state(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.queue_view_button.click()
        QApplication.processEvents()
        self.assertEqual(
            self.window.source_view_stack.currentIndex(),
            self.window._queue_view_index,
        )
        self.assertEqual(self.window._active_workspace_name, "queue")
        self.assertTrue(self.window.queue_view_button.isChecked())
        self.assertTrue(self.window.queue_button.isChecked())

        self.window.history_view_button.click()
        QApplication.processEvents()
        self.assertEqual(
            self.window.source_view_stack.currentIndex(),
            self.window._history_view_index,
        )
        self.assertEqual(self.window._active_workspace_name, "history")
        self.assertTrue(self.window.history_view_button.isChecked())
        self.assertTrue(self.window.history_button.isChecked())

        self.window.downloads_button.click()
        QApplication.processEvents()
        self.assertEqual(
            self.window.source_view_stack.currentIndex(),
            self.window._current_view_index,
        )
        self.assertEqual(self.window._active_workspace_name, "current")
        self.assertTrue(self.window.current_view_button.isChecked())
        self.assertTrue(self.window.downloads_button.isChecked())

    def test_source_preview_keeps_output_section_stable_when_metadata_arrives(self) -> None:
        self.window.show()
        QApplication.processEvents()

        before_preview_height = self.window.source_preview_card.height()
        before_output_height = self.window.output_section.height()

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

        self.assertGreaterEqual(
            self.window.source_preview_card.height(), before_preview_height
        )
        self.assertEqual(self.window.output_section.height(), before_output_height)
        self.assertTrue(self.window.source_preview_subtitle.isVisible())

    def test_convert_check_only_appears_for_webm_container(self) -> None:
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

        self.window.container_combo.setCurrentIndex(webm_index)
        self.window._update_controls_state()
        QApplication.processEvents()
        self.assertTrue(self.window.convert_check.isVisible())

    def test_source_preview_detail_chips_reflow_after_metric_change(self) -> None:
        self.window.show()
        QApplication.processEvents()

        for chip in (
            self.window.source_preview_detail_one,
            self.window.source_preview_detail_two,
            self.window.source_preview_detail_three,
        ):
            chip.setStyleSheet(
                "font-size: 14px; padding: 6px 10px; border: 1px solid #000;"
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

        for chip in (
            self.window.source_preview_detail_one,
            self.window.source_preview_detail_two,
            self.window.source_preview_detail_three,
        ):
            self.assertGreaterEqual(
                chip.geometry().height(),
                chip.sizeHint().height(),
                f"{chip.objectName()} is vertically clipped after chip metrics change",
            )

    def test_url_entry_enables_analyze_action_without_auto_fetching(self) -> None:
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")

        self.assertTrue(self.window.analyze_button.isEnabled())
        self.assertEqual(self.window.analyze_button.text(), "Analyze URL")
        self.assertFalse(self.window._fetch_timer.isActive())
        self.assertIn("Analyze URL", self.window.source_feedback_label.text())

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
        self.window.resize(900, 760)
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

    def test_shortening_url_keeps_download_cards_full_width(self) -> None:
        self.window.show()
        QApplication.processEvents()

        source_section = self.window.main_page.findChild(QGroupBox, "sourceSection")
        self.assertIsNotNone(source_section)
        assert source_section is not None

        widths = [
            "https://www.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/",
            "https://",
            "h",
            "",
        ]
        base_source_width = source_section.width()
        base_output_width = self.window.output_section.width()
        base_run_width = self.window.run_section.width()
        for url in widths:
            self.window.url_edit.setText(url)
            QApplication.processEvents()
            panel_width = self.window.panel_stack.width()
            self.assertEqual(self.window.main_page.width(), panel_width)
            self.assertEqual(source_section.width(), base_source_width)
            self.assertEqual(self.window.output_section.width(), base_output_width)
            self.assertEqual(self.window.run_section.width(), base_run_width)
            self.assertLess(source_section.width(), panel_width)
            self.assertLess(self.window.output_section.width(), panel_width)

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
        self.window.url_edit.setText("https://www.youtube.com/watch?v=abc123")
        self.window._video_labels = ["1080p"]
        self.window._update_controls_state()

        self.assertEqual(self.window.analyze_button.text(), "Refresh formats")

    def test_secondary_panels_start_with_empty_states(self) -> None:
        self.assertEqual(self.window.queue_stack.currentIndex(), self.window._queue_empty_index)
        self.assertEqual(
            self.window.history_stack.currentIndex(),
            self.window._history_empty_index,
        )

        self.window._clear_logs()

        self.assertEqual(self.window.logs_stack.currentIndex(), self.window._logs_empty_index)

    def test_empty_state_cards_are_not_vertically_clipped(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window._clear_logs()
        QApplication.processEvents()

        for panel_name, stack in (
            ("queue", self.window.queue_stack),
            ("history", self.window.history_stack),
            ("logs", self.window.logs_stack),
        ):
            self.window._open_panel(panel_name)
            QApplication.processEvents()
            page = stack.currentWidget()
            self.assertIsNotNone(page)
            assert page is not None
            labels = [
                label
                for label in page.findChildren(QLabel)
                if label.objectName()
                in {
                    "panelEmptyBadge",
                    "panelEmptyTitle",
                    "panelEmptyDescription",
                    "panelEmptyHint",
                }
            ]
            self.assertTrue(labels, f"No empty-state labels found for {panel_name}")
            for label in labels:
                self.assertGreaterEqual(
                    label.geometry().height(),
                    label.sizeHint().height(),
                    (
                        f"{panel_name} empty-state label {label.objectName()} "
                        "is vertically clipped"
                    ),
                )

    def test_empty_state_cards_are_left_aligned(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window._clear_logs()
        QApplication.processEvents()

        for panel_name, stack in (
            ("queue", self.window.queue_stack),
            ("history", self.window.history_stack),
            ("logs", self.window.logs_stack),
        ):
            self.window._open_panel(panel_name)
            QApplication.processEvents()
            page = stack.currentWidget()
            self.assertIsNotNone(page)
            assert page is not None

            layout = page.layout()
            self.assertIsNotNone(layout)
            assert layout is not None
            card_item = layout.itemAt(1)
            self.assertIsNotNone(card_item)
            assert card_item is not None
            self.assertTrue(
                bool(card_item.alignment() & Qt.AlignmentFlag.AlignLeft),
                f"{panel_name} empty-state card is not left aligned",
            )

            labels = [
                label
                for label in page.findChildren(QLabel)
                if label.objectName()
                in {
                    "panelEmptyBadge",
                    "panelEmptyTitle",
                    "panelEmptyDescription",
                    "panelEmptyHint",
                }
            ]
            self.assertTrue(labels, f"No empty-state labels found for {panel_name}")
            for label in labels:
                self.assertTrue(
                    bool(label.alignment() & Qt.AlignmentFlag.AlignLeft),
                    f"{panel_name} empty-state label {label.objectName()} is not left aligned",
                )

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

        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )
        QApplication.processEvents()
        self.assertTrue(self.window.source_feedback_label.isVisible())
        self.assertFalse(self.window.source_feedback_toast.isVisible())

        self.window._set_source_feedback(
            "URL ready. Click Analyze URL to load formats and preview details.",
            tone="neutral",
        )
        QApplication.processEvents()
        self.assertFalse(self.window.source_feedback_label.isVisible())
        self.assertFalse(self.window.source_feedback_toast.isVisible())

        self.window._set_source_feedback("", tone="hidden")
        self.window._apply_responsive_layout()
        QApplication.processEvents()
        self.assertFalse(self.window.source_feedback_label.isVisible())
        self.assertFalse(self.window.source_feedback_toast.isVisible())

    def test_source_feedback_banner_shows_inline_above_source_content(self) -> None:
        self.window.show()
        QApplication.processEvents()

        before_row_y = self.window.source_row.geometry().y()
        before_preview_top = self.window.source_preview_card.mapTo(
            self.window.main_page,
            self.window.source_preview_card.rect().topLeft(),
        ).y()

        self.window._set_source_feedback(
            "Formats are ready. Choose options and start the download.",
            tone="success",
        )
        QApplication.processEvents()

        feedback_top = self.window.source_feedback_label.mapTo(
            self.window.main_page,
            self.window.source_feedback_label.rect().topLeft(),
        ).y()
        feedback_bottom = self.window.source_feedback_label.mapTo(
            self.window.main_page,
            self.window.source_feedback_label.rect().bottomLeft(),
        ).y()
        preview_top = self.window.source_preview_card.mapTo(
            self.window.main_page,
            self.window.source_preview_card.rect().topLeft(),
        ).y()

        self.assertEqual(self.window.source_row.geometry().y(), before_row_y)
        self.assertGreater(
            preview_top,
            before_preview_top,
        )
        self.assertTrue(self.window.source_feedback_label.isVisible())
        self.assertFalse(self.window.source_feedback_toast.isVisible())
        self.assertGreater(feedback_top, self.window.source_row.geometry().bottom())
        self.assertLess(feedback_bottom, preview_top)

    def test_about_dialog_uses_app_metadata(self) -> None:
        with patch.object(self.window._effects.dialogs, "information") as info_mock:
            self.window._show_about_dialog()

        info_mock.assert_called_once()
        _parent, title, message = info_mock.call_args.args
        self.assertIn(APP_DISPLAY_NAME, title)
        self.assertIn(APP_DISPLAY_NAME, message)
        self.assertIn(APP_VERSION, message)

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

    def test_open_folder_after_download_prefers_latest_output_folder(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            target = Path(output_dir) / "video.mp4"
            target.write_text("x", encoding="utf-8")
            self.window.open_folder_after_download_check.setChecked(True)
            self.window._set_output_dir_text("/tmp/other-folder")
            self.window._set_last_output_path(target)

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

    def test_responsive_output_cards_reflow_on_resize(self) -> None:
        self.window.show()
        QApplication.processEvents()

        self.window.resize(1180, 900)
        QApplication.processEvents()
        self.assertEqual(
            self.window.workspace_layout.direction(),
            QBoxLayout.Direction.LeftToRight,
        )
        self.assertLess(
            self.window.output_layout.indexOf(self.window.format_card),
            self.window.output_layout.indexOf(self.window.save_card),
        )
        self.assertEqual(
            self.window.folder_row_layout.direction(),
            QBoxLayout.Direction.TopToBottom,
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
        self.assertLess(
            self.window.output_layout.indexOf(self.window.format_card),
            self.window.output_layout.indexOf(self.window.save_card),
        )
        self.assertEqual(
            self.window.folder_row_layout.direction(),
            QBoxLayout.Direction.TopToBottom,
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

        self.assertFalse(self.window.format_combo.isVisible())
        for label, field in (
            (self.window.content_type_label, self.window.video_radio),
            (self.window.content_type_label, self.window.audio_radio),
            (self.window.container_label, self.window.container_combo),
            (self.window.codec_label, self.window.codec_combo),
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
        overlap = map_rect_to_output(self.window.codec_label).intersected(
            map_rect_to_output(self.window.format_combo)
        )
        self.assertFalse(
            overlap.width() > 2 and overlap.height() > 2,
            "Codec label overlaps the quality picker after quality options load",
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
        widths = (1000, 1100, 1180, 1320, 1500, 1700)
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

    def test_downloads_page_is_not_wrapped_in_scroll_area(self) -> None:
        self.assertIs(self.window.panel_stack.widget(self.window._main_page_index), self.window.main_page)
        self.assertNotIsInstance(self.window.main_page, QScrollArea)
        self.assertEqual(self.window.main_page.findChildren(QScrollArea), [])

    def test_min_window_downloads_view_fits_without_vertical_scroll(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(900, 760)
        QApplication.processEvents()

        run_section = self.window.main_page.findChild(QWidget, "runSection")
        self.assertIsNotNone(run_section)
        assert run_section is not None

        bottom = run_section.mapTo(self.window.main_page, run_section.rect().bottomLeft()).y()
        self.assertLessEqual(
            bottom,
            self.window.main_page.height() + 2,
            "Downloads view should fit inside the minimum window height",
        )

    def test_output_dir_field_resets_to_start_of_path(self) -> None:
        path = "/Users/harshakrishnaswamy/Downloads/example/folder"

        self.window._set_output_dir_text(path)

        self.assertEqual(
            self.window.output_dir_edit.text(),
            "~/Downloads/example/folder",
        )
        self.assertEqual(self.window.output_dir_edit.toolTip(), path)
        self.assertEqual(self.window.output_dir_edit.cursorPosition(), 0)

    def test_min_width_save_card_keeps_output_folder_controls_clear_and_roomy(self) -> None:
        self.window.show()
        QApplication.processEvents()
        self.window.resize(1180, 900)
        QApplication.processEvents()

        save_rect = self.window.save_card.rect().adjusted(0, 0, -1, -1)
        output_rect = QRect(
            self.window.output_dir_edit.mapTo(
                self.window.save_card, self.window.output_dir_edit.rect().topLeft()
            ),
            self.window.output_dir_edit.mapTo(
                self.window.save_card, self.window.output_dir_edit.rect().bottomRight()
            ),
        ).normalized()
        browse_rect = QRect(
            self.window.browse_button.mapTo(
                self.window.save_card, self.window.browse_button.rect().topLeft()
            ),
            self.window.browse_button.mapTo(
                self.window.save_card, self.window.browse_button.rect().bottomRight()
            ),
        ).normalized()

        self.assertTrue(save_rect.contains(output_rect))
        self.assertTrue(save_rect.contains(browse_rect))
        overlap = output_rect.intersected(browse_rect)
        self.assertFalse(
            overlap.width() > 2 and overlap.height() > 2,
            "Output folder field overlaps the browse button in the save card",
        )
        self.assertGreater(
            browse_rect.top(),
            output_rect.bottom(),
            "Browse button should sit below the output folder field in the stacked save layout",
        )
        self.assertGreaterEqual(
            self.window.output_dir_edit.width(),
            220,
            "Output folder field should keep enough visible width in the save card",
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
            self.window.history_button,
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
        self.assertTrue(self.window.downloads_button.isVisible())
        self.assertFalse(self.window.queue_button.isVisible())
        self.assertFalse(self.window.history_button.isVisible())
        self.assertTrue(self.window.logs_button.isVisible())
        self.assertTrue(self.window.settings_button.isVisible())

        x_positions = {
            button.text(): button.mapTo(
                self.window.top_actions, button.rect().topLeft()
            ).x()
            for button in buttons
            if button.isVisible()
        }
        settings_x = x_positions["Settings"]
        self.assertGreater(settings_x, x_positions["Downloads"])
        self.assertGreater(settings_x, x_positions["Logs"])

    def test_downloads_button_returns_to_main_view(self) -> None:
        self.window._open_panel("queue")
        self.assertEqual(self.window._active_panel_name, "queue")
        self.window.downloads_button.click()
        QApplication.processEvents()

        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(self.window.panel_stack.currentIndex(), self.window._main_page_index)
        self.assertTrue(self.window.downloads_button.isChecked())

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

    def test_panel_switch_uses_smoother_fade_timing(self) -> None:
        self.window._open_panel("queue")

        self.assertTrue(self.window._active_animations)
        animation = self.window._active_animations[-1]
        self.assertEqual(animation.duration(), PANEL_SWITCH_FADE_MS)
        self.assertEqual(
            animation.easingCurve().type(),
            QEasingCurve.Type.InOutCubic,
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
        self.assertEqual(self.window.source_preview_badge.text(), "URL")
        self.assertEqual(self.window.preview_title_label.text(), "Source preview")

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
        self.assertEqual(self.window.source_preview_badge.text(), "VID")
        self.assertEqual(self.window.preview_title_label.text(), "Video ready")
        self.assertEqual(self.window.preview_value.text(), "Sample")
        self.assertEqual(self.window.source_preview_subtitle.text(), "Example Channel")
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

    def test_download_result_defaults_to_empty_mode(self) -> None:
        self.assertTrue(self.window.download_result_card.isHidden())
        self.assertEqual(
            self.window.download_result_title.text(),
            "No completed download yet.",
        )
        self.assertEqual(self.window.download_result_card.property("state"), "empty")
        self.assertFalse(self.window.copy_output_path_button.isEnabled())
        self.assertEqual(
            self.window.download_result_path.text(),
            "Files will appear here after a download finishes.",
        )

    def test_record_output_updates_latest_download_card(self) -> None:
        output_path = Path("/tmp/test-video.mp4")

        self.window._record_download_output(output_path, "https://example.com/video")

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(
            self.window.download_result_title.text(),
            "Latest completed download",
        )
        self.assertEqual(self.window.download_result_card.property("state"), "ready")
        self.assertTrue(self.window.download_result_path.text().endswith(".mp4"))
        self.assertEqual(
            self.window.download_result_path.toolTip(),
            str(output_path),
        )
        self.assertTrue(self.window.copy_output_path_button.isEnabled())

    def test_record_output_while_downloading_keeps_latest_output_available(self) -> None:
        output_path = Path("/tmp/test-video.mp4")
        self.window._is_downloading = True
        self.window._update_controls_state()

        self.window._record_download_output(output_path, "https://example.com/video")

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(
            self.window.download_result_title.text(),
            "Latest completed download",
        )
        self.assertEqual(self.window.download_result_card.property("state"), "ready")
        self.assertTrue(self.window.copy_output_path_button.isEnabled())
        self.assertEqual(self.window.download_result_path.toolTip(), str(output_path))

        self.window._on_download_done(download.DOWNLOAD_SUCCESS)

        self.assertFalse(self.window.download_result_card.isHidden())
        self.assertEqual(
            self.window.download_result_title.text(),
            "Latest completed download",
        )
        self.assertEqual(self.window.download_result_card.property("state"), "ready")
        self.assertTrue(self.window.copy_output_path_button.isEnabled())

    def test_clearing_latest_output_resets_download_card(self) -> None:
        output_path = Path("/tmp/test-video.mp4")
        self.window._record_download_output(output_path, "https://example.com/video")
        self.assertFalse(self.window.download_result_card.isHidden())

        self.window._clear_last_output_path()

        self.assertTrue(self.window.download_result_card.isHidden())
        self.assertEqual(
            self.window.download_result_title.text(),
            "No completed download yet.",
        )
        self.assertEqual(self.window.download_result_card.property("state"), "empty")
        self.assertEqual(
            self.window.download_result_path.text(),
            "Files will appear here after a download finishes.",
        )
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
        self.assertTrue(self.window.item_label.text().endswith("..."))

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
