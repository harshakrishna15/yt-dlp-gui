import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from _yt_dlp_stub import ensure_yt_dlp_stub

ensure_yt_dlp_stub()

from yt_dlp.utils import DownloadCancelled

from gui.common import download


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

    @patch("gui.common.download.resolve_binary")
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
        self.assertTrue(opts["writethumbnail"])
        self.assertIn({"key": "EmbedThumbnail"}, opts["postprocessors"])
        self.assertEqual(opts["ffmpeg_location"], "/usr/bin/ffmpeg")
        self.assertIn("[format] Audio WEBM", self.logs)
        self.assertEqual(opts["socket_timeout"], download.YDL_SOCKET_TIMEOUT_SECONDS)
        self.assertEqual(opts["retries"], download.YDL_RETRIES)
        self.assertEqual(opts["fragment_retries"], download.YDL_FRAGMENT_RETRIES)
        self.assertEqual(opts["extractor_retries"], download.YDL_EXTRACTOR_RETRIES)
        self.assertEqual(opts["file_access_retries"], download.YDL_FILE_ACCESS_RETRIES)
        self.assertEqual(
            opts["concurrent_fragment_downloads"],
            download.YDL_MAX_CONCURRENT_FRAGMENTS,
        )
        self.assertEqual(opts["skip_unavailable_fragments"], True)
        self.assertEqual(opts["continuedl"], True)

    @patch("gui.common.download.resolve_binary")
    def test_build_opts_honors_configured_fragment_concurrency_with_cap(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            concurrent_fragments=3,
        )
        self.assertEqual(opts["concurrent_fragment_downloads"], 3)

        opts_capped = download.build_ydl_opts(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            concurrent_fragments=99,
        )
        self.assertEqual(
            opts_capped["concurrent_fragment_downloads"],
            download.YDL_MAX_CONCURRENT_FRAGMENTS,
        )

    @patch("gui.common.download.resolve_binary")
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
        self.assertEqual(
            opts["sleep_interval"], download.YDL_PLAYLIST_SLEEP_MIN_SECONDS
        )
        self.assertEqual(
            opts["max_sleep_interval"], download.YDL_PLAYLIST_SLEEP_MAX_SECONDS
        )
        self.assertIn("match_filter", opts)
        self.assertNotIn("playlist_start", opts)
        self.assertNotIn("playlist_end", opts)
        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertEqual(opts["postprocessors"][0]["key"], "FFmpegVideoConvertor")
        self.assertTrue(opts["writethumbnail"])
        self.assertIn({"key": "EmbedThumbnail"}, opts["postprocessors"])
        self.assertTrue(str(opts["outtmpl"]).endswith("%(playlist_index)s - %(title)s_%(epoch)s.%(ext)s"))
        self.assertIn("[ffmpeg] source=missing (some merges/conversions may fail)", self.logs)

    @patch("gui.common.download.resolve_binary")
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
        self.assertEqual(
            opts["sleep_interval"], download.YDL_PLAYLIST_SLEEP_MIN_SECONDS
        )
        self.assertEqual(
            opts["max_sleep_interval"], download.YDL_PLAYLIST_SLEEP_MAX_SECONDS
        )
        self.assertEqual(opts["merge_output_format"], "mp4")

    @patch("gui.common.download.resolve_binary")
    def test_build_opts_uses_custom_filename_for_single_video(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            custom_filename="My Clip.mp4",
        )
        self.assertTrue(
            str(opts["outtmpl"]).endswith("My Clip_%(epoch)s.%(ext)s")
        )

    @patch("gui.common.download.resolve_binary")
    def test_build_opts_ignores_custom_filename_for_playlists(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/playlist",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=True,
            playlist_items="1-2",
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            custom_filename="My Clip",
        )
        self.assertTrue(
            str(opts["outtmpl"]).endswith("%(playlist_index)s - %(title)s_%(epoch)s.%(ext)s")
        )

    @patch("gui.common.download.resolve_binary")
    def test_build_opts_includes_subtitle_language_and_audio_language(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/video",
            output_dir=Path("/tmp/out"),
            fmt_info={
                "format_id": "22",
                "vcodec": "avc1.640028",
                "acodec": "mp4a.40.2",
                "ext": "mp4",
            },
            fmt_label="Video MP4",
            format_filter="mp4",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            network_timeout_s=7,
            subtitle_languages=["en", "es"],
            write_subtitles=True,
            embed_subtitles=True,
            audio_language="es",
        )
        self.assertEqual(opts["socket_timeout"], 7)
        self.assertTrue(opts["writesubtitles"])
        self.assertTrue(opts["writeautomaticsub"])
        self.assertEqual(opts["subtitleslangs"], ["en", "es"])
        self.assertTrue(opts["writethumbnail"])
        self.assertIn({"key": "EmbedThumbnail"}, opts["postprocessors"])
        self.assertIn({"key": "FFmpegEmbedSubtitle"}, opts["postprocessors"])
        self.assertEqual(opts["format_sort"], ["lang:es"])

    @patch("gui.common.download.resolve_binary")
    def test_build_opts_does_not_embed_subtitles_for_audio_only(self, mock_resolve_binary) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        opts = download.build_ydl_opts(
            url="https://example.com/audio",
            output_dir=Path("/tmp/out"),
            fmt_info={"format_id": "251", "vcodec": "none", "acodec": "opus", "ext": "webm"},
            fmt_label="Audio WEBM",
            format_filter="opus",
            convert_to_mp4=False,
            playlist_enabled=False,
            playlist_items=None,
            cancel_event=None,
            log=self._log,
            update_progress=self._update,
            write_subtitles=True,
            embed_subtitles=True,
        )
        self.assertTrue(opts["writesubtitles"])
        self.assertTrue(opts["writethumbnail"])
        self.assertIn({"key": "EmbedThumbnail"}, opts["postprocessors"])
        self.assertNotIn({"key": "FFmpegEmbedSubtitle"}, opts["postprocessors"])


class TestEditFriendlyMp4Postprocess(unittest.TestCase):
    @patch("gui.common.download.resolve_binary")
    def test_postprocess_edit_friendly_mp4_logs_when_ffmpeg_missing(
        self, mock_resolve_binary
    ) -> None:
        mock_resolve_binary.return_value = (None, "missing")
        logs: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "clip.mp4"
            output.write_text("data", encoding="utf-8")
            download._postprocess_edit_friendly_mp4(
                output_paths=[output],
                format_filter="mp4",
                fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a"},
                edit_friendly_encoder="auto",
                cancel_event=None,
                update_progress=lambda _payload: None,
                log=logs.append,
            )
        self.assertTrue(
            any("ffmpeg missing; skipped edit-friendly MP4 re-encode" in line for line in logs)
        )

    @patch("gui.common.download._reencode_edit_friendly_mp4_file")
    @patch("gui.common.download._select_edit_friendly_video_codec", return_value="libx264")
    @patch("gui.common.download.resolve_binary")
    def test_postprocess_edit_friendly_mp4_reencodes_unique_mp4_outputs(
        self, mock_resolve_binary, _mock_select_codec, mock_reencode
    ) -> None:
        def _resolve(tool: str):
            if tool == "ffmpeg":
                return (Path("/usr/bin/ffmpeg"), "system")
            if tool == "ffprobe":
                return (None, "missing")
            return (None, "missing")

        mock_resolve_binary.side_effect = _resolve
        logs: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "clip.mp4"
            output.write_text("data", encoding="utf-8")
            webm = Path(tmpdir) / "clip.webm"
            webm.write_text("data", encoding="utf-8")
            download._postprocess_edit_friendly_mp4(
                output_paths=[output, webm, output],
                format_filter="mp4",
                fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a"},
                edit_friendly_encoder="auto",
                cancel_event=None,
                update_progress=lambda _payload: None,
                log=logs.append,
            )

        mock_reencode.assert_called_once()
        self.assertEqual(mock_reencode.call_args.kwargs["input_path"], output)

    @patch("gui.common.download._select_edit_friendly_video_codec", return_value="h264_nvenc")
    @patch("gui.common.download._reencode_edit_friendly_mp4_file")
    @patch("gui.common.download.resolve_binary")
    def test_postprocess_edit_friendly_mp4_falls_back_to_libx264_after_hw_failure(
        self,
        mock_resolve_binary,
        mock_reencode,
        _mock_select_codec,
    ) -> None:
        def _resolve(tool: str):
            if tool == "ffmpeg":
                return (Path("/usr/bin/ffmpeg"), "system")
            if tool == "ffprobe":
                return (None, "missing")
            return (None, "missing")

        mock_resolve_binary.side_effect = _resolve
        mock_reencode.side_effect = [False, True]
        logs: list[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "clip.mp4"
            output.write_text("data", encoding="utf-8")
            download._postprocess_edit_friendly_mp4(
                output_paths=[output],
                format_filter="mp4",
                fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a"},
                edit_friendly_encoder="nvidia",
                cancel_event=None,
                update_progress=lambda _payload: None,
                log=logs.append,
            )

        self.assertEqual(mock_reencode.call_count, 2)
        first_codec = mock_reencode.call_args_list[0].kwargs["video_codec"]
        second_codec = mock_reencode.call_args_list[1].kwargs["video_codec"]
        self.assertEqual(first_codec, "h264_nvenc")
        self.assertEqual(second_codec, "libx264")
        self.assertTrue(any("falling back to libx264" in line for line in logs))

    def test_edit_friendly_mp4_required_skips_audio_only(self) -> None:
        self.assertFalse(
            download._edit_friendly_mp4_required(
                format_filter="mp4",
                fmt_info={"format_id": "251", "vcodec": "none", "acodec": "opus"},
            )
        )
        self.assertTrue(
            download._edit_friendly_mp4_required(
                format_filter="mp4",
                fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a"},
            )
        )


class TestRunDownload(unittest.TestCase):
    def setUp(self) -> None:
        self.logs: list[str] = []
        self.updates: list[dict] = []

    def _log(self, line: str) -> None:
        self.logs.append(line)

    def _update(self, payload: dict) -> None:
        self.updates.append(payload)

    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
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
        self.assertTrue(any(l.startswith("[time] Total item time: ") for l in self.logs))

    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
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
        self.assertTrue(any(l.startswith("[time] Total item time: ") for l in self.logs))

    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
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
        self.assertTrue(any(l.startswith("[time] Total item time: ") for l in self.logs))

    @patch("gui.common.download._postprocess_edit_friendly_mp4")
    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
    def test_run_download_invokes_edit_friendly_postprocess_for_mp4(
        self, mock_ytdl, mock_build_opts, mock_postprocess
    ) -> None:
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
            fmt_info={"format_id": "22", "vcodec": "avc1", "acodec": "mp4a", "ext": "mp4"},
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
        mock_postprocess.assert_called_once()
        self.assertEqual(mock_postprocess.call_args.kwargs["format_filter"], "mp4")

    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
    def test_run_download_passes_custom_filename_to_build_opts(
        self, mock_ytdl, mock_build_opts
    ) -> None:
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
            custom_filename="Renamed clip",
        )

        self.assertEqual(result, download.DOWNLOAD_SUCCESS)
        self.assertEqual(
            mock_build_opts.call_args.kwargs.get("custom_filename"),
            "Renamed clip",
        )

    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
    def test_run_download_retries_then_succeeds(self, mock_ytdl, mock_build_opts) -> None:
        mock_build_opts.return_value = {"outtmpl": "%(title)s.%(ext)s"}
        attempts = {"count": 0}

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                attempts["count"] += 1
                if attempts["count"] == 1:
                    raise RuntimeError("transient")
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
            network_retries=1,
            retry_backoff_s=0.0,
        )

        self.assertEqual(result, download.DOWNLOAD_SUCCESS)
        self.assertEqual(attempts["count"], 2)
        self.assertTrue(any("[retry]" in line for line in self.logs))

    @patch("gui.common.download.time.sleep", side_effect=KeyboardInterrupt)
    @patch("gui.common.download.build_ydl_opts")
    @patch("gui.common.download.YoutubeDL")
    def test_run_download_keyboard_interrupt_during_backoff_returns_cancelled(
        self, mock_ytdl, mock_build_opts, _mock_sleep
    ) -> None:
        mock_build_opts.return_value = {"outtmpl": "%(title)s.%(ext)s"}

        class _FakeYDL:
            def __init__(self, _opts: dict) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def download(self, _urls: list[str]) -> None:
                raise RuntimeError("transient")

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
            network_retries=1,
            retry_backoff_s=0.5,
        )

        self.assertEqual(result, download.DOWNLOAD_CANCELLED)
        self.assertTrue(any("[retry]" in line for line in self.logs))
        self.assertTrue(any("[cancelled] Download cancelled." in line for line in self.logs))
        self.assertIn({"status": "cancelled"}, self.updates)


class TestEditFriendlyProgressParsing(unittest.TestCase):
    def test_parse_hms_seconds(self) -> None:
        self.assertEqual(download._parse_hms_seconds("00:00:01.500000"), 1.5)
        self.assertEqual(download._parse_hms_seconds("1:02:03.000"), 3723.0)
        self.assertIsNone(download._parse_hms_seconds("bad"))

    def test_ffmpeg_speed_ratio_prefers_reported_speed(self) -> None:
        speed = download._ffmpeg_speed_ratio(
            snapshot={"speed": "1.25x"},
            out_seconds=4.0,
            elapsed_seconds=10.0,
        )
        self.assertEqual(speed, 1.25)

    def test_ffmpeg_speed_ratio_falls_back_to_out_time_vs_elapsed(self) -> None:
        speed = download._ffmpeg_speed_ratio(
            snapshot={"speed": "N/A"},
            out_seconds=4.0,
            elapsed_seconds=2.0,
        )
        self.assertEqual(speed, 2.0)


class TestEditFriendlyEncoderSelection(unittest.TestCase):
    @patch("gui.common.download.sys.platform", "darwin")
    @patch(
        "gui.common.download._available_h264_video_encoders",
        return_value={"h264_nvenc", "h264_videotoolbox", "libx264"},
    )
    def test_select_prefers_videotoolbox_on_macos(self, _mock_available) -> None:
        logs: list[str] = []
        selected = download._select_edit_friendly_video_codec(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            preferred="auto",
            log=logs.append,
        )
        self.assertEqual(selected, "h264_videotoolbox")

    @patch("gui.common.download.sys.platform", "linux")
    @patch(
        "gui.common.download._available_h264_video_encoders",
        return_value={"h264_qsv", "libx264"},
    )
    def test_select_prefers_qsv_when_no_nvenc_or_amf(self, _mock_available) -> None:
        logs: list[str] = []
        selected = download._select_edit_friendly_video_codec(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            preferred="auto",
            log=logs.append,
        )
        self.assertEqual(selected, "h264_qsv")

    @patch("gui.common.download.sys.platform", "darwin")
    @patch(
        "gui.common.download._available_h264_video_encoders",
        return_value={"h264_nvenc", "h264_videotoolbox", "libx264"},
    )
    def test_select_uses_manual_vendor_preference(self, _mock_available) -> None:
        logs: list[str] = []
        selected = download._select_edit_friendly_video_codec(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            preferred="nvidia",
            log=logs.append,
        )
        self.assertEqual(selected, "h264_nvenc")

    @patch("gui.common.download.sys.platform", "linux")
    @patch(
        "gui.common.download._available_h264_video_encoders",
        return_value={"h264_qsv", "libx264"},
    )
    def test_select_falls_back_to_cpu_when_manual_vendor_unavailable(
        self, _mock_available
    ) -> None:
        logs: list[str] = []
        selected = download._select_edit_friendly_video_codec(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            preferred="amd",
            log=logs.append,
        )
        self.assertEqual(selected, "libx264")


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

    def test_progress_hook_records_output_filename(self) -> None:
        outputs: list[Path] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=lambda _payload: None,
            cancel_event=None,
            ranges=[],
            record_output=outputs.append,
        )
        hook(
            {
                "status": "finished",
                "filename": "/tmp/example.mp4",
                "info_dict": {"title": "Done"},
            }
        )
        self.assertEqual(outputs, [Path("/tmp/example.mp4")])

    def test_progress_hook_handles_invalid_eta_and_percent_values(self) -> None:
        updates: list[dict] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=updates.append,
            cancel_event=None,
            ranges=[],
        )
        hook(
            {
                "status": "downloading",
                "downloaded_bytes": object(),
                "total_bytes": 100,
                "speed": 1024,
                "eta": "bad",
                "info_dict": {"playlist_index": 1, "title": "Title"},
            }
        )
        downloading_updates = [u for u in updates if u.get("status") == "downloading"]
        self.assertTrue(downloading_updates)
        self.assertIsNone(downloading_updates[-1]["percent"])
        self.assertEqual(downloading_updates[-1]["eta"], "—")

    def test_progress_hook_emits_single_video_item_title_once(self) -> None:
        updates: list[dict] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=updates.append,
            cancel_event=None,
            ranges=[],
        )
        payload = {
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 100,
            "speed": 1024,
            "eta": 5,
            "info_dict": {"title": "Single Video Title"},
        }
        hook(payload)
        hook(payload)

        item_updates = [u for u in updates if u.get("status") == "item"]
        self.assertEqual(
            item_updates,
            [{"status": "item", "item": "Single Video Title"}],
        )

    def test_progress_hook_includes_playlist_eta_for_playlist_downloads(self) -> None:
        updates: list[dict] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=updates.append,
            cancel_event=None,
            ranges=[],
        )
        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 10,
                "total_bytes": 100,
                "speed": 1024,
                "eta": 12,
                "info_dict": {"playlist_index": 1, "playlist_count": 4, "title": "One"},
            }
        )
        downloading_updates = [u for u in updates if u.get("status") == "downloading"]
        self.assertTrue(downloading_updates)
        self.assertEqual(downloading_updates[-1]["eta"], "0:12")
        self.assertEqual(downloading_updates[-1]["playlist_eta"], "0:48")
        self.assertAlmostEqual(downloading_updates[-1]["percent"], 2.5, places=2)

    def test_progress_hook_uses_percent_str_when_byte_totals_missing(self) -> None:
        updates: list[dict] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=updates.append,
            cancel_event=None,
            ranges=[],
        )
        hook(
            {
                "status": "downloading",
                "_percent_str": " 37.5%",
                "speed": 1024,
                "eta": 12,
                "info_dict": {"playlist_index": 1, "playlist_count": 4, "title": "One"},
            }
        )
        downloading_updates = [u for u in updates if u.get("status") == "downloading"]
        self.assertTrue(downloading_updates)
        self.assertAlmostEqual(downloading_updates[-1]["percent"], 9.375, places=3)

    def test_progress_hook_uses_elapsed_eta_percent_when_totals_missing(self) -> None:
        updates: list[dict] = []
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=updates.append,
            cancel_event=None,
            ranges=[],
        )
        hook(
            {
                "status": "downloading",
                "speed": 1024,
                "eta": 30,
                "elapsed": 30,
                "info_dict": {"playlist_index": 2, "playlist_count": 4, "title": "Two"},
            }
        )
        downloading_updates = [u for u in updates if u.get("status") == "downloading"]
        self.assertTrue(downloading_updates)
        self.assertAlmostEqual(downloading_updates[-1]["percent"], 37.5, places=2)

    def test_progress_hook_ignores_record_output_runtime_error(self) -> None:
        hook = download._progress_hook_factory(
            log=lambda _line: None,
            update_progress=lambda _payload: None,
            cancel_event=None,
            ranges=[],
            record_output=lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        hook(
            {
                "status": "finished",
                "filename": "/tmp/example.mp4",
                "info_dict": {"title": "Done"},
            }
        )


class TestPostprocessorHook(unittest.TestCase):
    def test_postprocessor_hook_removes_timestamp_when_no_name_conflict(self) -> None:
        logs: list[str] = []
        outputs: list[Path] = []
        hook = download._postprocessor_hook_factory(logs.append, record_output=outputs.append)
        with patch.object(Path, "exists", return_value=False), patch.object(
            Path, "rename"
        ) as mock_rename:
            hook(
                {
                    "status": "finished",
                    "filename": "/tmp/example_1700000000.mp4",
                    "info_dict": {},
                }
            )
        mock_rename.assert_called_once_with(Path("/tmp/example.mp4"))
        self.assertEqual(outputs, [Path("/tmp/example.mp4")])
        self.assertTrue(any("[rename] example.mp4" in line for line in logs))

    def test_postprocessor_hook_keeps_timestamp_when_name_conflicts(self) -> None:
        logs: list[str] = []
        outputs: list[Path] = []
        hook = download._postprocessor_hook_factory(logs.append, record_output=outputs.append)
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "rename"
        ) as mock_rename:
            hook(
                {
                    "status": "finished",
                    "filename": "/tmp/example_1700000000.mp4",
                    "info_dict": {},
                }
            )
        mock_rename.assert_not_called()
        self.assertEqual(outputs, [Path("/tmp/example_1700000000.mp4")])
        self.assertTrue(
            any(
                "[rename] Clean name exists; using epoch suffix fallback:" in line
                for line in logs
            )
        )

    def test_postprocessor_hook_logs_rename_failure(self) -> None:
        logs: list[str] = []
        hook = download._postprocessor_hook_factory(logs.append)
        with patch.object(Path, "exists", return_value=False), patch.object(
            Path, "rename", side_effect=OSError("rename failed")
        ):
            hook(
                {
                    "status": "finished",
                    "filename": "/tmp/example_123456.mp4",
                    "info_dict": {},
                }
            )
        self.assertTrue(any("[rename] Failed to rename: rename failed" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
