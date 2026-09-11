import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import app_data, settings_store, yt_dlp_binary


class TestAppData(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        overrides = patch.dict(os.environ, {
            "YT_DLP_GUI_SETTINGS_PATH": str(self.root / ".yt-dlp-gui" / "settings.json"),
            "YT_DLP_GUI_DATA_DIR": str(self.root / "yt-dlp-gui"),
        })
        overrides.start()
        self.addCleanup(overrides.stop)
        self.settings = settings_store.user_settings_path()
        self.settings.parent.mkdir()
        self.settings.write_text("{}")
        self.binary_dir = yt_dlp_binary.managed_binary_dir()
        self.runtime = self.binary_dir / "runtime"
        self.runtime.mkdir(parents=True)
        (self.runtime / "yt-dlp").touch()

    def test_removes_owned_paths_and_empty_parents_only(self):
        downloads = self.root / "Downloads"
        downloads.mkdir()
        video = downloads / "video.mp4"
        video.write_bytes(b"media")
        other = self.binary_dir / "unrelated.txt"
        other.write_text("keep")
        stage = self.binary_dir / ".runtime-1234abcd"
        stage.mkdir()
        (stage / "engine").touch()
        result = app_data.remove_app_data(app_data.cleanup_paths())
        self.assertEqual(result.errors, ())
        self.assertFalse(self.runtime.exists())
        self.assertFalse(stage.exists())
        self.assertFalse(self.settings.parent.exists())
        self.assertEqual(video.read_bytes(), b"media")
        self.assertEqual(other.read_text(), "keep")

    def test_symlinked_runtime_does_not_delete_target(self):
        import shutil
        shutil.rmtree(self.runtime)
        outside = self.root / "Downloads"
        outside.mkdir()
        video = outside / "video.mp4"
        video.touch()
        self.runtime.symlink_to(outside, target_is_directory=True)
        self.assertEqual(app_data.remove_app_data(app_data.cleanup_paths()).errors, ())
        self.assertTrue(video.exists())
        self.assertFalse(self.runtime.is_symlink())

    def test_symlinked_bin_is_refused(self):
        import shutil
        shutil.rmtree(self.binary_dir)
        outside = self.root / "shared-tools"
        outside.mkdir()
        tool = outside / "yt-dlp"
        tool.touch()
        self.binary_dir.symlink_to(outside, target_is_directory=True)
        result = app_data.remove_app_data(app_data.cleanup_paths())
        self.assertTrue(result.errors)
        self.assertTrue(tool.exists())

    def test_permission_failures_are_reported(self):
        with patch.object(app_data.shutil, "rmtree", side_effect=PermissionError("denied")):
            result = app_data.remove_app_data(app_data.cleanup_paths())
        self.assertTrue(any("denied" in error for error in result.errors))
        self.assertTrue(self.runtime.exists())
