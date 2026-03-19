import unittest

from gui.core import queue_presentation


class TestQueuePresentation(unittest.TestCase):
    def test_queue_preview_defaults(self) -> None:
        model = queue_presentation.build_queue_preview_model(
            queue_presentation.QueuePreviewInputs(
                folder_text="Downloads folder",
            )
        )

        self.assertEqual(model.badge_text, "PLAN")
        self.assertEqual(model.heading_text, "Download plan")
        self.assertEqual(
            model.placeholder_text,
            "Paste a URL to build the next queue item.",
        )
        self.assertEqual(
            model.subtitle_text,
            "Set defaults once, then keep adding items to the queue.",
        )
        self.assertEqual(model.detail_one_text, "Choose mode")
        self.assertEqual(model.detail_two_text, "Downloads folder")
        self.assertEqual(model.detail_three_text, "Queue empty")

    def test_queue_preview_uses_ready_metadata(self) -> None:
        model = queue_presentation.build_queue_preview_model(
            queue_presentation.QueuePreviewInputs(
                url="https://www.youtube.com/watch?v=abc123",
                preview_title="Sample video",
                source_summary={
                    "badge_text": "VID",
                    "subtitle_text": "Example Channel",
                    "detail_two_text": "5m 42s",
                },
                mode="video",
                container="mp4",
                has_filtered_formats=True,
                selected_quality="1080p",
                folder_text="Downloads folder",
                queue_count=3,
            )
        )

        self.assertEqual(model.badge_text, "VID")
        self.assertEqual(model.heading_text, "Ready to queue")
        self.assertEqual(model.subtitle_text, "Example Channel · 5m 42s")
        self.assertEqual(model.detail_one_text, "Video • MP4 • 1080p")
        self.assertEqual(model.detail_two_text, "Downloads folder")
        self.assertEqual(model.detail_three_text, "3 queued items")

    def test_queue_preview_playlist_scope_uses_requested_items(self) -> None:
        model = queue_presentation.build_queue_preview_model(
            queue_presentation.QueuePreviewInputs(
                url="https://www.youtube.com/playlist?list=PL123",
                playlist_mode=True,
                mode="audio",
                container="mp3",
                is_fetching=True,
                folder_text="Podcasts folder",
                playlist_items="1,3-5",
            )
        )

        self.assertEqual(model.badge_text, "LIST")
        self.assertEqual(model.heading_text, "Next queue item")
        self.assertEqual(model.detail_one_text, "Audio • MP3 • Loading formats")
        self.assertEqual(model.detail_three_text, "Items 1,3-5")

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


if __name__ == "__main__":
    unittest.main()
