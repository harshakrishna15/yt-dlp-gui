import unittest

from gui.core import queue_presentation


class TestQueuePresentation(unittest.TestCase):
    def test_queue_list_entry_prefers_stored_title_and_settings_summary(self) -> None:
        entry = queue_presentation.build_queue_list_entry(
            {
                "url": "https://www.youtube.com/watch?v=abc123",
                "title": "Stored title",
                "settings": {
                    "mode": "video",
                    "format_filter": "mp4",
                    "codec_filter": "avc1",
                    "format_label": "1080p",
                    "custom_filename": "edited-name",
                },
            },
            idx=1,
            active=False,
        )

        self.assertEqual(entry.title, "Stored title")
        self.assertEqual(
            entry.meta,
            "Video · MP4 · AVC1 · 1080p · Save as edited-name",
        )
        self.assertIn("https://www.youtube.com/watch?v=abc123", entry.tooltip)

    def test_queue_summary_entry_prefers_current_preview_title(self) -> None:
        item = {
            "url": "https://www.youtube.com/watch?v=abc123",
            "settings": {
                "mode": "video",
                "format_filter": "mp4",
                "format_label": "1080p",
            },
        }

        entry = queue_presentation.build_queue_summary_entry(
            item,
            idx=1,
            active=False,
            context=queue_presentation.QueueSummaryContext(
                current_url="https://www.youtube.com/watch?v=abc123",
                current_preview_title="Sample video",
            ),
        )

        self.assertEqual(entry.badge_text, "VID")
        self.assertEqual(entry.title, "Sample video")
        self.assertEqual(entry.meta, "MP4 · 1080p · Video & audio")
        self.assertEqual(
            entry.list_text,
            "1. https://www.youtube.com/watch?v=abc123 [video/mp4/-] 1080p",
        )

    def test_active_queue_summary_entry_uses_progress_metrics(self) -> None:
        item = {
            "url": "https://www.youtube.com/watch?v=abc123",
            "settings": {
                "mode": "video",
                "format_filter": "mp4",
                "codec_filter": "avc1",
                "format_label": "1080p",
            },
        }

        entry = queue_presentation.build_queue_summary_entry(
            item,
            idx=2,
            active=True,
            context=queue_presentation.QueueSummaryContext(
                current_item_title="Current download title",
                progress_text="Progress: 25.0%",
                speed_text="Speed: 3.5 MiB/s",
                eta_text="ETA: 00:09",
            ),
        )

        self.assertEqual(entry.title, "Current download title")
        self.assertEqual(
            entry.meta,
            "25.0% · 3.5 MiB/s · ETA 00:09 · MP4 · 1080p",
        )
        self.assertEqual(entry.status_text, "Downloading")
        self.assertEqual(entry.tone, "active")
        self.assertEqual(
            entry.list_text,
            "> 2. https://www.youtube.com/watch?v=abc123 [video/mp4/avc1] 1080p",
        )

    def test_queue_summary_entry_falls_back_to_url_title(self) -> None:
        entry = queue_presentation.build_queue_summary_entry(
            {"url": "https://www.youtube.com/watch?v=abc123"},
            idx=1,
            active=False,
        )

        self.assertEqual(entry.title, "youtube.com · abc123")
        self.assertEqual(entry.meta, "Video & audio")

    def test_queue_summary_entry_prefers_stored_title(self) -> None:
        entry = queue_presentation.build_queue_summary_entry(
            {
                "url": "https://www.youtube.com/watch?v=abc123",
                "title": "Stored title",
                "settings": {"mode": "video"},
            },
            idx=1,
            active=False,
        )

        self.assertEqual(entry.title, "Stored title")

    def test_metric_value_uses_prefix_and_fallback(self) -> None:
        self.assertEqual(
            queue_presentation.metric_value("Progress: 25%", "Progress:"),
            "25%",
        )
        self.assertEqual(
            queue_presentation.metric_value("Progress: -", "Progress:", fallback="n/a"),
            "n/a",
        )
        self.assertEqual(
            queue_presentation.metric_value("Speed: 1 MiB/s", "Progress:", fallback=""),
            "",
        )

    def test_queue_summary_entry_fallbacks_for_missing_data(self) -> None:
        entry = queue_presentation.build_queue_summary_entry(
            {"url": "", "settings": {"mode": "other"}},
            idx=3,
            active=False,
        )
        self.assertEqual(entry.badge_text, "URL")
        self.assertEqual(entry.title, "Queued item")
        self.assertEqual(entry.meta, "Video & audio")


if __name__ == "__main__":
    unittest.main()
