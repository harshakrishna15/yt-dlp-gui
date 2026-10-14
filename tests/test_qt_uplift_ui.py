"""Regression coverage for the light sidebar UI and focused download flow."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from tests import test_qt_app as f

if f.HAS_QT:
    from PySide6.QtGui import QColor, QFont, QPalette
    from gui.qt import style
    from gui.qt.widgets import ButtonSpec, LineEditSpec, build_button, build_line_edit, QUEUE_STATUS_ROLE


@unittest.skipUnless(f.HAS_QT, "PySide6 is required")
class TestUpliftUi(unittest.TestCase):
    setUp = f.TestQtApp.setUp
    tearDown = f.TestQtApp.tearDown
    _load_ready_preview_with_formats = f.TestQtApp._load_ready_preview_with_formats

    @classmethod
    def setUpClass(cls):
        cls._app = f.QApplication.instance() or f.QApplication([])

    def settle(self):
        for _ in range(5):
            self._app.processEvents()

    def test_initial_flow_exposes_link_entry_and_hides_output_options(self):
        self.window.show()
        self.settle()
        self.assertTrue(self.window.source_hint.isVisible())
        self.assertTrue(self.window.url_edit.isVisible())
        self.assertFalse(self.window.format_combo.isVisible())
        self.assertFalse(self.window.start_button.isVisible())
        self.window.url_edit.setText("https://example.test/video")
        self.assertTrue(self.window.analyze_button.isEnabled())
        self.assertFalse(self.window.format_combo.isVisible())
        self._load_ready_preview_with_formats()
        self.settle()
        self.assertTrue(self.window.format_combo.isVisible())
        self.assertTrue(self.window.start_button.isVisible())
        self.assertFalse(self.window.source_hint.isVisible())

    def test_link_change_clears_media_and_moves_focus_out_of_hidden_options(self):
        self._load_ready_preview_with_formats()
        self.window.show()
        self.settle()
        self.window.format_combo.setFocus(f.Qt.FocusReason.TabFocusReason)
        self.assertTrue(self.window.format_combo.hasFocus())
        self.window.url_edit.setText("https://example.test/changed")
        self.settle()
        self.assertTrue(self.window.url_edit.hasFocus())
        self.assertFalse(self.window.format_card.isVisible())
        self.assertFalse(self.window.media_summary.isVisible())
        self.assertFalse(self.window.run_actions_card.isVisible())

    def test_paired_options_and_labels_stay_aligned_across_sizes(self):
        self._load_ready_preview_with_formats()
        self.window.show()
        for width, height in ((900, 610), (1200, 800), (1800, 1000)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.settle()
                mode = self.window.video_radio.parentWidget()
                quality = self.window.format_combo
                self.assertLessEqual(abs(mode.mapToGlobal(f.QPoint()).y() - quality.mapToGlobal(f.QPoint()).y()), 2)
                self.assertLess(mode.mapToGlobal(mode.rect().topRight()).x(), quality.mapToGlobal(f.QPoint()).x())
                for label, control in ((self.window.content_type_label, mode), (self.window.format_label, quality)):
                    self.assertLess(label.mapToGlobal(label.rect().bottomLeft()).y(), control.mapToGlobal(f.QPoint()).y())
                self.assertEqual(self.window._ui.top_bar.header.width(), style.SIDEBAR_WIDTH)

    def test_feedback_moves_between_inline_source_actions_and_global_context(self):
        self._load_ready_preview_with_formats()
        self.window.show()
        self.window._set_source_feedback("Unable to analyze this link.", tone="error")
        self.settle()
        self.assertTrue(self.window.main_page.isAncestorOf(self.window.feedback_row))
        self.window._on_add_to_queue()
        self.settle()
        self.assertEqual(self.window.feedback_action_button.text(), "View queue")
        self.assertGreater(self.window.feedback_row.mapToGlobal(f.QPoint()).y(), self.window.start_button.mapToGlobal(f.QPoint()).y())
        self.window.feedback_action_button.click()
        self.settle()
        self.assertEqual(self.window._active_panel_name, "queue")
        self.assertIs(self.window.feedback_row.parentWidget(), self.window.content_column)
        self.assertTrue(self.window.feedback_row.isVisible())

    def test_sidebar_and_activity_stay_fixed_while_advanced_scrolls(self):
        self._load_ready_preview_with_formats()
        self.window.show()
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}):
            self.window.advanced_toggle.setChecked(True)
        self.window._is_downloading = True
        self.window._update_controls_state()
        self.settle()
        sidebar = self.window._ui.top_bar.header.geometry()
        activity = self.window.metrics_card.geometry()
        self.window.form_scroll.verticalScrollBar().setValue(self.window.form_scroll.verticalScrollBar().maximum())
        self.settle()
        self.assertEqual(self.window._ui.top_bar.header.geometry(), sidebar)
        self.assertEqual(self.window.metrics_card.geometry(), activity)
        self.assertGreaterEqual(self.window.format_combo.height(), style.CONTROL_HEIGHT)
        self.assertTrue(self.window.cancel_button.isVisible())
        self.window._is_downloading = False

    def test_native_palette_and_status_roles_remain_legible(self):
        palette = self.window.palette()
        self.assertEqual(palette.color(QPalette.ColorRole.Base).name(), "#ffffff")
        self.assertEqual(palette.color(QPalette.ColorRole.Text).name(), style._PALETTE["text_primary"])
        self.window.queue_items = [{"url": status, "status": status} for status in ("queued", "failed", "completed", "cancelled")]
        self.window._refresh_queue_panel()
        self.assertEqual([self.window.queue_list.item(i).data(QUEUE_STATUS_ROLE) for i in range(4)],
                         ["queued", "failed", "completed", "cancelled"])

    def test_reduced_motion_applies_download_progress_immediately(self):
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}):
            self.window._animate_progress_bar_to(42.3)
        self.assertEqual(self.window.progress_bar.value(), 423)
        self.assertIsNone(self.window._progress_anim)

    def test_control_variants_and_increased_font_metrics_do_not_shrink_controls(self):
        self._load_ready_preview_with_formats()
        self.window.show()
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}):
            self.window.advanced_toggle.setChecked(True)
        self.settle()
        button = build_button(self.window, spec=ButtonSpec("Analyze", sizing="url"))
        entry = build_line_edit(self.window, spec=LineEditSpec(sizing="url"))
        inline = build_button(self.window, spec=ButtonSpec("Edit", sizing="inline"))
        self.assertEqual(button.minimumHeight(), 44)
        self.assertEqual(entry.minimumHeight(), 44)
        self.assertEqual(inline.minimumHeight(), 32)
        button.deleteLater()
        entry.deleteLater()
        inline.deleteLater()
        for control in (self.window.filename_edit, self.window.url_edit, self.window.analyze_button):
            control.setStyleSheet("font-size: 28px;")
            control.ensurePolished()
        self.window._normalize_control_sizing()
        self.settle()
        self.assertEqual(self.window.filename_edit.font().pixelSize(), 28)
        self.assertGreaterEqual(self.window.filename_edit.height(), self.window.filename_edit.fontMetrics().height() + 16)
        self.assertGreaterEqual(self.window.analyze_button.height(), self.window.filename_edit.height())
        for control in (self.window.url_edit, self.window.analyze_button, self.window.filename_edit):
            self.assertTrue(control.parentWidget().rect().contains(control.geometry()), control.objectName())

    def test_light_text_and_field_boundaries_have_sufficient_contrast(self):
        def luminance(value):
            c = QColor(value)
            channels = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                        for v in (c.redF(), c.greenF(), c.blueF())]
            return sum(v * weight for v, weight in zip(channels, (.2126, .7152, .0722)))
        def contrast(a, b):
            hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
            return (hi + .05) / (lo + .05)
        for key in ("text_primary", "text_muted", "text_label", "accent_text", "destructive"):
            self.assertGreaterEqual(contrast(style._PALETTE[key], "#ffffff"), 4.5, key)
        self.assertGreaterEqual(contrast(style._PALETTE["border"], "#ffffff"), 3)
