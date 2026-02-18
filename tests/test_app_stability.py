import queue
import threading
import tempfile
import sys
import types
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

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

from gui.app import FORMAT_CACHE_MAX_ENTRIES, UI_EVENT_POLL_MS, YtDlpGui
from gui.state import FormatState


class _Var:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class TestFetchRaceGuard(unittest.TestCase):
    def _base_app(self) -> YtDlpGui:
        app = object.__new__(YtDlpGui)
        app.formats = FormatState()
        app.status_var = _Var("Idle")
        app.preview_title_var = _Var("")
        app._set_playlist_ui = Mock()
        app._apply_mode_formats = Mock()
        app._update_controls_state = Mock()
        app._reset_format_selections = Mock()
        app._active_fetch_request_id = None
        return app

    def test_set_formats_ignores_stale_fetch_result(self) -> None:
        app = self._base_app()
        app.formats.is_fetching = True
        app.formats.last_fetched_url = "https://new.example"
        app.formats.video_labels = ["keep me"]
        app.formats.video_lookup = {"keep me": {"format_id": "x"}}
        app._active_fetch_request_id = 2

        with patch("gui.app.format_pipeline.build_format_collections") as build_mock:
            app._set_formats(
                [{"format_id": "new"}],
                fetch_url="https://old.example",
                request_id=1,
            )

        build_mock.assert_not_called()
        self.assertTrue(app.formats.is_fetching)
        self.assertEqual(app.formats.last_fetched_url, "https://new.example")
        self.assertEqual(app.formats.video_labels, ["keep me"])
        self.assertEqual(app._active_fetch_request_id, 2)

    def test_set_formats_caches_by_fetch_url_for_active_request(self) -> None:
        app = self._base_app()
        app.formats.is_fetching = True
        app._active_fetch_request_id = 7
        app.url_var = _Var("https://example.com/watch?v=123")
        fetch_url = "https://example.com/watch?v=123"
        video_fmt = {"format_id": "137", "ext": "mp4", "vcodec": "avc1", "acodec": "none"}
        audio_fmt = {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus"}

        with patch(
            "gui.app.format_pipeline.build_format_collections",
            return_value={
                "video_labels": ["Video 1080p"],
                "video_lookup": {"Video 1080p": video_fmt},
                "audio_labels": ["Best audio only", "Audio opus"],
                "audio_lookup": {
                    "Best audio only": {"custom_format": "bestaudio/best", "is_audio_only": True},
                    "Audio opus": audio_fmt,
                },
                "audio_languages": [],
            },
        ):
            app._set_formats(
                [video_fmt, audio_fmt],
                fetch_url=fetch_url,
                request_id=7,
            )

        self.assertFalse(app.formats.is_fetching)
        self.assertIsNone(app._active_fetch_request_id)
        self.assertIn(fetch_url, app.formats.cache)
        self.assertEqual(app.formats.cache[fetch_url]["video_labels"], ["Video 1080p"])
        self.assertEqual(app.preview_title_var.get(), "")

    def test_set_formats_for_old_url_refetches_current_url(self) -> None:
        app = self._base_app()
        app.formats.is_fetching = True
        app._active_fetch_request_id = 9
        app.url_var = _Var("https://current.example")
        app._start_fetch_formats = Mock()
        scheduled: list[tuple[int, object]] = []
        app._safe_after = lambda delay, callback: scheduled.append((delay, callback)) or "after-2"

        with patch("gui.app.format_pipeline.build_format_collections") as build_mock:
            app._set_formats(
                [{"format_id": "stale"}],
                fetch_url="https://stale.example",
                request_id=9,
            )

        build_mock.assert_not_called()
        self.assertFalse(app.formats.is_fetching)
        self.assertIsNone(app._active_fetch_request_id)
        self.assertEqual(scheduled[0][0], 0)
        self.assertEqual(scheduled[0][1], app._start_fetch_formats)

    def test_set_formats_applies_preview_metadata(self) -> None:
        app = self._base_app()
        app.formats.is_fetching = True
        app._active_fetch_request_id = 11
        app.url_var = _Var("https://example.com/watch?v=123")

        video_fmt = {"format_id": "137", "ext": "mp4", "vcodec": "avc1", "acodec": "none"}
        audio_fmt = {"format_id": "251", "ext": "webm", "vcodec": "none", "acodec": "opus"}
        with patch(
            "gui.app.format_pipeline.build_format_collections",
            return_value={
                "video_labels": ["Video 1080p"],
                "video_lookup": {"Video 1080p": video_fmt},
                "audio_labels": ["Best audio only", "Audio opus"],
                "audio_lookup": {
                    "Best audio only": {"custom_format": "bestaudio/best", "is_audio_only": True},
                    "Audio opus": audio_fmt,
                },
                "audio_languages": [],
            },
        ):
            app._set_formats(
                [video_fmt, audio_fmt],
                fetch_url="https://example.com/watch?v=123",
                request_id=11,
                preview_title="Sample title",
            )

        self.assertEqual(app.preview_title_var.get(), "Sample title")


class TestUiEventQueue(unittest.TestCase):
    def test_posted_callbacks_run_in_drain_cycle(self) -> None:
        app = object.__new__(YtDlpGui)
        app._closing = False
        app._ui_event_queue = queue.Queue()
        app._ui_event_after_id = None
        app._log = lambda _msg: None
        scheduled: list[tuple[int, object]] = []
        app._safe_after = lambda delay, callback: scheduled.append((delay, callback)) or "after-1"

        calls: list[int] = []
        app._post_ui(calls.append, 42)
        app._drain_ui_events()

        self.assertEqual(calls, [42])
        self.assertEqual(app._ui_event_after_id, "after-1")
        self.assertEqual(scheduled[0][0], UI_EVENT_POLL_MS)

    def test_drain_ui_events_limits_batch_and_reschedules_immediately(self) -> None:
        app = object.__new__(YtDlpGui)
        app._closing = False
        app._ui_event_queue = queue.Queue()
        app._ui_event_after_id = None
        app._log = lambda _msg: None
        scheduled: list[tuple[int, object]] = []
        app._safe_after = lambda delay, callback: scheduled.append((delay, callback)) or "after-batch"

        calls: list[int] = []
        app._post_ui(calls.append, 1)
        app._post_ui(calls.append, 2)

        with patch("gui.app.UI_EVENT_MAX_PER_TICK", 1):
            app._drain_ui_events()

        self.assertEqual(calls, [1])
        self.assertEqual(scheduled[-1][0], 0)
        self.assertEqual(app._ui_event_queue.qsize(), 1)


class TestCodecPreferenceMatching(unittest.TestCase):
    def test_codec_match_accepts_h264_alias_for_avc1(self) -> None:
        self.assertTrue(YtDlpGui._codec_matches_preference("h264", "avc1"))
        self.assertTrue(YtDlpGui._codec_matches_preference("avc1.640028", "avc1"))

    def test_codec_match_accepts_av1_alias_for_av01(self) -> None:
        self.assertTrue(YtDlpGui._codec_matches_preference("av1", "av01"))
        self.assertTrue(YtDlpGui._codec_matches_preference("av01.0.08M.08", "av01"))

    def test_codec_match_rejects_different_codecs(self) -> None:
        self.assertFalse(YtDlpGui._codec_matches_preference("vp9", "avc1"))
        self.assertFalse(YtDlpGui._codec_matches_preference("h264", "av01"))


class TestFormatCacheBounded(unittest.TestCase):
    def test_cache_entry_is_bounded_with_eviction(self) -> None:
        app = object.__new__(YtDlpGui)
        app.formats = FormatState()

        for idx in range(FORMAT_CACHE_MAX_ENTRIES + 5):
            app._cache_formats_entry(f"url-{idx}", {"video_labels": [str(idx)]})

        self.assertEqual(len(app.formats.cache), FORMAT_CACHE_MAX_ENTRIES)
        self.assertNotIn("url-0", app.formats.cache)
        self.assertIn(f"url-{FORMAT_CACHE_MAX_ENTRIES + 4}", app.formats.cache)

    def test_touch_cached_url_promotes_key(self) -> None:
        app = object.__new__(YtDlpGui)
        app.formats = FormatState()
        app.formats.cache = {
            "url-a": {"video_labels": []},
            "url-b": {"video_labels": []},
            "url-c": {"video_labels": []},
        }
        app._touch_cached_url("url-a")
        self.assertEqual(list(app.formats.cache.keys())[-1], "url-a")

    def test_cache_entry_is_snapshot_not_shared_reference(self) -> None:
        app = object.__new__(YtDlpGui)
        app.formats = FormatState()
        src = {
            "video_labels": ["v1"],
            "video_lookup": {"v1": {"format_id": "1"}},
            "audio_labels": ["a1"],
            "audio_lookup": {"a1": {"format_id": "2"}},
        }
        app._cache_formats_entry("url-a", src)
        src["video_labels"].append("mutated")
        src["video_lookup"]["v2"] = {"format_id": "3"}
        self.assertEqual(app.formats.cache["url-a"]["video_labels"], ["v1"])
        self.assertNotIn("v2", app.formats.cache["url-a"]["video_lookup"])

    def test_load_cached_formats_copies_values(self) -> None:
        app = object.__new__(YtDlpGui)
        app.formats = FormatState()
        app.preview_title_var = _Var("")
        app._touch_cached_url = Mock()
        app._reset_format_selections = Mock()
        app._apply_mode_formats = Mock()
        app._update_controls_state = Mock()
        app.status_var = _Var("Idle")
        cached = {
            "video_labels": ["v1"],
            "video_lookup": {"v1": {"format_id": "1"}},
            "audio_labels": ["a1"],
            "audio_lookup": {"a1": {"format_id": "2"}},
        }
        app._load_cached_formats("url-a", cached)
        cached["video_labels"].append("mutated")
        cached["video_lookup"]["v2"] = {"format_id": "3"}
        self.assertEqual(app.formats.video_labels, ["v1"])
        self.assertNotIn("v2", app.formats.video_lookup)


class TestWorkerSnapshotPaths(unittest.TestCase):
    def test_run_download_uses_snapshot_inputs_and_posts_finish(self) -> None:
        app = object.__new__(YtDlpGui)
        app._cancel_event = None
        app._log = lambda _msg: None
        posted: list[tuple[object, tuple]] = []

        def on_progress(update: dict) -> None:
            return None

        def on_finish() -> None:
            return None

        app._on_progress_update = on_progress
        app._on_finish = on_finish
        app._post_ui = lambda callback, *args, **kwargs: posted.append((callback, args))

        def _fake_run_download(**kwargs) -> None:
            kwargs["update_progress"]({"status": "downloading", "percent": 55.0})

        with patch("gui.app.download.run_download", side_effect=_fake_run_download) as mock_run:
            app._run_download(
                url="https://example.com/video",
                output_dir=Path("/tmp/out"),
                fmt_label="Video Label",
                fmt_info={"format_id": "22"},
                format_filter="webm",
                playlist_enabled=True,
                playlist_items_raw="1, 2, 3",
                convert_to_mp4=True,
                custom_filename="Renamed File",
            )

        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["format_filter"], "webm")
        self.assertTrue(kwargs["convert_to_mp4"])
        self.assertTrue(kwargs["playlist_enabled"])
        self.assertEqual(kwargs["playlist_items"], "1,2,3")
        self.assertEqual(kwargs["custom_filename"], "Renamed File")
        self.assertEqual(kwargs["network_timeout_s"], 20)
        self.assertEqual(kwargs["network_retries"], 1)
        self.assertEqual(kwargs["retry_backoff_s"], 1.5)
        self.assertEqual(posted[0][0], on_progress)
        self.assertEqual(posted[-1][0], on_finish)


class TestAdvancedOptionsAndHistory(unittest.TestCase):
    def test_snapshot_download_options_parses_and_clamps(self) -> None:
        app = object.__new__(YtDlpGui)
        app.mode_var = _Var("video")
        app.subtitle_languages_var = _Var("en, es, en")
        app.write_subtitles_var = _Var(True)
        app.embed_subtitles_var = _Var(True)
        app.audio_language_var = _Var(" es ")
        app.custom_filename_var = _Var("  my clip.mp4  ")
        app.network_timeout_var = _Var("999")
        app.network_retries_var = _Var("2")
        app.retry_backoff_var = _Var("0.5")

        options = app._snapshot_download_options()
        self.assertEqual(options["network_timeout_s"], 300)
        self.assertEqual(options["network_retries"], 2)
        self.assertEqual(options["retry_backoff_s"], 0.5)
        self.assertEqual(options["subtitle_languages"], ["en", "es"])
        self.assertTrue(options["write_subtitles"])
        self.assertTrue(options["embed_subtitles"])
        self.assertEqual(options["audio_language"], "es")
        self.assertEqual(options["custom_filename"], "my clip")

    def test_record_download_output_deduplicates_paths(self) -> None:
        app = object.__new__(YtDlpGui)
        app.download_history = []
        app._history_seen_paths = set()
        app._refresh_history_panel = Mock()

        app._record_download_output(Path("/tmp/a.mp4"), "https://example.com/video")
        app._record_download_output(Path("/tmp/a.mp4"), "https://example.com/video")
        app._record_download_output(Path("/tmp/b.mp4"), "https://example.com/video2")

        self.assertEqual(len(app.download_history), 2)
        self.assertEqual(app.download_history[0]["name"], "b.mp4")
        self.assertEqual(app.download_history[1]["name"], "a.mp4")
        self.assertGreaterEqual(app._refresh_history_panel.call_count, 2)

    def test_capture_queue_settings_includes_estimated_size_and_advanced_options(self) -> None:
        app = object.__new__(YtDlpGui)
        app.mode_var = _Var("video")
        app.format_filter_var = _Var("mp4")
        app.codec_filter_var = _Var("avc1 (H.264)")
        app.convert_to_mp4_var = _Var(False)
        app.format_var = _Var("Video 1080p")
        app.output_dir_var = _Var("/tmp/out")
        app.playlist_items_var = _Var("")
        app.subtitle_languages_var = _Var("en,es")
        app.write_subtitles_var = _Var(True)
        app.embed_subtitles_var = _Var(False)
        app.audio_language_var = _Var("en")
        app.custom_filename_var = _Var("Queued Name")
        app.network_timeout_var = _Var("20")
        app.network_retries_var = _Var("1")
        app.retry_backoff_var = _Var("1.5")
        app.formats = FormatState()
        app.formats.filtered_lookup = {
            "Video 1080p": {"format_id": "137", "filesize_approx": 3 * 1024 * 1024}
        }

        settings = app._capture_queue_settings()
        self.assertEqual(settings["estimated_size"], "3.0 MiB")
        self.assertEqual(settings["subtitle_languages"], ["en", "es"])
        self.assertEqual(settings["network_retries"], 1)
        self.assertEqual(settings["audio_language"], "en")
        self.assertEqual(settings["custom_filename"], "Queued Name")

    def test_export_diagnostics_writes_report_file(self) -> None:
        app = object.__new__(YtDlpGui)
        app._log = Mock()
        app.status_var = _Var("Idle")
        app.simple_state_var = _Var("Idle")
        app.url_var = _Var("https://www.youtube.com/watch?v=abc123&t=45")
        app.mode_var = _Var("video")
        app.format_filter_var = _Var("mp4")
        app.codec_filter_var = _Var("avc1 (H.264)")
        app.format_var = _Var("1080p")
        app.queue_items = [{"url": "https://example.com/a", "settings": {"mode": "video"}}]
        app.queue_active = False
        app.is_downloading = False
        app.formats = FormatState()
        app.formats.preview_title = "Example Video"
        app.download_history = [
            {
                "timestamp": "2026-02-17 12:00:00",
                "name": "a.mp4",
                "path": "/tmp/a.mp4",
                "source_url": "https://www.youtube.com/watch?v=abc123&token=secret",
            }
        ]
        app.logs = Mock()
        app.logs.get_text.return_value = "line one\nline two"
        app._snapshot_download_options = Mock(
            return_value={
                "network_timeout_s": 20,
                "network_retries": 1,
                "retry_backoff_s": 1.5,
                "write_subtitles": False,
                "embed_subtitles": False,
                "subtitle_languages": [],
                "audio_language": "",
                "custom_filename": "",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "gui.app.messagebox.showinfo"
        ) as info_mock:
            app.output_dir_var = _Var(tmpdir)
            app._export_diagnostics()

            exported = sorted(Path(tmpdir).glob("yt-dlp-gui-diagnostics-*.txt"))
            self.assertEqual(len(exported), 1)
            report = exported[0].read_text(encoding="utf-8")
            self.assertIn("generated_at=", report)
            self.assertIn("[logs]", report)
            self.assertIn("line one", report)
            self.assertIn("watch?v=abc123", report)
            self.assertNotIn("token=secret", report)
            info_mock.assert_called_once()


class TestQueueMutationLockout(unittest.TestCase):
    def test_queue_mutations_blocked_while_active(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = True
        app.queue_index = 0
        app.queue_items = [
            {"url": "https://example.com/a"},
            {"url": "https://example.com/b"},
        ]
        app._queue_refresh = Mock()
        app._update_controls_state = Mock()

        app._queue_remove_selected([0])
        app._queue_move_up([1])
        app._queue_move_down([0])
        app._queue_clear()

        self.assertEqual(
            app.queue_items,
            [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}],
        )
        app._queue_refresh.assert_not_called()
        app._update_controls_state.assert_not_called()

    def test_queue_refresh_passes_editable_state(self) -> None:
        class _QueuePanel:
            def __init__(self) -> None:
                self.calls: list[tuple[list[dict], int | None, bool]] = []

            def refresh(
                self, items: list[dict], active_index: int | None = None, editable: bool = True
            ) -> None:
                self.calls.append((items, active_index, editable))

        app = object.__new__(YtDlpGui)
        app.queue_panel = _QueuePanel()
        app.queue_items = [{"url": "x"}, {"url": "y"}]
        app.queue_active = True
        app.queue_index = 1
        app._queue_refresh()

        items, active_index, editable = app.queue_panel.calls[-1]
        self.assertEqual(items, app.queue_items)
        self.assertEqual(active_index, 1)
        self.assertFalse(editable)


class TestQueueStartStability(unittest.TestCase):
    def test_start_next_queue_item_skips_empty_urls(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = True
        app.queue_index = 0
        app.queue_items = [
            {"url": ""},
            {"url": "   "},
            {"url": "https://example.com/ok", "settings": {"mode": "video"}},
        ]
        app._finish_queue = Mock()
        app._log = Mock()
        app._queue_refresh = Mock()
        app.output_dir_var = _Var("/tmp/out")

        started = {"called": False}

        class _FakeThread:
            def __init__(self, *, target, kwargs, daemon):
                self.target = target
                self.kwargs = kwargs
                self.daemon = daemon

            def start(self):
                started["called"] = True

        with patch("gui.app.threading.Thread", side_effect=lambda **kw: _FakeThread(**kw)):
            app._start_next_queue_item()

        self.assertEqual(app.queue_index, 2)
        self.assertTrue(started["called"])
        app._finish_queue.assert_not_called()

    def test_run_queue_download_posts_error_flag_for_failed_item(self) -> None:
        app = object.__new__(YtDlpGui)
        app._cancel_event = None
        app._log = lambda _msg: None
        app.progress_item_var = _Var("—")
        posted: list[tuple[object, tuple]] = []
        app._post_ui = lambda callback, *args, **kwargs: posted.append((callback, args))

        def _on_finish_flag(*_args, **_kwargs) -> None:
            return None

        app._on_queue_item_finish = _on_finish_flag
        app._on_progress_update = lambda _payload: None
        app._resolve_format_for_url = lambda _url, _settings: {
            "title": "Video",
            "is_playlist": False,
            "fmt_info": {"format_id": "22"},
            "fmt_label": "Label",
            "format_filter": "mp4",
        }

        with patch("gui.app.download.run_download", return_value="error"):
            app._run_queue_download(
                url="https://example.com/video",
                settings={"output_dir": "/tmp/out"},
                index=1,
                total=3,
                default_output_dir="/tmp/out",
            )

        self.assertEqual(posted[-1][0], _on_finish_flag)
        self.assertEqual(posted[-1][1], (True, False))

    def test_run_queue_download_posts_cancelled_flag_for_cancelled_item(self) -> None:
        app = object.__new__(YtDlpGui)
        app._cancel_event = None
        app._log = lambda _msg: None
        app.progress_item_var = _Var("—")
        posted: list[tuple[object, tuple]] = []
        app._post_ui = lambda callback, *args, **kwargs: posted.append((callback, args))
        app._on_queue_item_finish = lambda *_args, **_kwargs: None
        app._on_progress_update = lambda _payload: None
        app._resolve_format_for_url = lambda _url, _settings: {
            "title": "Video",
            "is_playlist": False,
            "fmt_info": {"format_id": "22"},
            "fmt_label": "Label",
            "format_filter": "mp4",
        }

        with patch("gui.app.download.run_download", return_value="cancelled"):
            app._run_queue_download(
                url="https://example.com/video",
                settings={"output_dir": "/tmp/out"},
                index=1,
                total=3,
                default_output_dir="/tmp/out",
            )

        self.assertEqual(posted[-1][1], (False, True))

    def test_run_queue_download_passes_custom_filename(self) -> None:
        app = object.__new__(YtDlpGui)
        app._cancel_event = None
        app._log = lambda _msg: None
        app.progress_item_var = _Var("—")
        posted: list[tuple[object, tuple]] = []
        app._post_ui = lambda callback, *args, **kwargs: posted.append((callback, args))
        app._on_queue_item_finish = lambda *_args, **_kwargs: None
        app._on_progress_update = lambda _payload: None
        app._resolve_format_for_url = lambda _url, _settings: {
            "title": "Video",
            "is_playlist": False,
            "fmt_info": {"format_id": "22"},
            "fmt_label": "Label",
            "format_filter": "mp4",
        }

        with patch("gui.app.download.run_download", return_value="success") as mock_run:
            app._run_queue_download(
                url="https://example.com/video",
                settings={"output_dir": "/tmp/out", "custom_filename": "Queued Name"},
                index=1,
                total=3,
                default_output_dir="/tmp/out",
            )

        self.assertEqual(
            mock_run.call_args.kwargs.get("custom_filename"),
            "Queued Name",
        )


class TestQueueCompletionFlow(unittest.TestCase):
    def test_on_queue_item_finish_continues_to_next_item_after_error(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = True
        app.queue_index = 0
        app.queue_items = [{"url": "a"}, {"url": "b"}]
        app._queue_failed_items = 0
        app._cancel_requested = False
        app._reset_progress_summary = Mock()
        app._start_next_queue_item = Mock()
        app._finish_queue = Mock()
        app._log = lambda _msg: None

        app._on_queue_item_finish(had_error=True, cancelled=False)

        self.assertEqual(app._queue_failed_items, 1)
        self.assertEqual(app.queue_index, 1)
        app._reset_progress_summary.assert_called_once()
        app._start_next_queue_item.assert_called_once()
        app._finish_queue.assert_not_called()

    def test_on_queue_item_finish_ignores_late_callback_when_inactive(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = False
        app.queue_index = None
        app._queue_failed_items = 0
        app._finish_queue = Mock()

        app._on_queue_item_finish(had_error=True, cancelled=False)

        self.assertEqual(app._queue_failed_items, 0)
        app._finish_queue.assert_not_called()

    def test_on_queue_item_finish_cancelled_stops_queue(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = True
        app.queue_index = 0
        app.queue_items = [{"url": "a"}, {"url": "b"}]
        app._queue_failed_items = 0
        app._cancel_requested = False
        app._finish_queue = Mock()
        app._log = Mock()

        app._on_queue_item_finish(had_error=False, cancelled=True)

        self.assertTrue(app._cancel_requested)
        app._log.assert_called_with("[queue] cancelled")
        app._finish_queue.assert_called_once_with(cancelled=True)

    def test_finish_queue_logs_cancelled_state(self) -> None:
        app = object.__new__(YtDlpGui)
        app.queue_active = True
        app.queue_index = 1
        app.queue_settings = {"x": 1}
        app._queue_failed_items = 2
        app.is_downloading = True
        app._show_progress_item = True
        app._cancel_requested = True
        app._cancel_event = threading.Event()
        app.simple_state_var = _Var("Downloading queue")
        app.status_var = _Var("Downloading queue...")
        app._reset_progress_summary = Mock()
        app._update_controls_state = Mock()
        app._queue_refresh = Mock()
        app._log = Mock()

        app._finish_queue(cancelled=True)

        app._log.assert_called_with("[queue] stopped by cancellation")
        self.assertEqual(app.simple_state_var.get(), "Idle")
        self.assertEqual(app.status_var.get(), "Idle")
        self.assertFalse(app.queue_active)


class TestCloseBehavior(unittest.TestCase):
    def test_on_close_respects_cancel_confirmation(self) -> None:
        app = object.__new__(YtDlpGui)
        app.is_downloading = True
        app._closing = False
        app._cancel_event = threading.Event()
        app._active_fetch_request_id = 1
        app._cancel_requested = False
        app._cancel_after = Mock()
        app.logs = Mock()
        app.queue_panel = Mock()
        app.root = Mock()
        app.formats = FormatState()
        app._ui_event_queue = queue.Queue()
        app._ui_event_queue.put(("x", (), {}))

        with patch("gui.app.messagebox.askokcancel", return_value=False):
            app._on_close()

        self.assertFalse(app._closing)
        self.assertFalse(app._cancel_requested)
        app._cancel_after.assert_not_called()
        app.logs.shutdown.assert_not_called()
        app.queue_panel.shutdown.assert_not_called()
        app.root.destroy.assert_not_called()

    def test_on_close_cancels_and_shuts_down(self) -> None:
        app = object.__new__(YtDlpGui)
        app.is_downloading = True
        app._closing = False
        app._cancel_event = threading.Event()
        app._active_fetch_request_id = 3
        app._cancel_after = Mock()
        app.logs = Mock()
        app.queue_panel = Mock()
        app.root = Mock()
        app.formats = FormatState()
        app._ui_event_queue = queue.Queue()
        app._ui_event_queue.put(("x", (), {}))
        app._cancel_requested = False

        with patch("gui.app.messagebox.askokcancel", return_value=True):
            app._on_close()

        self.assertTrue(app._closing)
        self.assertTrue(app._cancel_requested)
        self.assertTrue(app._cancel_event.is_set())
        self.assertIsNone(app._active_fetch_request_id)
        self.assertTrue(app._ui_event_queue.empty())
        app.logs.shutdown.assert_called_once()
        app.queue_panel.shutdown.assert_called_once()
        app.root.destroy.assert_called_once()

    def test_on_close_ignores_shutdown_errors(self) -> None:
        app = object.__new__(YtDlpGui)
        app.is_downloading = False
        app._closing = False
        app._cancel_event = None
        app._active_fetch_request_id = 3
        app._cancel_requested = False
        app._cancel_after = Mock()
        app.logs = Mock()
        app.logs.shutdown.side_effect = RuntimeError("logs boom")
        app.queue_panel = Mock()
        app.queue_panel.shutdown.side_effect = RuntimeError("queue boom")
        app.root = Mock()
        app.root.destroy.side_effect = RuntimeError("destroy boom")
        app.formats = FormatState()
        app._ui_event_queue = queue.Queue()
        app._ui_event_queue.put(("x", (), {}))

        app._on_close()

        self.assertTrue(app._closing)
        self.assertTrue(app._ui_event_queue.empty())
        app.logs.shutdown.assert_called_once()
        app.queue_panel.shutdown.assert_called_once()
        app.root.destroy.assert_called_once()


class TestOutputDirValidation(unittest.TestCase):
    def test_ensure_output_dir_handles_mkdir_failure(self) -> None:
        app = object.__new__(YtDlpGui)
        app.status_var = _Var("Idle")
        app._log = Mock()

        with patch("gui.app.Path.mkdir", side_effect=PermissionError("denied")), patch(
            "gui.app.messagebox.showerror"
        ) as showerror:
            result = app._ensure_output_dir("/tmp/locked")

        self.assertIsNone(result)
        self.assertEqual(app.status_var.get(), "Output folder unavailable")
        app._log.assert_called_once()
        showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
