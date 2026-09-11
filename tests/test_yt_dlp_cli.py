from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import yt_dlp_cli


class _FakeProcess:
    def __init__(self, *, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode = returncode
        self.pid = 12345
        self.killed = False

    def poll(self) -> int:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def kill(self) -> None:
        self.killed = True


class TestYtDlpMetadataCli(unittest.TestCase):
    def test_fetch_info_uses_deterministic_json_command(self) -> None:
        payload = {"id": "abc123", "title": "Example"}
        completed = _FakeProcess(
            returncode=0,
            stdout=f"{json.dumps(payload)}\n",
            stderr="",
        )
        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=completed) as run:
            result = yt_dlp_cli.fetch_info(Path("/opt/yt-dlp"), "https://example.test/v")

        self.assertEqual(result, payload)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "/opt/yt-dlp")
        self.assertIn("--ignore-config", command)
        self.assertIn("--dump-single-json", command)
        self.assertIn("--skip-download", command)
        self.assertIn("--no-quiet", command)
        self.assertEqual(command[command.index("--socket-timeout") + 1], "15")
        self.assertEqual(command[command.index("--extractor-retries") + 1], "1")
        self.assertEqual(command[command.index("--playlist-items") + 1], "1")
        self.assertEqual(command[-2:], ["--", "https://example.test/v"])

    def test_fetch_info_surfaces_last_error_line(self) -> None:
        completed = _FakeProcess(
            returncode=1,
            stdout="",
            stderr="warning\nERROR: unsupported URL\n",
        )
        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "unsupported URL"):
                yt_dlp_cli.fetch_info(Path("/opt/yt-dlp"), "bad-url")

    def test_status_is_streamed_before_metadata_is_ready(self) -> None:
        received = []
        started = time.monotonic()
        result = yt_dlp_cli.fetch_info(
            Path(sys.executable), "test-url",
            prefix_args=("-u", "-c", 'import time; print("Downloading player"); time.sleep(0.4); print(\'{"id":"test"}\')'),
            on_status=lambda line: received.append((line, time.monotonic())),
        )
        self.assertEqual(result, {"id": "test"})
        self.assertEqual(received[0][0], "Downloading player")
        self.assertLess(received[0][1] - started, 1)
        self.assertGreater(time.monotonic() - received[0][1], 0.3)

    def test_cancel_terminates_and_reaps_live_process(self) -> None:
        cancelled = threading.Event()
        pids = []

        def cancel(line):
            pids.append(int(line))
            cancelled.set()

        started = time.monotonic()
        with self.assertRaises(yt_dlp_cli.MetadataCancelled):
            yt_dlp_cli.fetch_info(
                Path(sys.executable), "test-url", cancel_event=cancelled,
                prefix_args=("-u", "-c", 'import os,time; print(os.getpid()); time.sleep(30)'),
                on_status=cancel,
            )
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(len(pids), 1)
        if sys.platform != "win32":
            with self.assertRaises(ProcessLookupError):
                os.kill(pids[0], 0)

    def test_timeout_even_if_child_closes_output_pipes(self) -> None:
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            yt_dlp_cli.fetch_info(
                Path(sys.executable), "test-url", timeout=0.25,
                prefix_args=("-u", "-c", 'import os,time; os.close(1); os.close(2); time.sleep(30)'),
            )
        self.assertLess(time.monotonic() - started, 5)

    def test_pre_cancelled_lookup_never_starts_process(self) -> None:
        cancelled = threading.Event()
        cancelled.set()
        with patch.object(yt_dlp_cli.subprocess, "Popen") as popen:
            with self.assertRaises(yt_dlp_cli.MetadataCancelled):
                yt_dlp_cli.fetch_info(Path("yt-dlp"), "test-url", cancel_event=cancelled)
        popen.assert_not_called()

    def test_invalid_metadata_is_reported(self) -> None:
        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=_FakeProcess(stdout="{invalid}\n")):
            with self.assertRaisesRegex(RuntimeError, "invalid metadata"):
                yt_dlp_cli.fetch_info(Path("yt-dlp"), "test-url")


class TestYtDlpDownloadArguments(unittest.TestCase):
    def test_build_download_args_maps_existing_download_options(self) -> None:
        args = yt_dlp_cli.build_download_args(
            Path("/opt/yt-dlp"),
            url="https://example.test/playlist",
            options={
                "outtmpl": "/tmp/%(title)s.%(ext)s",
                "format": "137+bestaudio/best",
                "noplaylist": False,
                "merge_output_format": "mp4",
                "socket_timeout": 30,
                "retries": 10,
                "fragment_retries": 9,
                "extractor_retries": 5,
                "file_access_retries": 3,
                "concurrent_fragment_downloads": 4,
                "skip_unavailable_fragments": True,
                "continuedl": True,
                "postprocessors": [
                    {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
                    {"key": "EmbedThumbnail"},
                    {"key": "FFmpegEmbedSubtitle"},
                ],
                "postprocessor_args": ["-movflags", "+faststart"],
                "writethumbnail": True,
                "writesubtitles": True,
                "subtitleslangs": ["en", "es"],
                "format_sort": ["lang:en"],
                "ffmpeg_location": "/opt/ffmpeg",
                "playlist_items": "1-5,7,10-",
                "sleep_interval": 1.0,
                "max_sleep_interval": 2.5,
            },
        )

        def _value(option: str) -> str:
            return args[args.index(option) + 1]

        self.assertEqual(args[0], "/opt/yt-dlp")
        self.assertEqual(_value("--output"), "/tmp/%(title)s.%(ext)s")
        self.assertEqual(_value("--format"), "137+bestaudio/best")
        self.assertIn("--yes-playlist", args)
        self.assertEqual(_value("--merge-output-format"), "mp4")
        self.assertEqual(_value("--recode-video"), "mp4")
        self.assertIn("--embed-thumbnail", args)
        self.assertIn("--embed-subs", args)
        self.assertIn("--write-subs", args)
        self.assertIn("--write-auto-subs", args)
        self.assertEqual(_value("--sub-langs"), "en,es")
        self.assertEqual(_value("--playlist-items"), "1:5,7,10:")
        self.assertEqual(
            _value("--postprocessor-args"),
            "ffmpeg_o:-movflags +faststart",
        )
        self.assertEqual(args[-2:], ["--", "https://example.test/playlist"])

    def test_build_download_args_maps_audio_extraction(self) -> None:
        args = yt_dlp_cli.build_download_args(
            Path("yt-dlp"),
            url="https://example.test/audio",
            options={
                "noplaylist": True,
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
                ],
            },
        )

        self.assertIn("--no-playlist", args)
        self.assertIn("--extract-audio", args)
        self.assertEqual(args[args.index("--audio-format") + 1], "m4a")


class TestYtDlpProcessProtocol(unittest.TestCase):
    def test_process_protocol_reports_items_progress_outputs_and_logs(self) -> None:
        item = {"title": "Example", "playlist_index": 2, "playlist_count": 4}
        progress = {
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 100,
        }
        output = "/tmp/Example.mp4"
        stdout = "\n".join(
            (
                yt_dlp_cli.ITEM_PREFIX + json.dumps(item),
                yt_dlp_cli.PROGRESS_PREFIX + json.dumps(progress),
                yt_dlp_cli.OUTPUT_PREFIX + json.dumps(output),
                "ordinary yt-dlp output",
            )
        ) + "\n"
        process = _FakeProcess(stdout=stdout, stderr="a warning\n")
        updates: list[dict[str, object]] = []
        outputs: list[Path] = []
        logs: list[str] = []

        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=process):
            result = yt_dlp_cli.run_download_process(
                ["yt-dlp", "https://example.test/v"],
                cancel_event=threading.Event(),
                on_progress=updates.append,
                on_output=outputs.append,
                log=logs.append,
            )

        self.assertEqual(result.returncode, 0)
        self.assertFalse(result.cancelled)
        self.assertEqual(updates[0], {"status": "starting", "info_dict": item})
        self.assertEqual(updates[1]["status"], "downloading")
        self.assertEqual(updates[1]["info_dict"], item)
        self.assertEqual(outputs, [Path(output)])
        self.assertIn("ordinary yt-dlp output", logs)
        self.assertIn("a warning", logs)

    def test_cancel_event_terminates_process_tree(self) -> None:
        process = _FakeProcess()
        cancel_event = threading.Event()
        cancel_event.set()
        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=process):
            with patch.object(yt_dlp_cli, "_terminate_process_tree") as terminate:
                result = yt_dlp_cli.run_download_process(
                    ["yt-dlp", "https://example.test/v"],
                    cancel_event=cancel_event,
                    on_progress=lambda _payload: None,
                    on_output=lambda _path: None,
                    log=lambda _line: None,
                )

        self.assertTrue(result.cancelled)
        terminate.assert_called_once_with(process)

    def test_progress_callback_failure_terminates_process_before_propagating(self) -> None:
        stdout = yt_dlp_cli.PROGRESS_PREFIX + json.dumps({"status": "downloading"}) + "\n"
        process = _FakeProcess(stdout=stdout)

        def _raise(_payload: dict[str, object]) -> None:
            raise RuntimeError("callback failed")

        with patch.object(yt_dlp_cli.subprocess, "Popen", return_value=process):
            with patch.object(yt_dlp_cli, "_terminate_process_tree") as terminate:
                with self.assertRaisesRegex(RuntimeError, "callback failed"):
                    yt_dlp_cli.run_download_process(
                        ["yt-dlp", "https://example.test/v"],
                        cancel_event=None,
                        on_progress=_raise,
                        on_output=lambda _path: None,
                        log=lambda _line: None,
                    )

        terminate.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
