import threading
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch

if "yt_dlp" not in sys.modules:
    yt_dlp_stub = types.ModuleType("yt_dlp")
    yt_dlp_utils_stub = types.ModuleType("yt_dlp.utils")

    class _DownloadCancelled(Exception):
        pass

    class _YoutubeDL:
        def __init__(self, _opts: dict | None = None) -> None:
            self.opts = _opts or {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, _urls: list[str]) -> None:
            return None

    yt_dlp_utils_stub.DownloadCancelled = _DownloadCancelled
    yt_dlp_stub.YoutubeDL = _YoutubeDL
    yt_dlp_stub.utils = yt_dlp_utils_stub
    yt_dlp_stub.version = types.SimpleNamespace(__version__="stub")
    sys.modules["yt_dlp"] = yt_dlp_stub
    sys.modules["yt_dlp.utils"] = yt_dlp_utils_stub

from yt_dlp.utils import DownloadCancelled

from gui import download


class TestPlaylistParsing(unittest.TestCase):
    def test_parse_playlist_items_mixed_ranges(self) -> None:
        items = "1-3, 7, 10-, invalid, -4, 2-a"
        parsed = download._parse_playlist_items(items)
        self.assertEqual(parsed, [(1, 3), (7, 7), (10, None)])

    def test_playlist_ranges_count(self) -> None:
        self.assertEqual(download._playlist_ranges_count([(1, 3), (7, 7)]), 4)
        self.assertIsNone(download._playlist_ranges_count([(1, None)]))
        self.assertIsNone(download._playlist_ranges_count([]))

    def test_playlist_position_for_index(self) -> None:
        ranges = [(1, 3), (7, 7), (10, 11)]
        self.assertEqual(download._playlist_position_for_index(ranges, 1), 1)
        self.assertEqual(download._playlist_position_for_index(ranges, 3), 3)
        self.assertEqual(download._playlist_position_for_index(ranges, 7), 4)
        self.assertEqual(download._playlist_position_for_index(ranges, 11), 6)
        self.assertIsNone(download._playlist_position_for_index(ranges, 8))

    def test_playlist_match_filter(self) -> None:
        fn = download._playlist_match_filter([(1, 2), (5, 5)])
        self.assertIsNone(fn({"playlist_index": 1}))
        self.assertIsNone(fn({"playlist_index": "2"}))
        self.assertIsNone(fn({"playlist_index": 5}))
        self.assertEqual(fn({"playlist_index": 4}), "skip playlist item")
        self.assertIsNone(fn({}))

    def test_parse_playlist_items_rejects_invalid_nonpositive_ranges(self) -> None:
        items = "0,0-5,5-3,-1,2-2,4-"
        parsed = download._parse_playlist_items(items)
        self.assertEqual(parsed, [(2, 2), (4, None)])


class TestBuildYdlOptions(unittest.TestCase):
    def setUp(self) -> None:
        self.logs: list[str] = []
        self.updates: list[dict] = []

    def _log(self, line: str) -> None:
        self.logs.append(line)

    def _update(self, payload: dict) -> None:
        self.updates.append(payload)

    @patch("gui.download.resolve_binary")
    def test_build_opts_audio_extract(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (Path("/usr/bin/ffmpeg"), "system")
        opts = download.build_ydl_opts(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "251", "vcodec": "none", "acodec": "opus", "ext": "webm"},
            fmt_label="Audio WEBM",
            format_filter="mp3",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
        )
        self.assertEqual(opts["format"], "251")
        self.assertEqual(opts["merge_output_format"], None)
        self.assertEqual(opts["postprocessors"][0]["key"], "FFmpegExtractAudio")
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")
        self.assertEqual(opts["ffmpeg_location"], "/usr/bin/ffmpeg")
        self.assertIn("[format] Audio WEBM", self.logs)
        self.assertEqual(opts["socket_timeout"], download.YDL_SOCKET_TIMEOUT_SECONDS)
        self.assertEqual(opts["retries"], download.YDL_RETRIES)
        self.assertEqual(opts["fragment_retries"], download.YDL_FRAGMENT_RETRIES)
        self.assertEqual(opts["extractor_retries"], download.YDL_EXTRACTOR_RETRIES)
        self.assertEqual(opts["file_access_retries"], download.YDL_FILE_ACCESS_RETRIES)
        self.assertEqual(opts["skip_unavailable_fragments"], True)
        self.assertEqual(opts["continuedl"], True)

    @patch("gui.download.resolve_binary")
    def test_build_opts_playlist_items_sets_filters(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/playlist",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "137", "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=True,
            playlist_items="2-4,9",
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
        )
        self.assertEqual(opts["noplaylist"], False)
        self.assertEqual(opts["playlist_items"], "2-4,9")
        self.assertIn("match_filter", opts)
        self.assertNotIn("playlist_start", opts)
        self.assertNotIn("playlist_end", opts)
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertEqual(opts["postprocessors"][0]["key"], "FFmpegVideoConvertor")
        self.assertTrue(str(opts["outtmpl"]).endswith("%(playlist_index)s - %(title)s_%(epoch)s.%(ext)s"))
        self.assertIn("[ffmpeg] source=missing (some merges/conversions may fail)", self.logs)

    @patch("gui.download.resolve_binary")
    def test_build_opts_simple_range_sets_start_end(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/playlist",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "248", "vcodec": "av01", "acodec": "none", "ext": "webm"},
            fmt_label="Video WEBM",
            format_filter="webm",
            convert_to_mp4=True,
            playlist_enabled=True,
            playlist_items="3-6",
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
        )
        self.assertEqual(opts["playlist_start"], 3)
        self.assertEqual(opts["playlist_end"], 6)
        self.assertEqual(opts["merge_output_format"], "mp4")


class TestRunDownload(unittest.TestCase):
    def setUp(self) -> None:
        self.logs: list[str] = []
        self.updates: list[dict] = []

    def _log(self, line: str) -> None:
        self.logs.append(line)

    def _update(self, payload: dict) -> None:
        self.updates.append(payload)

    @patch("gui.download.build_ydl_opts")
    @patch("gui.download.YoutubeDL")
    def test_run_download_cancelled(self, mock_ytdl, mock_build_opts) -> None:
        mock_build_opts.return_value = {"outtmpl": "%(title)s.%(ext)s"}

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                raise DownloadCancelled()

        mock_ytdl.side_effect = _FakeYDL

        result = download.run_download(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22"},
            fmt_label="label",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=threading.Event(),
            log=self._log,
            update_progress=self._update,
        )

        self.assertEqual(result, download.DOWNLOAD_CANCELLED)
        self.assertTrue(any("[cancelled] Download cancelled." in l for l in self.logs))
        self.assertIn({"status": "cancelled"}, self.updates)
        self.assertTrue(any(l.startswith("[time] Elapsed: ") for l in self.logs))

    @patch("gui.download.build_ydl_opts")
    @patch("gui.download.YoutubeDL")
    def test_run_download_error(self, mock_ytdl, mock_build_opts) -> None:
        mock_build_opts.return_value = {"outtmpl": "%(title)s.%(ext)s"}

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                raise RuntimeError("boom")

        mock_ytdl.side_effect = _FakeYDL

        result = download.run_download(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22"},
            fmt_label="label",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
        )

        self.assertEqual(result, download.DOWNLOAD_ERROR)
        self.assertTrue(any("[error] boom" in l for l in self.logs))
        self.assertTrue(any(l.startswith("[time] Elapsed: ") for l in self.logs))

    @patch("gui.download.build_ydl_opts")
    @patch("gui.download.YoutubeDL")
    def test_run_download_success(self, mock_ytdl, mock_build_opts) -> None:
        mock_build_opts.return_value = {"outtmpl": "%(title)s.%(ext)s"}

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                return None

        mock_ytdl.side_effect = _FakeYDL
        result = download.run_download(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22"},
            fmt_label="label",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
        )

        self.assertEqual(result, download.DOWNLOAD_SUCCESS)
        self.assertTrue(any("[done] Download complete." in l for l in self.logs))


class TestUtilityFormatting(unittest.TestCase):
    def test_format_duration(self) -> None:
        self.assertEqual(download.format_duration(59), "0:59")
        self.assertEqual(download.format_duration(61), "1:01")
        self.assertEqual(download.format_duration(3661), "1:01:01")


class TestProgressHookResilience(unittest.TestCase):
    def test_progress_hook_survives_update_callback_errors(self) -> None:
        logs: list[str] = []

        def _log(line: str) -> None:
            logs.append(line)

        def _bad_update(_payload: dict) -> None:
            raise RuntimeError("ui fail")

        hook = download._progress_hook_factory(
            log=_log,
            update_progress=_bad_update,
            cancel_event=None,
            ranges=[],
        )

        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 2048,
                "eta": 3,
                "info_dict": {"playlist_index": 1, "title": "Title"},
            }
        )
        hook({"status": "finished", "info_dict": {"title": "Done"}})
        self.assertTrue(any("[progress] UI update failed: ui fail" in x for x in logs))


if __name__ == "__main__":
    unittest.main()
