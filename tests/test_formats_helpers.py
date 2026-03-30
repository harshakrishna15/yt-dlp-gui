import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests._yt_dlp_stub import ensure_yt_dlp_stub

ensure_yt_dlp_stub()

from gui.common import formats as formats_mod
from gui.common import tooling
from gui.common import yt_dlp_helpers as helpers


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

    def test_sort_formats_prefers_video_mp4_avc_then_other_formats(self) -> None:
        formats = [
            {"format_id": "a1", "vcodec": "none", "ext": "webm", "abr": 160},
            {"format_id": "v3", "vcodec": "vp9", "ext": "webm", "height": 1080},
            {"format_id": "v2", "vcodec": "av01", "ext": "mp4", "height": 1080},
            {"format_id": "v1", "vcodec": "avc1.640028", "ext": "mp4", "height": 720},
        ]
        ordered = helpers.sort_formats(formats)
        self.assertEqual([fmt["format_id"] for fmt in ordered], ["v1", "v2", "v3", "a1"])


class TestTooling(unittest.TestCase):
    @patch("gui.common.tooling.os.access")
    def test_is_executable_respects_execute_permission(self, mock_access) -> None:
        with TemporaryDirectory() as tmpdir:
            candidate = Path(tmpdir) / "ffmpeg"
            candidate.write_text("binary", encoding="utf-8")

            mock_access.return_value = False
            self.assertFalse(tooling._is_executable(candidate))

            mock_access.return_value = True
            self.assertTrue(tooling._is_executable(candidate))

    @patch("gui.common.tooling.shutil.which")
    def test_resolve_binary_uses_path_lookup(self, mock_which) -> None:
        mock_which.return_value = "/usr/local/bin/ffmpeg"
        path, source = tooling.resolve_binary("ffmpeg")
        self.assertEqual(str(path), "/usr/local/bin/ffmpeg")
        self.assertEqual(source, "system")

    @patch("gui.common.tooling.subprocess.run")
    def test_available_ffmpeg_encoders_parses_requested_candidates(
        self,
        mock_run,
    ) -> None:
        mock_run.return_value = unittest.mock.Mock(
            returncode=0,
            stdout=" V....D h264_nvenc\n V....D libx264\n",
            stderr="",
        )

        encoders = tooling.available_ffmpeg_encoders(
            Path("/usr/local/bin/ffmpeg"),
            candidates=("h264_nvenc", "libx264", "h264_qsv"),
        )

        self.assertEqual(encoders, {"h264_nvenc", "libx264"})

    @patch("gui.common.tooling.subprocess.run", side_effect=OSError("missing"))
    def test_available_ffmpeg_encoders_returns_empty_on_subprocess_error(
        self,
        _mock_run,
    ) -> None:
        encoders = tooling.available_ffmpeg_encoders(
            Path("/usr/local/bin/ffmpeg"),
            candidates=("h264_nvenc", "libx264"),
        )
        self.assertEqual(encoders, set())

    @patch("gui.common.tooling.resolve_binary")
    def test_missing_required_binaries(self, mock_resolve_binary) -> None:
        def _fake(tool: str):
            if tool == "ffmpeg":
                return (None, "missing")
            return ("/usr/bin/ffprobe", "system")

        mock_resolve_binary.side_effect = _fake
        self.assertEqual(tooling.missing_required_binaries(), ["ffmpeg"])


class TestToolchainDetection(unittest.TestCase):
    @patch("gui.common.yt_dlp_helpers.resolve_binary")
    @patch("gui.common.yt_dlp_helpers._import_yt_dlp")
    def test_detect_toolchain_reports_versions_and_paths(
        self,
        mock_import_yt_dlp,
        mock_resolve_binary,
    ) -> None:
        class _FakeVersion:
            __version__ = "2026.1.29"

        class _FakeYtDlpModule:
            version = _FakeVersion()

        mock_import_yt_dlp.return_value = _FakeYtDlpModule

        def _resolve(tool: str):
            if tool == "yt-dlp":
                return (Path("/usr/local/bin/yt-dlp"), "system")
            if tool == "ffmpeg":
                return (Path("/usr/local/bin/ffmpeg"), "system")
            if tool == "ffprobe":
                return (None, "missing")
            return (None, "missing")

        mock_resolve_binary.side_effect = _resolve
        detected = helpers.detect_toolchain()

        self.assertEqual(detected["yt_dlp_module_version"], "2026.1.29")
        self.assertEqual(detected["yt_dlp_binary_source"], "system")
        self.assertEqual(detected["yt_dlp_binary_path"], "/usr/local/bin/yt-dlp")
        self.assertEqual(detected["ffmpeg_source"], "system")
        self.assertEqual(detected["ffmpeg_path"], "/usr/local/bin/ffmpeg")
        self.assertEqual(detected["ffprobe_source"], "missing")
        self.assertEqual(detected["ffprobe_path"], "not found")


if __name__ == "__main__":
    unittest.main()
