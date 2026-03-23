import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import settings_store


class TestSettingsStore(unittest.TestCase):
    def test_user_settings_path_uses_override_then_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "YT_DLP_GUI_SETTINGS_PATH": "~/custom/settings.json",
                "HOME": "/Users/tester",
            },
            clear=True,
        ):
            self.assertEqual(
                settings_store.user_settings_path(),
                Path("/Users/tester/custom/settings.json"),
            )
        with patch("gui.common.settings_store.Path.home", return_value=Path("/Users/tester")):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    settings_store.user_settings_path(),
                    Path("/Users/tester/.yt-dlp-gui/settings.json"),
                )

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

    def test_save_settings_returns_false_on_write_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            with patch.dict(
                os.environ, {"YT_DLP_GUI_SETTINGS_PATH": str(settings_path)}
            ), patch(
                "pathlib.Path.write_text",
                side_effect=OSError("write failed"),
            ):
                ok = settings_store.save_settings(
                    {
                        "output_dir": "/tmp/downloads",
                        "edit_friendly_encoder": "auto",
                        "open_folder_after_download": False,
                    },
                    default_output_dir="/tmp/default",
                )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
