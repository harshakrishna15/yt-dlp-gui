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
        self.assertEqual(loaded["edit_friendly_encoder"], "auto")
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
                        "edit_friendly_encoder": "intel",
                        "open_folder_after_download": True,
                    },
                    default_output_dir="/tmp/default",
                )
                loaded = settings_store.load_settings(
                    default_output_dir="/tmp/default"
                )
        self.assertTrue(ok)
        self.assertEqual(loaded["output_dir"], "/tmp/downloads")
        self.assertEqual(loaded["edit_friendly_encoder"], "intel")
        self.assertTrue(loaded["open_folder_after_download"])

    def test_load_settings_sanitizes_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(
                (
                    "{"
                    '"output_dir":"   ",'
                    '"edit_friendly_encoder":"nvenc",'
                    '"open_folder_after_download":"yes"'
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"YT_DLP_GUI_SETTINGS_PATH": str(settings_path)}
            ):
                loaded = settings_store.load_settings(default_output_dir="/tmp/default")
        self.assertEqual(loaded["output_dir"], "/tmp/default")
        self.assertEqual(loaded["edit_friendly_encoder"], "nvidia")
        self.assertTrue(loaded["open_folder_after_download"])


if __name__ == "__main__":
    unittest.main()
