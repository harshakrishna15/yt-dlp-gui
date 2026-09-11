import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import yt_dlp_cli, yt_dlp_helpers


class TestMetadataHelpers(unittest.TestCase):
    def test_development_fallback_runs_cancellable_python_subprocess(self):
        event = threading.Event()
        with (
            patch.object(yt_dlp_helpers.yt_dlp_binary, "resolve_yt_dlp_binary", return_value=None),
            patch.object(yt_dlp_helpers, "_import_yt_dlp"),
            patch.object(yt_dlp_cli, "fetch_info", return_value={"id": "test"}) as fetch,
        ):
            self.assertEqual(yt_dlp_helpers.fetch_info("test-url", cancel_event=event), {"id": "test"})
        fetch.assert_called_once_with(
            Path(sys.executable), "test-url", prefix_args=("-m", "yt_dlp"),
            cancel_event=event, on_status=None,
        )

    def test_frozen_app_does_not_launch_itself_if_engine_is_missing(self):
        with (
            patch.object(yt_dlp_helpers.yt_dlp_binary, "resolve_yt_dlp_binary", return_value=None),
            patch.object(sys, "frozen", True, create=True),
            patch.object(yt_dlp_cli, "fetch_info") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "Reinstall"):
                yt_dlp_helpers.fetch_info("test-url")
        fetch.assert_not_called()

    def test_cancelled_request_does_not_resolve_or_bootstrap_engine(self):
        event = threading.Event()
        event.set()
        with patch.object(yt_dlp_helpers.yt_dlp_binary, "resolve_yt_dlp_binary") as resolve:
            with self.assertRaises(yt_dlp_cli.MetadataCancelled):
                yt_dlp_helpers.fetch_info("test-url", cancel_event=event)
        resolve.assert_not_called()
