import unittest
from pathlib import Path

from gui.core import download_plan


class TestCoreDownloadPlan(unittest.TestCase):
    def test_normalize_playlist_items(self) -> None:
        value, changed = download_plan.normalize_playlist_items("1, 2, 5-7")
        self.assertEqual(value, "1,2,5-7")
        self.assertTrue(changed)

        value, changed = download_plan.normalize_playlist_items("")
        self.assertIsNone(value)
        self.assertFalse(changed)

    def test_build_single_download_request_disables_playlist_items_when_disabled(self) -> None:
        request = download_plan.build_single_download_request(
            url="https://example.com/watch?v=1",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22"},
            fmt_label="Video",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items_raw="1-5",
            options={
                "network_timeout_s": 20,
                "network_retries": 1,
                "retry_backoff_s": 1.5,
                "subtitle_languages": ["en"],
                "write_subtitles": True,
                "embed_subtitles": False,
                "audio_language": "en",
                "custom_filename": "clip",
            },
        )
        self.assertIsNone(request["playlist_items"])
        self.assertEqual(request["network_retries"], 1)
        self.assertEqual(request["custom_filename"], "clip")

    def test_build_queue_download_request_parses_and_clamps_network_values(self) -> None:
        request = download_plan.build_queue_download_request(
            url="https://example.com/watch?v=1",
            settings={
                "output_dir": "/tmp/custom",
                "playlist_items": "1, 2, 3",
                "convert_to_mp4": True,
                "network_timeout_s": "999",
                "network_retries": "bad",
                "retry_backoff_s": "100",
                "subtitle_languages": "en,es",
                "write_subtitles": True,
                "embed_subtitles": True,
                "audio_language": "es",
                "custom_filename": "Queued Name",
            },
            resolved={
                "fmt_info": {"format_id": "22"},
                "fmt_label": "Video",
                "format_filter": "mp4",
                "is_playlist": True,
            },
            default_output_dir="/tmp/default",
            timeout_default=20,
            retries_default=1,
            backoff_default=1.5,
        )
        self.assertEqual(request["output_dir"], Path("/tmp/custom"))
        self.assertEqual(request["playlist_items"], "1,2,3")
        self.assertEqual(request["network_timeout_s"], 300)
        self.assertEqual(request["network_retries"], 1)
        self.assertEqual(request["retry_backoff_s"], 30.0)
        self.assertEqual(request["subtitle_languages"], ["en", "es"])


if __name__ == "__main__":
    unittest.main()
