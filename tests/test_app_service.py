import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from gui.services import app_service


class TestAppService(unittest.TestCase):
    def _build_request(self, output_dir: Path) -> dict[str, object]:
        return {
            "url": "https://example.com/watch?v=abc",
            "output_dir": output_dir,
            "fmt_info": {"format_id": "22"},
            "fmt_label": "1080p",
            "format_filter": "mp4",
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

    @patch("gui.services.app_service.download.run_download", return_value="success")
    def test_run_download_request_ensure_output_dir_toggle(self, mock_run_download) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            missing_with_ensure = root / "with-ensure"
            missing_without_ensure = root / "without-ensure"

            result = app_service.run_download_request(
                request=self._build_request(missing_with_ensure),
                cancel_event=threading.Event(),
                log=lambda _line: None,
                update_progress=lambda _payload: None,
                ensure_output_dir=True,
            )
            self.assertEqual(result, "success")
            self.assertTrue(missing_with_ensure.exists())

            result = app_service.run_download_request(
                request=self._build_request(missing_without_ensure),
                cancel_event=threading.Event(),
                log=lambda _line: None,
                update_progress=lambda _payload: None,
                ensure_output_dir=False,
            )
            self.assertEqual(result, "success")
            self.assertFalse(missing_without_ensure.exists())

        self.assertEqual(mock_run_download.call_count, 2)

    def test_record_history_output_keeps_entry_when_stat_fails(self) -> None:
        history: list[dict[str, object]] = []
        seen_paths: set[str] = set()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.mp4"
            saved = app_service.record_history_output(
                history=history,
                seen_paths=seen_paths,
                output_path=missing_file,
                source_url="https://example.com/watch?v=abc",
                max_entries=10,
                timestamp=datetime(2026, 3, 19, 12, 0, 0),
                title="Sample title",
                format_label="1080p",
                queue_settings={"mode": "video", "format_filter": "mp4"},
            )

        self.assertTrue(saved)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["file_size_bytes"], 0)
        self.assertEqual(history[0]["title"], "Sample title")
        self.assertEqual(history[0]["format_label"], "1080p")
        self.assertEqual(history[0]["queue_settings"], {"mode": "video", "format_filter": "mp4"})


if __name__ == "__main__":
    unittest.main()
