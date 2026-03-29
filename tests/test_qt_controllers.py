from __future__ import annotations

import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from _yt_dlp_stub import ensure_yt_dlp_stub

ensure_yt_dlp_stub()

from gui.qt.controllers import RunQueueController, RunQueueState, SourceController, SourceState
from gui.qt.ports import SideEffectPorts


class FakeLineEdit:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def text(self) -> str:
        return self._value

    def setText(self, value: str) -> None:
        self._value = str(value)

    def clear(self) -> None:
        self._value = ""

    def blockSignals(self, _blocked: bool) -> None:
        return


class FakeStatusValue:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def text(self) -> str:
        return self._value

    def setText(self, value: str) -> None:
        self._value = str(value)


class FakeTimer:
    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0
        self.active = False

    def start(self) -> None:
        self.starts += 1
        self.active = True

    def stop(self) -> None:
        self.stops += 1
        self.active = False


class FakeCombo:
    def __init__(self) -> None:
        self.current_index = 0
        self.clear_calls = 0

    def blockSignals(self, _blocked: bool) -> None:
        return

    def setCurrentIndex(self, index: int) -> None:
        self.current_index = int(index)

    def clear(self) -> None:
        self.clear_calls += 1


class FakeCheckBox:
    def __init__(self, checked: bool = False) -> None:
        self._checked = bool(checked)

    def setChecked(self, checked: bool) -> None:
        self._checked = bool(checked)

    def isChecked(self) -> bool:
        return self._checked


class FakeSignal:
    def __init__(self) -> None:
        self.emits: list[tuple[object, ...]] = []

    def emit(self, *args: object) -> None:
        self.emits.append(args)


class RaisingRuntimeSignal(FakeSignal):
    def emit(self, *args: object) -> None:
        raise RuntimeError("Signal source has been deleted")


class FakeSignals:
    def __init__(self) -> None:
        self.formats_loaded = FakeSignal()
        self.progress = FakeSignal()
        self.log = FakeSignal()
        self.download_done = FakeSignal()
        self.queue_item_done = FakeSignal()


class FakeWindow:
    def __init__(self) -> None:
        self.url_edit = FakeLineEdit()
        self.output_dir_edit = FakeLineEdit("/tmp/out")
        self.playlist_items_edit = FakeLineEdit("")
        self.status_value = FakeStatusValue("")
        self._fetch_timer = FakeTimer()
        self.container_combo = FakeCombo()
        self.codec_combo = FakeCombo()
        self.convert_check = FakeCheckBox(False)
        self.format_combo = FakeCombo()
        self._signals = FakeSignals()

        self._is_downloading = False
        self._playlist_mode = False
        self._filtered_lookup: dict[str, dict] = {}
        self._last_error_log = ""
        self._preview_title_raw = ""

        self.status_updates: list[str] = []
        self.feedback_updates: list[tuple[str, str]] = []
        self.feedback_titles: list[str | None] = []
        self.logs: list[str] = []
        self.popups: list[tuple[str, str, bool]] = []
        self.preview_title = ""
        self.source_summary: dict[str, object] | None = None
        self.audio_languages: list[str] = []
        self.metrics_visible = False
        self.progress_resets = 0
        self.queue_progress_preps = 0
        self.queue_refreshes = 0
        self.controls_refreshes = 0
        self.source_detail_refreshes = 0
        self.current_item: tuple[str, str] = ("-", "-")
        self.open_output_calls = 0
        self.close_after_cancel_calls = 0
        self.edited_queue_items: list[tuple[int, dict[str, object]]] = []
        self.cleared_queue_edit_mode = 0
        self.pending_queue_edit_apply_calls = 0
        self.post_download_output_dir: Path | None = None
        self.captured_queue_settings = {
            "mode": "audio",
            "format_filter": "mp3",
            "format_label": "High",
        }
        self.default_output_dir = "/tmp/default-downloads"

    def _set_status(self, text: str, *, log: bool = True) -> None:
        self.status_updates.append(str(text))
        self.status_value.setText(text)
        if log:
            self.logs.append(str(text))

    def _set_source_feedback(
        self,
        message: str,
        *,
        tone: str,
        title: str | None = None,
    ) -> None:
        self.feedback_updates.append((str(message), str(tone)))
        self.feedback_titles.append(str(title) if title is not None else None)

    def _set_mode_unselected(self) -> None:
        return

    def _set_combo_items(
        self,
        _combo: FakeCombo,
        _items: list[tuple[str, str]],
        *,
        keep_current: bool = True,
    ) -> None:
        return

    def _set_preview_title(self, title: str) -> None:
        self.preview_title = str(title)
        self._preview_title_raw = str(title)

    def _set_source_summary(self, summary: dict[str, object] | None) -> None:
        self.source_summary = dict(summary) if isinstance(summary, dict) else None

    def _set_audio_language_values(self, values: list[str]) -> None:
        self.audio_languages = list(values)

    def _update_source_details_visibility(self) -> None:
        self.source_detail_refreshes += 1

    def _update_controls_state(self) -> None:
        self.controls_refreshes += 1

    def _apply_mode_formats(self) -> None:
        return

    def _apply_pending_queue_edit_settings(self) -> None:
        self.pending_queue_edit_apply_calls += 1

    def _show_feedback_popup(self, *, title: str, message: str, critical: bool = False) -> None:
        self.popups.append((str(title), str(message), bool(critical)))

    def _clear_logs(self) -> None:
        self.logs.clear()

    def _reset_progress_summary(self) -> None:
        self.progress_resets += 1

    def _prepare_next_queue_item_progress(self) -> None:
        self.queue_progress_preps += 1

    def _set_post_download_output_dir(self, output_dir: Path) -> None:
        self.post_download_output_dir = Path(output_dir)

    def _clear_post_download_output_dir(self) -> None:
        self.post_download_output_dir = None

    def _set_metrics_visible(self, visible: bool) -> None:
        self.metrics_visible = bool(visible)

    def _selected_format_info(self) -> dict[str, object]:
        return {}

    def _selected_format_label(self) -> str:
        return "Best"

    def _current_container(self) -> str:
        return "mp4"

    def _snapshot_download_options(self) -> dict[str, object]:
        return {
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

    def _append_log(self, text: str) -> None:
        self.logs.append(str(text))

    def _capture_queue_settings(self) -> dict[str, object]:
        return dict(self.captured_queue_settings)

    def _default_output_dir(self) -> str:
        return self.default_output_dir

    def _refresh_queue_panel(self) -> None:
        self.queue_refreshes += 1

    def _edit_queue_item(self, row: int, item: dict[str, object]) -> None:
        self.edited_queue_items.append((int(row), dict(item)))

    def _clear_queue_item_edit_mode(self) -> None:
        self.cleared_queue_edit_mode += 1

    def _set_current_item_display(self, *, progress: str, title: str) -> None:
        self.current_item = (str(progress), str(title))

    def _maybe_open_output_folder(self) -> None:
        self.open_output_calls += 1

    def _maybe_close_after_cancel(self) -> None:
        self.close_after_cancel_calls += 1


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    def submit(
        self,
        target: object,
        /,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.calls.append((target, args, kwargs))


class FakeDialogs:
    def __init__(self) -> None:
        self.critical_calls: list[tuple[str, str]] = []
        self.warning_calls: list[tuple[str, str]] = []
        self.info_calls: list[tuple[str, str]] = []
        self.question_response = True

    def critical(self, _parent: object, title: str, message: str) -> None:
        self.critical_calls.append((str(title), str(message)))

    def warning(self, _parent: object, title: str, message: str) -> None:
        self.warning_calls.append((str(title), str(message)))

    def information(self, _parent: object, title: str, message: str) -> None:
        self.info_calls.append((str(title), str(message)))

    def question(
        self,
        _parent: object,
        _title: str,
        _message: str,
        *,
        default_yes: bool,
    ) -> bool:
        return bool(self.question_response if self.question_response is not None else default_yes)


class FakeFileDialogs:
    def pick_directory(self, _parent: object, _title: str) -> str:
        return ""


class FakeFilesystem:
    def __init__(self) -> None:
        self.ensure_dir_calls: list[Path] = []
        self.write_calls: list[tuple[Path, str, str]] = []

    def ensure_dir(self, path: Path) -> None:
        self.ensure_dir_calls.append(Path(path))

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        self.write_calls.append((Path(path), str(content), str(encoding)))


class FakeDesktop:
    def __init__(self) -> None:
        self.opened: list[Path] = []

    def open_path(self, path: Path) -> None:
        self.opened.append(Path(path))


class FakeClipboard:
    def __init__(self) -> None:
        self.value = ""

    def get_text(self) -> str:
        return self.value

    def set_text(self, value: str) -> None:
        self.value = str(value)


class FakeClock:
    def __init__(self, *, now_ts: float = 100.0) -> None:
        self._now_ts = float(now_ts)

    def now(self) -> datetime:
        return datetime(2025, 1, 2, 3, 4, 5)

    def now_ts(self) -> float:
        return self._now_ts


class FakeCancelEvents:
    def __init__(self) -> None:
        self.created = 0

    def new_event(self) -> threading.Event:
        self.created += 1
        return threading.Event()


def build_ports(*, executor: FakeExecutor | None = None) -> tuple[SideEffectPorts, FakeDialogs, FakeFilesystem, FakeClock]:
    dialogs = FakeDialogs()
    filesystem = FakeFilesystem()
    clock = FakeClock()
    ports = SideEffectPorts(
        dialogs=dialogs,
        file_dialogs=FakeFileDialogs(),
        filesystem=filesystem,
        desktop=FakeDesktop(),
        clipboard=FakeClipboard(),
        clock=clock,
        cancel_events=FakeCancelEvents(),
        worker_executor=executor or FakeExecutor(),
    )
    return ports, dialogs, filesystem, clock


class TestSourceController(unittest.TestCase):
    def test_on_url_changed_requires_explicit_analyze_action(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        state = SourceState()
        controller = SourceController(window, state=state, ports=ports)

        controller.on_url_changed()

        self.assertFalse(state.is_fetching)
        self.assertEqual(window._fetch_timer.starts, 0)
        self.assertFalse(window._fetch_timer.active)
        self.assertIn(
            (
                "URL ready. Click Analyze URL to load formats and preview details.",
                "neutral",
            ),
            window.feedback_updates,
        )

    def test_start_fetch_formats_sets_state_and_submits_worker(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        executor = FakeExecutor()
        ports, _dialogs, _filesystem, _clock = build_ports(executor=executor)
        state = SourceState()
        controller = SourceController(window, state=state, ports=ports)

        controller.start_fetch_formats()

        self.assertTrue(state.is_fetching)
        self.assertEqual(state.fetch_request_seq, 1)
        self.assertEqual(state.active_fetch_request_id, 1)
        self.assertEqual(window.status_value.text(), "Fetching formats...")
        self.assertEqual(len(executor.calls), 1)
        target, args, kwargs = executor.calls[0]
        self.assertEqual(target, controller.fetch_formats_worker)
        self.assertEqual(args, (1, "https://example.com/watch?v=abc"))
        self.assertEqual(kwargs, {})

    def test_on_formats_loaded_updates_source_state(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        executor = FakeExecutor()
        ports, _dialogs, _filesystem, _clock = build_ports(executor=executor)
        state = SourceState(active_fetch_request_id=9, is_fetching=True)
        controller = SourceController(window, state=state, ports=ports)

        payload = {
            "collections": {
                "video_labels": ["1080p"],
                "video_lookup": {"1080p": {"id": "v1"}},
                "audio_labels": ["128k"],
                "audio_lookup": {"128k": {"id": "a1"}},
                "audio_languages": ["en"],
            },
            "preview_title": "Example title",
            "source_summary": {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "Example Channel",
                "detail_one_text": "Formats ready",
                "detail_two_text": "12m 08s",
                "detail_three_text": "1 video format",
            },
        }
        controller.on_formats_loaded(
            request_id=9,
            url="https://example.com/watch?v=abc",
            payload=payload,
            error=False,
            is_playlist=False,
        )

        self.assertFalse(state.is_fetching)
        self.assertEqual(state.video_labels, ["1080p"])
        self.assertEqual(state.audio_labels, ["128k"])
        self.assertEqual(window.preview_title, "Example title")
        self.assertEqual(
            window.source_summary,
            {
                "badge_text": "VID",
                "eyebrow_text": "Video ready",
                "subtitle_text": "Example Channel",
                "detail_one_text": "Formats ready",
                "detail_two_text": "12m 08s",
                "detail_three_text": "1 video format",
            },
        )
        self.assertEqual(window.status_value.text(), "Formats loaded")

    def test_fetch_formats_worker_ignores_deleted_signal_source(self) -> None:
        window = FakeWindow()
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        state = SourceState()
        controller = SourceController(window, state=state, ports=ports)
        window._signals.log = RaisingRuntimeSignal()
        window._signals.formats_loaded = RaisingRuntimeSignal()

        with patch(
            "gui.qt.controllers.helpers.fetch_info",
            side_effect=RuntimeError("boom"),
        ):
            controller.fetch_formats_worker(1, "https://example.com/watch?v=abc")

    def test_on_formats_loaded_ignores_stale_request_id(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        state = SourceState(
            active_fetch_request_id=9,
            is_fetching=True,
            video_labels=["old-video"],
            video_lookup={"old-video": {"id": "v-old"}},
            audio_labels=["old-audio"],
            audio_lookup={"old-audio": {"id": "a-old"}},
        )
        controller = SourceController(window, state=state, ports=ports)

        controller.on_formats_loaded(
            request_id=8,
            url="https://example.com/watch?v=abc",
            payload={
                "collections": {
                    "video_labels": ["new-video"],
                    "video_lookup": {"new-video": {"id": "v-new"}},
                    "audio_labels": ["new-audio"],
                    "audio_lookup": {"new-audio": {"id": "a-new"}},
                },
                "preview_title": "New title",
            },
            error=False,
            is_playlist=False,
        )

        self.assertTrue(state.is_fetching)
        self.assertEqual(state.video_labels, ["old-video"])
        self.assertEqual(state.audio_labels, ["old-audio"])
        self.assertEqual(window.preview_title, "")

    def test_on_formats_loaded_deduplicates_error_popup_by_reason(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        window._last_error_log = "HTTP Error 403: Forbidden"
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        state = SourceState(active_fetch_request_id=3, is_fetching=True)
        controller = SourceController(window, state=state, ports=ports)

        controller.on_formats_loaded(
            request_id=3,
            url="https://example.com/watch?v=abc",
            payload={},
            error=True,
            is_playlist=False,
        )
        controller.on_formats_loaded(
            request_id=3,
            url="https://example.com/watch?v=abc",
            payload={},
            error=True,
            is_playlist=False,
        )

        self.assertEqual(len(window.popups), 1)
        self.assertTrue(state.last_formats_error_popup_key.startswith("https://example.com/watch?v=abc|"))


class TestRunQueueController(unittest.TestCase):
    def test_on_start_sets_single_run_state_and_submits_worker(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        window._filtered_lookup = {"Best": {"id": "x"}}
        executor = FakeExecutor()
        ports, dialogs, filesystem, _clock = build_ports(executor=executor)
        state = RunQueueState()
        controller = RunQueueController(window, state=state, ports=ports)

        request = {
            "url": "https://example.com/watch?v=abc",
            "output_dir": Path("/tmp/out"),
            "fmt_info": {},
            "fmt_label": "Best",
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
        with patch(
            "gui.qt.controllers.app_service.build_single_download_request",
            return_value=(request, False),
        ):
            controller.on_start()

        self.assertEqual(len(dialogs.critical_calls), 0)
        self.assertEqual(filesystem.ensure_dir_calls, [Path("/tmp/out")])
        self.assertTrue(state.is_downloading)
        self.assertFalse(state.cancel_requested)
        self.assertIsNotNone(state.cancel_event)
        self.assertEqual(state.run_state.value, "single")
        self.assertEqual(window.status_value.text(), "Downloading...")
        self.assertEqual(len(executor.calls), 1)
        target, args, kwargs = executor.calls[0]
        self.assertEqual(target, controller.run_single_download_worker)
        self.assertEqual(args, ())
        self.assertEqual(kwargs["request"], request)
        self.assertEqual(window.post_download_output_dir, Path("/tmp/out"))

    def test_on_start_uses_default_output_dir_when_field_blank(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        window.output_dir_edit.setText("")
        window._filtered_lookup = {"Best": {"id": "x"}}
        executor = FakeExecutor()
        ports, dialogs, filesystem, _clock = build_ports(executor=executor)
        state = RunQueueState()
        controller = RunQueueController(window, state=state, ports=ports)

        def _build_request(**kwargs: object) -> tuple[dict[str, object], bool]:
            return (
                {
                    "url": "https://example.com/watch?v=abc",
                    "output_dir": kwargs["output_dir"],
                    "fmt_info": {},
                    "fmt_label": "Best",
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
                },
                False,
            )

        with patch(
            "gui.qt.controllers.app_service.build_single_download_request",
            side_effect=_build_request,
        ) as mock_build_request:
            controller.on_start()

        self.assertEqual(dialogs.critical_calls, [])
        self.assertEqual(filesystem.ensure_dir_calls, [Path("/tmp/default-downloads")])
        self.assertEqual(
            mock_build_request.call_args.kwargs["output_dir"],
            Path("/tmp/default-downloads"),
        )
        self.assertEqual(window.post_download_output_dir, Path("/tmp/default-downloads"))

    def test_on_start_with_invalid_playlist_items_uses_dialog_port(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc&list=PL1")
        window._filtered_lookup = {"Best": {"id": "x"}}
        window._playlist_mode = True
        window.playlist_items_edit.setText("invalid-only")
        executor = FakeExecutor()
        ports, dialogs, filesystem, _clock = build_ports(executor=executor)
        state = RunQueueState()
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_start()

        self.assertFalse(state.is_downloading)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(filesystem.ensure_dir_calls, [Path("/tmp/out")])
        self.assertEqual(len(dialogs.critical_calls), 1)
        self.assertEqual(dialogs.critical_calls[0][0], "Invalid playlist items")

    def test_start_queue_download_sets_state_and_submits_queue_worker(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {
                    "url": "https://example.com/watch?v=abc",
                    "settings": {
                        "mode": "audio",
                        "format_filter": "mp3",
                        "format_label": "High",
                    },
                }
            ]
        )
        executor = FakeExecutor()
        ports, dialogs, _filesystem, clock = build_ports(executor=executor)
        clock._now_ts = 55.0
        controller = RunQueueController(window, state=state, ports=ports)

        controller.start_queue_download()

        self.assertEqual(dialogs.critical_calls, [])
        self.assertTrue(state.queue_active)
        self.assertEqual(state.queue_index, 0)
        self.assertTrue(state.is_downloading)
        self.assertTrue(state.show_progress_item)
        self.assertEqual(state.queue_started_ts, 55.0)
        self.assertEqual(window.status_value.text(), "Downloading queue...")
        self.assertEqual(window.current_item, ("1/1", "Resolving title..."))
        self.assertEqual(len(executor.calls), 1)
        target, args, kwargs = executor.calls[0]
        self.assertEqual(target, controller.run_queue_download_worker)
        self.assertEqual(args, ())
        self.assertEqual(kwargs["url"], "https://example.com/watch?v=abc")
        self.assertEqual(kwargs["index"], 1)
        self.assertEqual(kwargs["total"], 1)

    def test_on_start_prefers_queue_when_queue_items_exist(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("")
        state = RunQueueState(
            queue_items=[
                {
                    "url": "https://example.com/watch?v=queued",
                    "settings": {
                        "mode": "audio",
                        "format_filter": "mp3",
                        "format_label": "High",
                    },
                },
            ]
        )
        executor = FakeExecutor()
        ports, dialogs, _filesystem, clock = build_ports(executor=executor)
        clock._now_ts = 77.0
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_start()

        self.assertEqual(dialogs.critical_calls, [])
        self.assertTrue(state.queue_active)
        self.assertEqual(state.queue_index, 0)
        self.assertEqual(window.status_value.text(), "Downloading queue...")
        self.assertEqual(len(executor.calls), 1)
        target, args, kwargs = executor.calls[0]
        self.assertEqual(target, controller.run_queue_download_worker)
        self.assertEqual(args, ())
        self.assertEqual(kwargs["url"], "https://example.com/watch?v=queued")
        self.assertEqual(kwargs["index"], 1)
        self.assertEqual(kwargs["total"], 1)

    def test_queue_mutation_handlers_update_state_without_qt(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {"url": "a", "settings": {}},
                {"url": "b", "settings": {}},
                {"url": "c", "settings": {}},
            ]
        )
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_queue_move_up([1, 2])
        self.assertEqual([item.get("url") for item in state.queue_items], ["b", "c", "a"])
        controller.on_queue_remove_selected([1])
        self.assertEqual([item.get("url") for item in state.queue_items], ["b", "a"])
        controller.on_queue_reorder([1, 0])
        self.assertEqual([item.get("url") for item in state.queue_items], ["a", "b"])
        controller.on_queue_clear()
        self.assertEqual(state.queue_items, [])
        self.assertGreaterEqual(window.queue_refreshes, 3)

    def test_on_queue_edit_item_sets_edit_mode_and_delegates_to_window(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {
                    "url": "https://example.com/watch?v=abc",
                    "title": "Example title",
                    "settings": {"mode": "video", "format_filter": "mp4"},
                }
            ]
        )
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_queue_edit_item(0)

        self.assertEqual(state.editing_queue_index, 0)
        self.assertEqual(
            window.edited_queue_items,
            [
                (
                    0,
                    {
                        "url": "https://example.com/watch?v=abc",
                        "title": "Example title",
                        "settings": {"mode": "video", "format_filter": "mp4"},
                    },
                )
            ],
        )

    def test_on_add_to_queue_announces_position_and_queue_count(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        window._filtered_lookup = {"Best": {"id": "x"}}
        state = RunQueueState(
            queue_items=[
                {
                    "url": "https://example.com/watch?v=queued",
                    "settings": {
                        "mode": "audio",
                        "format_filter": "mp3",
                        "format_label": "High",
                    },
                }
            ]
        )
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_add_to_queue()

        self.assertEqual(len(state.queue_items), 2)
        self.assertEqual(state.queue_items[-1]["url"], "https://example.com/watch?v=abc")
        self.assertEqual(state.queue_items[-1].get("title", ""), "")
        self.assertEqual(window.status_value.text(), "Added to queue as item 2")
        self.assertEqual(
            window.feedback_updates[-1],
            (
                "Saved as queue item 2. Queue now has 2 items. Open Queue to review, or press Download to start it.",
                "success",
            ),
        )
        self.assertEqual(window.feedback_titles[-1], "Added to queue")

    def test_on_add_to_queue_preserves_preview_title(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=abc")
        window._filtered_lookup = {"Best": {"id": "x"}}
        window._preview_title_raw = "Example video title"
        state = RunQueueState()
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_add_to_queue()

        self.assertEqual(state.queue_items[0]["title"], "Example video title")

    def test_on_add_to_queue_updates_existing_edit_item(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("https://example.com/watch?v=updated")
        window._filtered_lookup = {"Best": {"id": "x"}}
        window._preview_title_raw = "Updated title"
        window.captured_queue_settings = {
            "mode": "video",
            "format_filter": "mp4",
            "codec_filter": "avc1",
            "format_label": "1080p",
        }
        state = RunQueueState(
            queue_items=[
                {
                    "url": "https://example.com/watch?v=old",
                    "title": "Old title",
                    "settings": {
                        "mode": "audio",
                        "format_filter": "mp3",
                        "format_label": "High",
                    },
                }
            ],
            editing_queue_index=0,
        )
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_add_to_queue()

        self.assertEqual(len(state.queue_items), 1)
        self.assertEqual(state.queue_items[0]["url"], "https://example.com/watch?v=updated")
        self.assertEqual(state.queue_items[0]["title"], "Updated title")
        self.assertEqual(state.queue_items[0]["settings"]["codec_filter"], "avc1")
        self.assertIsNone(state.editing_queue_index)
        self.assertEqual(window.cleared_queue_edit_mode, 1)
        self.assertEqual(window.feedback_titles[-1], "Queue item updated")

    def test_on_queue_item_done_prepares_next_item_without_full_progress_reset(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {"url": "https://example.com/watch?v=one", "settings": {}},
                {"url": "https://example.com/watch?v=two", "settings": {}},
            ],
            queue_active=True,
            queue_index=0,
            is_downloading=True,
            show_progress_item=True,
            cancel_event=threading.Event(),
        )
        ports, _dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_queue_item_done(had_error=False, cancelled=False)

        self.assertEqual(state.queue_index, 1)
        self.assertEqual(window.queue_progress_preps, 1)
        self.assertEqual(window.progress_resets, 0)
        self.assertEqual(window.current_item, ("2/2", "Resolving title..."))

    def test_on_start_with_missing_url_uses_dialog_port(self) -> None:
        window = FakeWindow()
        window.url_edit.setText("")
        window._filtered_lookup = {"Best": {"id": "x"}}
        ports, dialogs, _filesystem, _clock = build_ports(executor=FakeExecutor())
        state = RunQueueState()
        controller = RunQueueController(window, state=state, ports=ports)

        controller.on_start()

        self.assertFalse(state.is_downloading)
        self.assertEqual(len(dialogs.critical_calls), 1)

    def test_finish_queue_success_updates_status_and_opens_folder(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {"url": "https://example.com/watch?v=one", "settings": {}},
                {"url": "https://example.com/watch?v=two", "settings": {}},
            ],
            queue_active=True,
            queue_index=1,
            queue_failed_items=0,
            queue_started_ts=10.0,
            is_downloading=True,
            show_progress_item=True,
            cancel_requested=False,
            cancel_event=threading.Event(),
        )
        ports, _dialogs, _filesystem, clock = build_ports(executor=FakeExecutor())
        clock._now_ts = 20.0
        controller = RunQueueController(window, state=state, ports=ports)

        controller.finish_queue(cancelled=False)

        self.assertFalse(state.queue_active)
        self.assertFalse(state.is_downloading)
        self.assertFalse(state.show_progress_item)
        self.assertIsNone(state.queue_started_ts)
        self.assertEqual(window.status_value.text(), "Queue complete")
        self.assertEqual(window.open_output_calls, 1)
        self.assertTrue(any("[queue] finished successfully" in line for line in window.logs))

    def test_finish_queue_failed_shows_warning_popup(self) -> None:
        window = FakeWindow()
        window._last_error_log = "HTTP Error 429: Too many requests"
        state = RunQueueState(
            queue_items=[
                {"url": "https://example.com/watch?v=one", "settings": {}},
                {"url": "https://example.com/watch?v=two", "settings": {}},
                {"url": "https://example.com/watch?v=three", "settings": {}},
            ],
            queue_active=True,
            queue_index=2,
            queue_failed_items=2,
            queue_started_ts=30.0,
            is_downloading=True,
            show_progress_item=True,
            cancel_requested=False,
            cancel_event=threading.Event(),
        )
        ports, _dialogs, _filesystem, clock = build_ports(executor=FakeExecutor())
        clock._now_ts = 50.0
        controller = RunQueueController(window, state=state, ports=ports)

        controller.finish_queue(cancelled=False)

        self.assertEqual(window.status_value.text(), "Queue finished with errors")
        self.assertEqual(window.open_output_calls, 1)
        self.assertEqual(len(window.popups), 1)
        self.assertEqual(window.popups[0][0], "Queue finished with errors")
        self.assertFalse(window.popups[0][2])

    def test_finish_queue_cancelled_does_not_open_output_folder(self) -> None:
        window = FakeWindow()
        state = RunQueueState(
            queue_items=[
                {"url": "https://example.com/watch?v=one", "settings": {}},
                {"url": "https://example.com/watch?v=two", "settings": {}},
                {"url": "https://example.com/watch?v=three", "settings": {}},
            ],
            queue_active=True,
            queue_index=1,
            queue_failed_items=1,
            queue_started_ts=5.0,
            is_downloading=True,
            show_progress_item=True,
            cancel_requested=True,
            cancel_event=threading.Event(),
        )
        ports, _dialogs, _filesystem, clock = build_ports(executor=FakeExecutor())
        clock._now_ts = 9.0
        controller = RunQueueController(window, state=state, ports=ports)

        controller.finish_queue(cancelled=True)

        self.assertEqual(window.status_value.text(), "Queue cancelled")
        self.assertEqual(window.open_output_calls, 0)
        self.assertTrue(any("[queue] stopped by cancellation" in line for line in window.logs))


if __name__ == "__main__":
    unittest.main()
