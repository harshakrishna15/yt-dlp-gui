import tempfile
import threading
import unittest
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

    @patch("gui.common.download.build_ydl_opts", return_value={"outtmpl": "%(title)s.%(ext)s"})
    @patch("gui.common.download.YoutubeDL")
    def test_run_download_request_handles_cancelled_after_late_stub_init(
        self,
        mock_ytdl,
        _mock_build_opts,
    ) -> None:
        from _yt_dlp_stub import ensure_yt_dlp_stub

        ensure_yt_dlp_stub()
        from yt_dlp.utils import DownloadCancelled as StubDownloadCancelled

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                raise StubDownloadCancelled()

        mock_ytdl.side_effect = _FakeYDL
        logs: list[str] = []
        updates: list[dict[str, object]] = []

        result = app_service.run_download_request(
            request=self._build_request(Path("/tmp/out")),
            cancel_event=threading.Event(),
            log=logs.append,
            update_progress=updates.append,
        )

        self.assertEqual(result, "cancelled")
        self.assertTrue(any("[cancelled] Download cancelled." in line for line in logs))
        self.assertIn({"status": "cancelled"}, updates)


if __name__ == "__main__":
    unittest.main()
