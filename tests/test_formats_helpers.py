import unittest
import sys
import types
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

        def extract_info(self, _url: str, download: bool, process: bool) -> dict:
            return {}

    yt_dlp_utils_stub.DownloadCancelled = _DownloadCancelled
    yt_dlp_stub.YoutubeDL = _YoutubeDL
    yt_dlp_stub.utils = yt_dlp_utils_stub
    yt_dlp_stub.version = types.SimpleNamespace(__version__="stub")
    sys.modules["yt_dlp"] = yt_dlp_stub
    sys.modules["yt_dlp.utils"] = yt_dlp_utils_stub

from gui import formats as formats_mod
from gui import tooling
from gui import yt_dlp_helpers as helpers


class TestFormatsFromInfo(unittest.TestCase):
    def test_formats_from_single_info(self) -> None:
        info = {"formats": [{"format_id": "22"}]}
        self.assertEqual(formats_mod.formats_from_info(info), [{"format_id": "22"}])

    def test_formats_from_playlist_first_entry(self) -> None:
        info = {
            "_type": "playlist",
            "entries": [
                {"formats": [{"format_id": "137"}]},
                {"formats": [{"format_id": "22"}]},
            ],
        }
        self.assertEqual(formats_mod.formats_from_info(info), [{"format_id": "137"}])

    def test_formats_from_invalid_entries(self) -> None:
        info = {"_type": "playlist", "entries": None}
        self.assertEqual(formats_mod.formats_from_info(info), [])


class TestFormatHelpers(unittest.TestCase):
    def test_split_and_filter_formats_applies_thresholds(self) -> None:
        formats = [
            {"format_id": "v1", "vcodec": "avc1", "height": 360, "ext": "mp4"},
            {"format_id": "v2", "vcodec": "avc1", "height": 720, "ext": "mp4"},
            {"format_id": "a1", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 96, "ext": "m4a"},
            {"format_id": "a2", "vcodec": "none", "acodec": "opus", "abr": 160, "ext": "webm"},
        ]
        video, audio = helpers.split_and_filter_formats(formats)
        self.assertEqual([f["format_id"] for f in video], ["v2"])
        self.assertEqual([f["format_id"] for f in audio], ["a2"])

    def test_collapse_formats_keeps_best_bitrate(self) -> None:
        formats = [
            {
                "format_id": "x1",
                "vcodec": "avc1",
                "acodec": "none",
                "ext": "mp4",
                "height": 720,
                "fps": 30,
                "tbr": 1000,
            },
            {
                "format_id": "x2",
                "vcodec": "avc1",
                "acodec": "none",
                "ext": "mp4",
                "height": 720,
                "fps": 30,
                "tbr": 2000,
            },
        ]
        collapsed = helpers.collapse_formats(formats)
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0]["format_id"], "x2")

    def test_label_format_audio_and_video(self) -> None:
        audio_label = helpers.label_format(
            {
                "format_id": "251",
                "ext": "webm",
                "vcodec": "none",
                "acodec": "opus",
                "abr": 160,
                "filesize_approx": 5 * 1024 * 1024,
            }
        )
        self.assertIn("Audio WEBM 160k (opus)", audio_label)
        self.assertIn("[251]", audio_label)
        self.assertIn("~5.0 MiB", audio_label)

        video_label = helpers.label_format(
            {
                "format_id": "137",
                "ext": "mp4",
                "vcodec": "avc1.640028",
                "acodec": "none",
                "height": 1080,
                "width": 1920,
                "fps": 30,
            }
        )
        self.assertIn("1080p 1920x1080 MP4 30fps", video_label)
        self.assertIn("[137]", video_label)

    def test_estimate_filesize_and_humanize_bytes(self) -> None:
        size = helpers.estimate_filesize_bytes({"filesize": 1536})
        self.assertEqual(size, 1536)
        self.assertEqual(helpers.humanize_bytes(size), "2 KiB")
        approx_only = helpers.estimate_filesize_bytes({"filesize_approx": 3 * 1024 * 1024})
        self.assertEqual(helpers.humanize_bytes(approx_only), "3.0 MiB")

    def test_build_labeled_formats_filters_missing_format_id(self) -> None:
        labeled = helpers.build_labeled_formats(
            [
                {"format_id": "22", "vcodec": "avc1", "ext": "mp4", "height": 720},
                {"vcodec": "avc1", "ext": "mp4", "height": 1080},
            ]
        )
        self.assertEqual(len(labeled), 1)
        self.assertEqual(labeled[0][1]["format_id"], "22")

    def test_extract_audio_languages_unique_and_sorted(self) -> None:
        formats = [
            {"format_id": "v1", "vcodec": "avc1", "language": "fr"},
            {"format_id": "a1", "vcodec": "none", "language": "ES"},
            {"format_id": "a2", "vcodec": "none", "language": "en"},
            {"format_id": "a3", "vcodec": "none", "language": "es"},
            {"format_id": "a4", "vcodec": "none", "language": "und"},
            {"format_id": "a5", "vcodec": "none", "language": ""},
        ]
        self.assertEqual(helpers.extract_audio_languages(formats), ["en", "es"])


class TestTooling(unittest.TestCase):
    @patch("gui.tooling.shutil.which")
    def test_resolve_binary_uses_path_lookup(self, mock_which) -> None:
        mock_which.return_value = "/usr/local/bin/ffmpeg"
        path, source = tooling.resolve_binary("ffmpeg")
        self.assertEqual(str(path), "/usr/local/bin/ffmpeg")
        self.assertEqual(source, "system")

    @patch("gui.tooling.resolve_binary")
    def test_missing_required_binaries(self, mock_resolve_binary) -> None:
        def _fake(tool: str):
            if tool == "ffmpeg":
                return (None, "missing")
            return ("/usr/bin/ffprobe", "system")

        mock_resolve_binary.side_effect = _fake
        self.assertEqual(tooling.missing_required_binaries(), ["ffmpeg"])


if __name__ == "__main__":
    unittest.main()
