import threading
import unittest
from unittest.mock import patch

from gui.core.format_selection import queue_format_selector
from gui.services import app_service
from gui.common.yt_dlp_cli import MetadataCancelled


class TestQueueSelectors(unittest.TestCase):
    def test_selected_video_has_codec_container_and_general_fallbacks(self):
        selector = queue_format_selector(mode="video", container="mp4", codec="avc1",
                                         info={"format_id": "137", "acodec": "none"})
        self.assertTrue(selector.startswith("137+bestaudio/"))
        self.assertIn("bestvideo[ext=mp4][vcodec~='^(avc1|h264)']+bestaudio", selector)
        self.assertIn("/bestvideo[ext=mp4]+bestaudio/", selector)
        self.assertTrue(selector.endswith("/bestvideo+bestaudio/best"))

    def test_muxed_and_audio_streams_do_not_add_audio(self):
        self.assertTrue(queue_format_selector(mode="video", container="mp4", codec="avc1",
                                              info={"format_id": "22", "acodec": "aac"}).startswith("22/"))
        self.assertEqual(queue_format_selector(mode="audio", container="mp3", codec="",
                                              info={"format_id": "140"}), "140/bestaudio/best")

    def test_unknown_formats_keep_metadata_resolution(self):
        for info in ({}, {"format_id": "unsafe/[id]"}, {"custom_format": "unknown"}):
            self.assertIsNone(queue_format_selector(mode="video", container="mp4", codec="avc1", info=info))

    def test_fast_queue_resolution_never_fetches_metadata(self):
        with patch.object(app_service.helpers, "fetch_info") as fetch:
            result = app_service.resolve_format_for_url(
                url="https://example.com/video", settings={"format_selector": "140/bestaudio/best",
                "mode": "audio", "format_filter": "m4a"}, log=lambda _: None,
            )
        fetch.assert_not_called()
        self.assertTrue(result["fmt_info"]["is_audio_only"])
        self.assertFalse(result["is_playlist"])

    def test_fast_resolution_still_honors_cancel(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(MetadataCancelled):
            app_service.resolve_format_for_url(url="test", settings={"format_selector": "best"},
                                               log=lambda _: None, cancel_event=event)
