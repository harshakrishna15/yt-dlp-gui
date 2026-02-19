import unittest

from gui.core import workflow


class TestCoreWorkflow(unittest.TestCase):
    def test_single_start_issue_and_message(self) -> None:
        self.assertEqual(
            workflow.single_start_issue(url="", formats_loaded=True),
            "missing_url",
        )
        self.assertEqual(
            workflow.single_start_issue(url="https://example.com", formats_loaded=False),
            "formats_unavailable",
        )
        self.assertIsNone(
            workflow.single_start_issue(url="https://example.com", formats_loaded=True)
        )
        title, message = workflow.single_start_error_text("missing_url")
        self.assertEqual(title, "Missing URL")
        self.assertIn("paste a video URL", message)

    def test_validate_queue_start_reports_invalid_settings(self) -> None:
        check = workflow.validate_queue_start(
            is_downloading=False,
            queue_items=[
                {"url": "https://example.com", "settings": {"mode": ""}},
            ],
        )
        self.assertFalse(check.can_start)
        self.assertEqual(check.invalid_index, 1)
        self.assertEqual(check.invalid_issue, "mode")

    def test_next_queue_run_item_skips_empty_url(self) -> None:
        item = workflow.next_queue_run_item(
            [
                {"url": "", "settings": {}},
                {"url": " https://example.com ", "settings": {"mode": "video"}},
            ],
            0,
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.index, 1)
        self.assertEqual(item.display_index, 2)
        self.assertEqual(item.url, "https://example.com")

    def test_advance_queue_progress_paths(self) -> None:
        keep_going = workflow.advance_queue_progress(
            queue_length=3,
            current_index=0,
            failed_items=0,
            cancel_requested=False,
            had_error=True,
            cancelled=False,
        )
        self.assertFalse(keep_going.should_finish)
        self.assertEqual(keep_going.failed_items, 1)
        self.assertEqual(keep_going.next_index, 1)

        finish_cancelled = workflow.advance_queue_progress(
            queue_length=3,
            current_index=1,
            failed_items=0,
            cancel_requested=False,
            had_error=False,
            cancelled=True,
        )
        self.assertTrue(finish_cancelled.should_finish)
        self.assertTrue(finish_cancelled.finish_cancelled)

        finish_success = workflow.advance_queue_progress(
            queue_length=2,
            current_index=1,
            failed_items=0,
            cancel_requested=False,
            had_error=False,
            cancelled=False,
        )
        self.assertTrue(finish_success.should_finish)
        self.assertFalse(finish_success.finish_cancelled)

    def test_queue_finish_outcome(self) -> None:
        self.assertEqual(
            workflow.queue_finish_outcome(cancelled=True, failed_items=0),
            "cancelled",
        )
        self.assertEqual(
            workflow.queue_finish_outcome(cancelled=False, failed_items=2),
            "failed",
        )
        self.assertEqual(
            workflow.queue_finish_outcome(cancelled=False, failed_items=0),
            "success",
        )


if __name__ == "__main__":
    unittest.main()
