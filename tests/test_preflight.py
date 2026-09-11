import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gui.services import preflight, app_service
from gui.common.yt_dlp_cli import MetadataCancelled


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "downloads"
        self.request = {"output_dir": self.output, "format_filter": "mp4",
                        "fmt_info": {"filesize": 1000, "vcodec": "h264", "acodec": "aac"}}
        tools = patch.object(preflight, "resolve_binary", return_value=(Path("/tool"), "test"))
        tools.start()
        self.addCleanup(tools.stop)

    def test_writable_destination_created_without_probe_files_left(self):
        preflight.check_download(self.request, None)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_known_size_includes_processing_headroom(self):
        with patch.object(preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=2000)):
            with self.assertRaisesRegex(OSError, "Insufficient free disk space"):
                preflight.check_download(self.request, None)
        with patch.object(preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=3001)):
            preflight.check_download(self.request, None)

    def test_unknown_size_does_not_invent_a_requirement(self):
        self.request["fmt_info"] = {}
        with patch.object(preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=1)):
            preflight.check_download(self.request, None)

    def test_missing_tools_fail_before_creating_destination(self):
        with patch.object(preflight, "resolve_binary", return_value=(None, "missing")):
            with self.assertRaisesRegex(RuntimeError, "missing: ffmpeg"):
                preflight.check_download(self.request, None)
        self.assertFalse(self.output.exists())

    def test_cancelled_preflight_has_no_filesystem_side_effects(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(MetadataCancelled):
            preflight.check_download(self.request, event)
        self.assertFalse(self.output.exists())

    def test_permission_error_does_not_start_download(self):
        with patch.object(preflight.tempfile, "TemporaryFile", side_effect=PermissionError("denied")), patch.object(
            app_service.download, "run_download"
        ) as run:
            with self.assertRaises(PermissionError):
                app_service.run_download_request(request=self.request, cancel_event=None,
                                                 log=lambda _: None, update_progress=lambda _: None)
        run.assert_not_called()
