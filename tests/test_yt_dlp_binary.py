from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gui.common import yt_dlp_binary, yt_dlp_release


class TestYtDlpBinaryPaths(unittest.TestCase):
    def tearDown(self) -> None:
        yt_dlp_binary._reset_bootstrap_cache()

    def test_managed_binary_dir_uses_platform_application_data(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "gui.common.yt_dlp_binary.Path.home",
                return_value=Path("/Users/example"),
            ):
                self.assertEqual(
                    yt_dlp_binary.managed_binary_dir(platform="darwin"),
                    Path("/Users/example/Library/Application Support/yt-dlp-gui/bin"),
                )

        with patch.dict(
            os.environ,
            {"LOCALAPPDATA": r"C:\Users\example\AppData\Local"},
            clear=True,
        ):
            self.assertEqual(
                yt_dlp_binary.managed_binary_dir(platform="win32"),
                Path(r"C:\Users\example\AppData\Local") / "yt-dlp-gui" / "bin",
            )

    def test_data_directory_override_is_respected(self) -> None:
        with patch.dict(
            os.environ,
            {"YT_DLP_GUI_DATA_DIR": "/tmp/custom-yt-dlp-gui"},
            clear=False,
        ):
            self.assertEqual(
                yt_dlp_binary.managed_binary_dir(platform="darwin"),
                Path("/tmp/custom-yt-dlp-gui/bin"),
            )

    def test_windows_staged_binary_keeps_exe_suffix(self) -> None:
        staged = yt_dlp_binary._staged_binary_path(Path(r"C:\app\yt-dlp.exe"))
        self.assertEqual(staged.suffix, ".exe")
        self.assertIn(".update.exe", staged.name)


class TestYtDlpBinaryResolution(unittest.TestCase):
    def setUp(self) -> None:
        yt_dlp_binary._reset_bootstrap_cache()

    def tearDown(self) -> None:
        yt_dlp_binary._reset_bootstrap_cache()

    def test_override_takes_precedence(self) -> None:
        with TemporaryDirectory() as tmp:
            override = Path(tmp) / yt_dlp_binary.executable_name()
            override.write_bytes(b"override")
            override.chmod(0o755)
            with patch.dict(
                os.environ,
                {"YT_DLP_GUI_BINARY": str(override)},
                clear=False,
            ):
                with patch.object(
                    yt_dlp_binary,
                    "_read_version",
                    return_value="2026.08.19",
                ):
                    resolved = yt_dlp_binary.resolve_yt_dlp_binary()

        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.path, override)
        self.assertEqual(resolved.source, "override")
        self.assertEqual(resolved.version, "2026.08.19")

    def test_bundled_seed_bootstraps_managed_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed"
            managed = root / "managed" / yt_dlp_binary.executable_name()
            seed_license = root / "THIRD_PARTY_LICENSES.txt"
            managed_license = managed.parent / "THIRD_PARTY_LICENSES.txt"
            managed_version = managed.parent / "VERSION"
            seed.write_bytes(b"latest executable")
            seed_license.write_bytes(b"release notices")

            def _version(path: Path) -> str:
                return "2026.08.19" if Path(path).read_bytes() == seed.read_bytes() else ""

            with patch.object(yt_dlp_binary, "managed_binary_path", return_value=managed):
                with patch.object(yt_dlp_binary, "bundled_binary_path", return_value=seed):
                    with patch.object(
                        yt_dlp_binary,
                        "bundled_license_path",
                        return_value=seed_license,
                    ):
                        with patch.object(
                            yt_dlp_binary,
                            "managed_license_path",
                            return_value=managed_license,
                        ):
                            with patch.object(
                                yt_dlp_binary,
                                "_is_executable",
                                side_effect=lambda path: Path(path).is_file(),
                            ):
                                with patch.object(
                                    yt_dlp_binary,
                                    "_read_version",
                                    side_effect=_version,
                                ):
                                    resolved = yt_dlp_binary.resolve_yt_dlp_binary()

            self.assertEqual(managed.read_bytes(), seed.read_bytes())
            self.assertEqual(managed_license.read_bytes(), seed_license.read_bytes())
            self.assertEqual(
                managed_version.read_text(encoding="utf-8"),
                "2026.08.19\n",
            )
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.path, managed)
            self.assertEqual(resolved.source, "managed")
            self.assertEqual(resolved.version, "2026.08.19")

    def test_newer_managed_copy_is_not_replaced_by_bundled_seed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed"
            managed = root / "managed"
            seed.write_bytes(b"seed")
            managed.write_bytes(b"newer")

            def _version(path: Path) -> str:
                return "2026.08.19" if Path(path) == seed else "2026.09.01"

            with patch.object(yt_dlp_binary, "managed_binary_path", return_value=managed):
                with patch.object(yt_dlp_binary, "bundled_binary_path", return_value=seed):
                    with patch.object(
                        yt_dlp_binary,
                        "_is_executable",
                        side_effect=lambda path: Path(path).is_file(),
                    ):
                        with patch.object(
                            yt_dlp_binary,
                            "_read_version",
                            side_effect=_version,
                        ):
                            resolved = yt_dlp_binary.resolve_yt_dlp_binary()

            self.assertEqual(managed.read_bytes(), b"newer")
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.version, "2026.09.01")

    def test_version_sidecars_avoid_startup_subprocesses(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "bundle" / "yt-dlp"
            managed = root / "managed" / "yt-dlp"
            seed.parent.mkdir()
            managed.parent.mkdir()
            seed.write_bytes(b"seed")
            managed.write_bytes(b"managed")
            seed_version = seed.parent / "VERSION"
            managed_version = managed.parent / "VERSION"
            seed_version.write_text("2026.08.19\n", encoding="utf-8")
            managed_version.write_text("2026.08.19\n", encoding="utf-8")

            with patch.object(yt_dlp_binary, "managed_binary_path", return_value=managed):
                with patch.object(yt_dlp_binary, "bundled_binary_path", return_value=seed):
                    with patch.object(
                        yt_dlp_binary,
                        "bundled_version_path",
                        return_value=seed_version,
                    ):
                        with patch.object(
                            yt_dlp_binary,
                            "_is_executable",
                            side_effect=lambda path: Path(path).is_file(),
                        ):
                            with patch.object(
                                yt_dlp_binary,
                                "_read_version",
                                side_effect=AssertionError(
                                    "version subprocess should not run"
                                ),
                            ):
                                resolved = yt_dlp_binary.resolve_yt_dlp_binary()

            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertEqual(resolved.version, "2026.08.19")


class TestYtDlpUpdater(unittest.TestCase):
    def tearDown(self) -> None:
        yt_dlp_binary._reset_bootstrap_cache()

    def test_update_replaces_managed_binary_and_verifies_version(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / yt_dlp_binary.executable_name()
            license_path = Path(tmp) / "THIRD_PARTY_LICENSES.txt"
            version_path = Path(tmp) / "VERSION"
            path.write_bytes(b"old")
            path.chmod(0o755)
            license_path.write_bytes(b"old notices")
            version_path.write_text("2026.07.04\n", encoding="utf-8")
            resolved = yt_dlp_binary.YtDlpBinary(
                path=path,
                source="managed",
                version="2026.07.04",
            )
            release = yt_dlp_release.YtDlpReleaseAsset(
                filename="yt-dlp_macos",
                payload=b"new",
                sha256="a" * 64,
            )

            with patch.object(
                yt_dlp_binary,
                "resolve_yt_dlp_binary",
                return_value=resolved,
            ):
                with patch.object(
                    yt_dlp_binary.yt_dlp_release,
                    "fetch_latest_release_asset",
                    return_value=release,
                ):
                    with patch.object(
                        yt_dlp_binary.yt_dlp_release,
                        "fetch_third_party_licenses",
                        return_value=b"new notices",
                    ):
                        with patch.object(
                            yt_dlp_binary,
                            "_read_version",
                            return_value="2026.08.19",
                        ):
                            result = yt_dlp_binary.update_managed_yt_dlp()

            self.assertTrue(result.success)
            self.assertTrue(result.changed)
            self.assertEqual(result.version, "2026.08.19")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(license_path.read_bytes(), b"new notices")
            self.assertEqual(
                version_path.read_text(encoding="utf-8"),
                "2026.08.19\n",
            )
            self.assertFalse(path.with_name(f"{path.name}.backup").exists())

    def test_failed_update_restores_previous_binary(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / yt_dlp_binary.executable_name()
            license_path = Path(tmp) / "THIRD_PARTY_LICENSES.txt"
            version_path = Path(tmp) / "VERSION"
            path.write_bytes(b"old")
            path.chmod(0o755)
            license_path.write_bytes(b"old notices")
            version_path.write_text("2026.07.04\n", encoding="utf-8")
            resolved = yt_dlp_binary.YtDlpBinary(
                path=path,
                source="managed",
                version="2026.07.04",
            )
            release = yt_dlp_release.YtDlpReleaseAsset(
                filename="yt-dlp_macos",
                payload=b"new",
                sha256="a" * 64,
            )
            real_replace = os.replace

            def _replace(source, destination):
                source_path = Path(source)
                destination_path = Path(destination)
                if (
                    destination_path == version_path
                    and source_path.name.endswith(".update")
                ):
                    raise OSError("version install failed")
                real_replace(source, destination)

            with patch.object(
                yt_dlp_binary,
                "resolve_yt_dlp_binary",
                return_value=resolved,
            ):
                with patch.object(
                    yt_dlp_binary.yt_dlp_release,
                    "fetch_latest_release_asset",
                    return_value=release,
                ):
                    with patch.object(
                        yt_dlp_binary.yt_dlp_release,
                        "fetch_third_party_licenses",
                        return_value=b"new notices",
                    ):
                        with patch.object(
                            yt_dlp_binary,
                            "_read_version",
                            return_value="2026.08.19",
                        ):
                            with patch.object(
                                yt_dlp_binary.os,
                                "replace",
                                side_effect=_replace,
                            ):
                                result = yt_dlp_binary.update_managed_yt_dlp()

            self.assertFalse(result.success)
            self.assertEqual(result.version, "2026.07.04")
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(license_path.read_bytes(), b"old notices")
            self.assertEqual(
                version_path.read_text(encoding="utf-8"),
                "2026.07.04\n",
            )

    def test_update_rejects_non_managed_binary(self) -> None:
        resolved = yt_dlp_binary.YtDlpBinary(
            path=Path("/usr/local/bin/yt-dlp"),
            source="system",
            version="2026.08.19",
        )
        with patch.object(
            yt_dlp_binary,
            "resolve_yt_dlp_binary",
            return_value=resolved,
        ):
            result = yt_dlp_binary.update_managed_yt_dlp()

        self.assertFalse(result.success)
        self.assertIn("managed", result.message.lower())


if __name__ == "__main__":
    unittest.main()
