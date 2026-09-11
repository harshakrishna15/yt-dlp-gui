from __future__ import annotations

import io
import os
import stat
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gui.common import yt_dlp_binary as binary, yt_dlp_release as release
from scripts import fetch_yt_dlp_binary as build


def runtime_archive(*, extra: str | None = None, symlink: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("yt-dlp_macos", b"new engine")
        library = zipfile.ZipInfo("_internal/library.dylib")
        library.external_attr = (stat.S_IFREG | 0o755) << 16
        archive.writestr(library, b"new library")
        if extra:
            entry = zipfile.ZipInfo(extra)
            entry.external_attr = ((stat.S_IFLNK if symlink else stat.S_IFREG) | 0o777) << 16
            archive.writestr(entry, b"../../outside")
    return output.getvalue()


class TestRuntimeArchive(unittest.TestCase):
    def test_extracts_complete_runtime_with_executable_permissions(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            executable = release.extract_macos_runtime(runtime_archive(), root)
            self.assertEqual(executable.read_bytes(), b"new engine")
            self.assertTrue(os.access(executable, os.X_OK))
            self.assertTrue(os.access(root / "_internal/library.dylib", os.X_OK))

    def test_rejects_path_traversal_absolute_paths_and_symlinks(self):
        for name, link in (("../outside", False), ("/tmp/outside", False), ("x\\outside", False), ("C:/outside", False), ("link", True)):
            with self.subTest(name=name), TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    release.extract_macos_runtime(runtime_archive(extra=name, symlink=link), Path(temp))
                self.assertEqual(list(Path(temp).iterdir()), [])

    def test_rejects_nonempty_staging_and_malformed_archives(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Invalid"):
                release.extract_macos_runtime(b"bad zip", root)
            (root / "keep").write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "empty"):
                release.extract_macos_runtime(runtime_archive(), root)
            self.assertEqual((root / "keep").read_bytes(), b"keep")


class TestMacRuntimeLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.patch = patch.dict(os.environ, {"YT_DLP_GUI_DATA_DIR": str(self.data), "YT_DLP_GUI_BINARY": ""})
        self.patch.start()
        self.platform = patch.object(binary.sys, "platform", "darwin")
        self.platform.start()
        binary._reset_bootstrap_cache()

    def tearDown(self):
        binary._reset_bootstrap_cache()
        self.platform.stop()
        self.patch.stop()
        self.temp.cleanup()

    def seed(self, *, version="2026.08.19"):
        parent = self.root / "bundle"
        parent.mkdir(exist_ok=True)
        path = parent / "yt-dlp.zip"
        path.write_bytes(runtime_archive())
        (parent / "VERSION").write_text(version)
        (parent / "THIRD_PARTY_LICENSES.txt").write_text("notices")
        return path

    def old_engine(self, *, runtime=False, version="2026.08.19"):
        parent = self.data / "bin"
        if runtime:
            parent /= "runtime"
        parent.mkdir(parents=True)
        path = parent / "yt-dlp"
        path.write_bytes(b"old engine")
        path.chmod(0o755)
        (parent / "VERSION").write_text(version)
        (parent / "THIRD_PARTY_LICENSES.txt").write_text("old notices")
        return binary.YtDlpBinary(path, "managed", version)

    def test_bootstrap_migrates_equal_version_single_file_and_caches_runtime(self):
        old = self.old_engine()
        with patch.object(binary, "bundled_runtime_archive_path", return_value=self.seed()), patch.object(binary, "_read_version", return_value=old.version) as read:
            resolved = binary.resolve_yt_dlp_binary()
            again = binary.resolve_yt_dlp_binary()
            self.assertEqual(read.call_count, 1)
        self.assertEqual(resolved, again)
        self.assertEqual(resolved.path, self.data / "bin/runtime/yt-dlp")
        self.assertFalse(old.path.exists())
        self.assertEqual(resolved.path.read_bytes(), b"new engine")
        self.assertEqual(binary.managed_license_path().read_text(), "notices")
        self.assertEqual(sorted(p.name for p in (self.data / "bin").iterdir()), ["runtime"])

    def test_current_runtime_launch_uses_sidecar_without_running_executable(self):
        old = self.old_engine(runtime=True)
        with patch.object(binary, "bundled_runtime_archive_path", return_value=self.seed()), patch.object(binary, "_read_version", side_effect=AssertionError("unnecessary process")):
            self.assertEqual(binary.resolve_yt_dlp_binary(), old)

    def test_newer_engine_is_not_downgraded(self):
        old = self.old_engine(version="2026.09.01")
        with patch.object(binary, "bundled_runtime_archive_path", return_value=self.seed()), patch.object(binary, "_read_version", side_effect=AssertionError("unnecessary process")):
            self.assertEqual(binary.resolve_yt_dlp_binary(), old)

    def update(self, old):
        asset = release.YtDlpReleaseAsset("yt-dlp_macos.zip", runtime_archive(), "0" * 64)
        with patch.object(binary, "resolve_yt_dlp_binary", return_value=old), patch.object(release, "fetch_latest_release_asset", return_value=asset), patch.object(binary, "_read_version", return_value="2026.09.01"), patch.object(release, "fetch_third_party_licenses", return_value=b"new notices"):
            return binary.update_managed_yt_dlp()

    def test_updater_replaces_whole_runtime_and_removes_staging(self):
        old = self.old_engine(runtime=True)
        (old.path.parent / "obsolete-library").write_bytes(b"obsolete")
        result = self.update(old)
        self.assertTrue(result.success)
        self.assertEqual(old.path.read_bytes(), b"new engine")
        self.assertEqual((old.path.parent / "_internal/library.dylib").read_bytes(), b"new library")
        self.assertFalse((old.path.parent / "obsolete-library").exists())
        self.assertEqual(sorted(p.name for p in (self.data / "bin").iterdir()), ["runtime"])

    def test_install_failure_rolls_back_entire_runtime(self):
        old = self.old_engine(runtime=True)
        real_replace = os.replace
        def fail_install(source, target):
            if Path(source).name == "engine" and Path(target).name == "runtime":
                raise OSError("install failed")
            real_replace(source, target)
        with patch.object(binary.os, "replace", side_effect=fail_install):
            result = self.update(old)
        self.assertFalse(result.success)
        self.assertEqual(old.path.read_bytes(), b"old engine")
        self.assertEqual((old.path.parent / "VERSION").read_text(), old.version)
        self.assertEqual(sorted(p.name for p in (self.data / "bin").iterdir()), ["runtime"])

    def test_failed_first_migration_keeps_single_file_engine(self):
        old = self.old_engine()
        with patch.object(binary, "_install_runtime", side_effect=OSError("read only")):
            result = self.update(old)
        self.assertFalse(result.success)
        self.assertEqual(old.path.read_bytes(), b"old engine")

    def test_build_stores_archive_and_manifest_not_repacked_binary(self):
        asset = release.YtDlpReleaseAsset("yt-dlp_macos.zip", runtime_archive(), "0" * 64)
        output = self.root / "build/yt-dlp"
        with patch.object(release, "fetch_latest_release_asset", return_value=asset), patch.object(build, "_binary_version", return_value="2026.08.19"), patch.object(release, "fetch_third_party_licenses", return_value=b"notices"):
            build.fetch_latest_binary(platform="macos", output=output, license_output=output.parent / "THIRD_PARTY_LICENSES.txt")
        self.assertFalse(output.exists())
        self.assertEqual(output.with_suffix(".zip").read_bytes(), asset.payload)
        self.assertEqual((output.parent / "VERSION").read_text(), "2026.08.19\n")
