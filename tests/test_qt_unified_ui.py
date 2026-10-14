"""Behavior and layout coverage for the shared UI and independent queue runs."""
import os
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from tests import test_qt_app as fixtures
from tests import test_qt_controllers as controller_fixtures
from gui.qt.controllers import RunQueueController, RunQueueState


@unittest.skipUnless(fixtures.HAS_QT, "PySide6 is required")
class TestUnifiedUi(unittest.TestCase):
    setUp = fixtures.TestQtApp.setUp
    tearDown = fixtures.TestQtApp.tearDown
    _load_ready_preview_with_formats = fixtures.TestQtApp._load_ready_preview_with_formats

    @classmethod
    def setUpClass(cls):
        cls._app = fixtures.QApplication.instance() or fixtures.QApplication([])

    def show(self):
        self.window.show()
        for _ in range(4):
            self._app.processEvents()

    def test_forms_center_and_cap_width(self):
        self.show()
        for width, height in ((900, 610), (1200, 800), (1800, 1000)):
            self.window.resize(width, height)
            for _ in range(4):
                self._app.processEvents()
            form = self.window.main_page
            viewport = self.window.form_scroll.viewport()
            self.assertLessEqual(form.width(), 760)
            self.assertGreaterEqual(form.width(), min(760, viewport.width()) - 2)
            self.assertLessEqual(abs(form.mapTo(viewport, fixtures.QPoint()).x() * 2 + form.width() - viewport.width()), 2)

    def test_advanced_scrolls_without_growing_window_or_controls(self):
        self._load_ready_preview_with_formats()
        self.show()
        before = self.window.size()
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}):
            self.window.advanced_toggle.setChecked(True)
        self.window._is_downloading = True
        self.window._set_metrics_visible(True)
        self.window._update_controls_state()
        for _ in range(5):
            self._app.processEvents()
        self.assertEqual(self.window.size(), before)
        self.assertGreater(self.window.form_scroll.verticalScrollBar().maximum(), 0)
        self.assertGreaterEqual(self.window.format_combo.height(), 36)
        self.assertFalse(self.window.main_page.isAncestorOf(self.window.metrics_card))

    def test_visible_buttons_fit_their_containers_in_every_panel(self):
        self.show()
        self.window._set_source_feedback("Unable to download this video. Try another link.", tone="error")
        for panel in (None, "queue", "settings", "logs"):
            self.window._open_panel(panel) if panel else self.window._show_main_workspace()
            if panel == "settings":
                self.window.yt_dlp_update_status.show()
                self.window.yt_dlp_update_details_button.show()
            for _ in range(5):
                self._app.processEvents()
            for button in self.window.findChildren(fixtures.QPushButton):
                if not button.isVisible():
                    continue
                parent = button.parentWidget()
                rect = fixtures.QRect(button.mapTo(parent, fixtures.QPoint()), button.size())
                with self.subTest(panel=panel, button=button.text() or button.accessibleName()):
                    self.assertTrue(parent.rect().contains(rect),
                        f"{button.text()} {rect.getRect()} outside {parent.objectName()} {parent.rect().getRect()}")

    def test_metadata_clears_with_link_and_omits_missing_values(self):
        self._load_ready_preview_with_formats()
        self.assertFalse(self.window.media_summary.isHidden())
        self.assertIn("Example Channel", self.window.media_detail._full_text)
        self.assertIn("5m 42s", self.window.media_detail._full_text)
        self.window._set_source_summary(None)
        self.assertTrue(self.window.media_detail.isHidden())
        self.window.url_edit.setText("https://example.com/next")
        self.assertTrue(self.window.media_summary.isHidden())
        self.assertEqual(self.window.media_title._full_text, "")

    def test_download_needs_current_link_even_with_pending_queue(self):
        self.window.queue_items = [{"url": "queued", "status": "queued"}]
        self.window._refresh_queue_panel()
        self.window._update_controls_state()
        self.assertFalse(self.window.start_button.isEnabled())
        self.assertTrue(self.window.queue_start_button.isEnabled())

    def test_queue_start_ignores_completed_results_and_busy_states(self):
        self.window.queue_items = [{"url": "done", "status": "completed"}]
        self.window._refresh_queue_panel()
        self.assertFalse(self.window.queue_start_button.isEnabled())
        self.window.queue_items.append({"url": "failed", "status": "failed"})
        for busy in ("_is_fetching", "_is_downloading", "_yt_dlp_update_in_progress", "_tool_checks_pending"):
            setattr(self.window, busy, True)
            self.window._refresh_queue_panel_state()
            self.assertFalse(self.window.queue_start_button.isEnabled(), busy)
            setattr(self.window, busy, False)

    def test_clear_undo_restores_complete_snapshot_and_survives_navigation(self):
        original = [{"url": "one", "title": "One", "settings": {"output_dir": "/tmp"}},
                    {"url": "two", "status": "completed", "output_path": "/tmp/two.mp4"}]
        self.window.queue_items = deepcopy(original)
        controller = self.window._run_queue_controller
        controller.on_queue_clear()
        self.assertEqual(self.window.queue_items, [])
        self.assertFalse(self.window.queue_undo_row.isHidden())
        self.window._open_panel("settings")
        self.window._open_panel("queue")
        controller.undo_queue_clear()
        self.assertEqual(self.window.queue_items, original)
        self.assertTrue(self.window.queue_undo_row.isHidden())

    def test_add_invalidates_undo_and_offers_view_queue_without_navigation(self):
        self._load_ready_preview_with_formats(queue_ready=True)
        self.window._run_queue_controller.on_queue_clear()
        self.window._on_add_to_queue()
        self.assertIsNone(self.window._run_queue_state.cleared_queue)
        self.assertIsNone(self.window._active_panel_name)
        self.assertEqual(self.window._feedback_action, "queue")
        self.assertEqual(self.window.feedback_action_button.text(), "View queue")
        self.window._activate_feedback_action()
        self.assertEqual(self.window._active_panel_name, "queue")

    def test_empty_queue_has_navigation_and_hides_bulk_actions(self):
        self.window._open_panel("queue")
        self.assertTrue(self.window.queue_clear_button.isHidden())
        self.assertTrue(self.window.queue_retry_button.isHidden())
        button = next(b for b in self.window.queue_empty_state.findChildren(fixtures.QPushButton) if b.text() == "Go to Downloads")
        button.click()
        self.assertIsNone(self.window._active_panel_name)

    def test_activity_and_cancel_work_across_all_screens(self):
        self.show()
        for panel in (None, "queue", "settings", "logs"):
            self.window._is_downloading = True
            self.window._cancel_requested = False
            self.window._set_metrics_visible(True)
            self.window._open_panel(panel) if panel else self.window._show_main_workspace()
            self.window._update_controls_state()
            self.assertTrue(self.window.metrics_card.isVisible())
            self.assertTrue(self.window.cancel_button.isVisible())
            self.window.cancel_button.click()
            self.assertTrue(self.window._cancel_requested)
            self.assertFalse(self.window.cancel_button.isEnabled())
        self.window._is_downloading = False

    def test_unknown_progress_is_indeterminate_and_unknown_metrics_hidden(self):
        self.window._is_downloading = True
        self.window._on_progress_update({"status": "downloading", "percent": None, "speed": "", "eta": ""})
        self.assertEqual(self.window.progress_bar.maximum(), 0)
        self.assertTrue(self.window.speed_label.isHidden())
        self.assertTrue(self.window.eta_label.isHidden())
        self.window._on_progress_update({"status": "downloading", "percent": 10, "speed": "2 MiB/s", "eta": "00:20"})
        self.assertEqual(self.window.progress_bar.maximum(), 1000)
        self.assertFalse(self.window.speed_label.isHidden())
        self.window._is_downloading = False

    def test_processing_stage_survives_resize_and_elides_long_messages(self):
        self.show()
        self.window._is_downloading = True
        self.window._set_metrics_visible(True)
        self.window._set_current_item_display(progress="1/3", title="Example video")
        message = "Preparing media: " + "long-processing-detail" * 80
        self.window._on_progress_update({"status": "preparing", "message": message})
        self.window.resize(1200, 800)
        for _ in range(4):
            self._app.processEvents()
        self.assertEqual(self.window.item_label.toolTip(), message)
        self.assertTrue(self.window.item_label.text().startswith("Preparing media:"))
        self.assertLessEqual(self.window.item_label.fontMetrics().horizontalAdvance(self.window.item_label.text()), self.window.item_label.width())
        self.window._on_progress_update({"status": "downloading", "percent": 10})
        self.assertIn("Example video", self.window.item_label.text())
        self.window._is_downloading = False

    def test_subset_progress_excludes_retained_completed_items(self):
        self.window.queue_items = [{"url": str(i)} for i in range(5)]
        self.window.queue_active = True
        self.window.queue_index = 3
        self.window._run_queue_state.run_indices = [1, 3]
        self.assertEqual(self.window._queue_overall_progress_percent(50), 75)
        self.window.queue_active = False

    def test_selected_queue_row_exposes_keyboard_actions(self):
        self.window.queue_items = [{"url": "one", "title": "One"}]
        self.window._refresh_queue_panel()
        self.window._open_panel("queue")
        self.show()
        self.window.queue_list.setCurrentRow(0)
        edit = self.window.queue_list._row_buttons["edit"]
        remove = self.window.queue_list._row_buttons["remove"]
        self.assertTrue(edit.isVisible())
        self.assertEqual(edit.accessibleName(), "Edit: One")
        self.assertEqual(remove.accessibleName(), "Remove: One")
        remove.setFocus(fixtures.Qt.FocusReason.TabFocusReason)
        self.assertTrue(remove.hasFocus())
        fixtures.QTest.keyClick(remove, fixtures.Qt.Key.Key_Space)
        self.assertEqual(self.window.queue_items, [])


class TestIndependentQueueRuns(unittest.TestCase):
    def controller(self, items):
        state = RunQueueState(queue_items=items)
        window = controller_fixtures.FakeWindow()
        executor = controller_fixtures.FakeExecutor()
        ports, *_ = controller_fixtures.build_ports(executor=executor)
        return RunQueueController(window, state=state, ports=ports), state, window, executor

    def test_queue_skips_completed_and_numbers_only_selected_items(self):
        settings = {"mode": "audio", "format_filter": "mp3", "format_label": "High"}
        items = [{"url": "done", "settings": {}, "status": "completed", "output_path": "/tmp/done.mp3"}]
        items += [{"url": status, "settings": settings.copy(), "status": status} for status in ("queued", "failed", "cancelled")]
        controller, state, window, executor = self.controller(items)
        controller.start_queue_download()
        for _ in range(3):
            controller.on_queue_item_done(False, False)
        self.assertFalse(state.queue_active)
        self.assertEqual([c[2]["url"] for c in executor.calls], ["queued", "failed", "cancelled"])
        self.assertEqual([c[2]["index"] for c in executor.calls], [1, 2, 3])
        self.assertEqual([c[2]["total"] for c in executor.calls], [3, 3, 3])
        self.assertEqual(state.queue_items[0]["output_path"], "/tmp/done.mp3")

    def test_single_start_preserves_queue_and_invalidates_undo(self):
        controller, state, window, executor = self.controller([{"url": "queued"}])
        state.cleared_queue = [{"url": "old"}]
        window.url_edit.setText("https://example.com/current")
        window._filtered_lookup = {"Best": {"format_id": "x"}}
        with patch("gui.qt.controllers.app_service.build_single_download_request", return_value=({"output_dir": Path("/tmp"), "playlist_enabled": False}, False)):
            controller.on_start()
        self.assertFalse(state.queue_active)
        self.assertTrue(state.is_downloading)
        self.assertEqual(state.queue_items, [{"url": "queued"}])
        self.assertIsNone(state.cleared_queue)
        self.assertEqual(executor.calls[0][0], controller.run_single_download_worker)
