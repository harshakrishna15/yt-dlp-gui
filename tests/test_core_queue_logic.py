import unittest

from gui.core import queue_logic


class TestCoreQueueLogic(unittest.TestCase):
    def test_queue_settings_issue(self) -> None:
        self.assertEqual(queue_logic.queue_settings_issue({}), "mode")
        self.assertEqual(
            queue_logic.queue_settings_issue(
                {"mode": "video", "format_filter": "mp4", "format_label": "x"}
            ),
            "codec",
        )
        self.assertEqual(
            queue_logic.queue_settings_issue(
                {"mode": "audio", "format_filter": "", "format_label": "x"}
            ),
            "container",
        )
        self.assertEqual(
            queue_logic.queue_settings_issue(
                {"mode": "audio", "format_filter": "mp3", "format_label": ""}
            ),
            "format",
        )
        self.assertIsNone(
            queue_logic.queue_settings_issue(
                {
                    "mode": "video",
                    "codec_filter": "avc1",
                    "format_filter": "mp4",
                    "format_label": "x",
                }
            )
        )

    def test_first_invalid_queue_item(self) -> None:
        items = [
            {"url": "a", "settings": {"mode": "audio", "format_filter": "mp3", "format_label": "x"}},
            {"url": "b", "settings": {"mode": "video", "format_filter": "mp4", "format_label": "x"}},
        ]
        self.assertEqual(queue_logic.first_invalid_queue_item(items), (2, "codec"))

    def test_next_non_empty_queue_index(self) -> None:
        items = [
            {"url": " "},
            {"url": ""},
            {"url": "https://example.com/watch?v=1"},
        ]
        self.assertEqual(queue_logic.next_non_empty_queue_index(items, 0), 2)
        self.assertIsNone(queue_logic.next_non_empty_queue_index(items, 3))

    def test_queue_messages(self) -> None:
        status, log = queue_logic.queue_add_feedback("codec")
        self.assertIn("codec", status.lower())
        self.assertIn("codec", log.lower())
        self.assertEqual(queue_logic.queue_start_missing_detail("mode"), "audio/video mode")

    def test_queue_add_issue_checks_preconditions_before_settings(self) -> None:
        issue = queue_logic.queue_add_issue(
            url="",
            playlist_mode=False,
            formats_loaded=True,
            settings={},
        )
        self.assertEqual(issue, "missing_url")

        issue = queue_logic.queue_add_issue(
            url="https://example.com/watch?v=1",
            playlist_mode=True,
            formats_loaded=True,
            settings={},
        )
        self.assertEqual(issue, "playlist")

        issue = queue_logic.queue_add_issue(
            url="https://example.com/watch?v=1",
            playlist_mode=False,
            formats_loaded=False,
            settings={},
        )
        self.assertEqual(issue, "formats")

        issue = queue_logic.queue_add_issue(
            url="https://example.com/watch?v=1",
            playlist_mode=False,
            formats_loaded=True,
            settings={"mode": "audio", "format_filter": "mp3", "format_label": "x"},
        )
        self.assertIsNone(issue)


if __name__ == "__main__":
    unittest.main()
