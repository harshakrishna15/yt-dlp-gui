import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import settings_store


class TestSettingsStore(unittest.TestCase):
    def test_load_settings_returns_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch.dict(
                os.environ, {"YT_DLP_GUI_SETTINGS_PATH": str(settings_path)}
            ):
                loaded = settings_store.load_settings(default_output_dir="/tmp/out")
        self.assertEqual(loaded["output_dir"], "/tmp/out")
        self.assertEqual(loaded["ui_layout"], "Simple")
        self.assertEqual(loaded["concurrent_fragments"], "4")
        self.assertFalse(loaded["open_folder_after_download"])

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "prefs.json"
            with patch.dict(
                os.environ, {"YT_DLP_GUI_SETTINGS_PATH": str(settings_path)}
            ):
                ok = settings_store.save_settings(
                    {
                        "output_dir": "/tmp/downloads",
                        "subtitle_languages": "en,es",
                        "write_subtitles": True,
                        "network_timeout": "18",
                        "network_retries": "3",
                        "retry_backoff": "2.5",
                        "concurrent_fragments": "3",
                        "ui_layout": "Classic",
                        "open_folder_after_download": True,
                    },
                    default_output_dir="/tmp/default",
                )
                loaded = settings_store.load_settings(
                    default_output_dir="/tmp/default"
                )
        self.assertTrue(ok)
        self.assertEqual(loaded["output_dir"], "/tmp/downloads")
        self.assertEqual(loaded["subtitle_languages"], "en,es")
        self.assertTrue(loaded["write_subtitles"])
        self.assertEqual(loaded["network_timeout"], "18")
        self.assertEqual(loaded["network_retries"], "3")
        self.assertEqual(loaded["retry_backoff"], "2.5")
        self.assertEqual(loaded["concurrent_fragments"], "3")
        self.assertEqual(loaded["ui_layout"], "Classic")
        self.assertTrue(loaded["open_folder_after_download"])

    def test_load_settings_sanitizes_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(
                (
                    "{"
                    '"ui_layout":"broken",'
                    '"network_timeout":"",'
                    '"network_retries":"",'
                    '"retry_backoff":"",'
                    '"concurrent_fragments":"999",'
                    '"open_folder_after_download":"yes"'
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"YT_DLP_GUI_SETTINGS_PATH": str(settings_path)}
            ):
                loaded = settings_store.load_settings(default_output_dir="/tmp/default")
        defaults = settings_store.default_settings(default_output_dir="/tmp/default")
        self.assertEqual(loaded["ui_layout"], "Simple")
        self.assertEqual(loaded["network_timeout"], defaults["network_timeout"])
        self.assertEqual(loaded["network_retries"], defaults["network_retries"])
        self.assertEqual(loaded["retry_backoff"], defaults["retry_backoff"])
        self.assertEqual(loaded["concurrent_fragments"], "4")
        self.assertTrue(loaded["open_folder_after_download"])


if __name__ == "__main__":
    unittest.main()
