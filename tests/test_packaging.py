from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from gui.qt.assets_manifest import REQUIRED_ASSET_FILENAMES, assets_dir
from scripts import check_packaged_assets
from scripts import write_pyinstaller_version_info


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestQtAssetManifest(unittest.TestCase):
    def test_required_assets_exist_in_repo(self) -> None:
        root = assets_dir()
        for filename in REQUIRED_ASSET_FILENAMES:
            self.assertTrue((root / filename).is_file(), filename)


class TestPackagedAssetsSmokeCheck(unittest.TestCase):
    def test_candidate_assets_dirs_covers_supported_bundle_layouts(self) -> None:
        bundle = Path("/tmp/example-bundle")
        self.assertEqual(
            check_packaged_assets.candidate_assets_dirs(bundle),
            (
                bundle / "gui" / "qt" / "assets",
                bundle / "_internal" / "gui" / "qt" / "assets",
                bundle / "Contents" / "Resources" / "gui" / "qt" / "assets",
                bundle / "Contents" / "Frameworks" / "gui" / "qt" / "assets",
                bundle / "Contents" / "Frameworks" / "_internal" / "gui" / "qt" / "assets",
                bundle / "Contents" / "MacOS" / "_internal" / "gui" / "qt" / "assets",
            ),
        )

    def test_find_assets_dir_prefers_first_existing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            direct = bundle / "gui" / "qt" / "assets"
            internal = bundle / "_internal" / "gui" / "qt" / "assets"
            internal.mkdir(parents=True)
            direct.mkdir(parents=True)
            self.assertEqual(check_packaged_assets.find_assets_dir(bundle), direct)

    def test_missing_required_assets_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            assets_path = Path(tmp)
            (assets_path / REQUIRED_ASSET_FILENAMES[0]).write_text("x", encoding="utf-8")
            missing = check_packaged_assets.missing_required_assets(assets_path)
            self.assertIn(REQUIRED_ASSET_FILENAMES[1], missing)
            self.assertNotIn(REQUIRED_ASSET_FILENAMES[0], missing)

    def test_main_succeeds_when_all_assets_exist_in_internal_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "pyinstaller_entry"
            assets_path = bundle / "_internal" / "gui" / "qt" / "assets"
            assets_path.mkdir(parents=True)
            for filename in REQUIRED_ASSET_FILENAMES:
                (assets_path / filename).write_text("x", encoding="utf-8")
            self.assertEqual(check_packaged_assets.main([str(bundle)]), 0)

    def test_main_succeeds_when_all_assets_exist_in_macos_app_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "yt-dlp-gui.app"
            assets_path = bundle / "Contents" / "Frameworks" / "_internal" / "gui" / "qt" / "assets"
            assets_path.mkdir(parents=True)
            for filename in REQUIRED_ASSET_FILENAMES:
                (assets_path / filename).write_text("x", encoding="utf-8")
            self.assertEqual(check_packaged_assets.main([str(bundle)]), 0)

    def test_main_fails_when_bundle_directory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "missing-bundle"
            self.assertEqual(check_packaged_assets.main([str(bundle)]), 1)

    def test_main_fails_when_bundle_is_missing_assets_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "pyinstaller_entry"
            bundle.mkdir(parents=True)
            self.assertEqual(check_packaged_assets.main([str(bundle)]), 1)

    def test_main_fails_when_assets_dir_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "pyinstaller_entry"
            assets_path = bundle / "gui" / "qt" / "assets"
            assets_path.mkdir(parents=True)
            (assets_path / REQUIRED_ASSET_FILENAMES[0]).write_text("x", encoding="utf-8")
            self.assertEqual(check_packaged_assets.main([str(bundle)]), 1)

    def test_cli_script_runs_from_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "dist" / "pyinstaller_entry"
            assets_path = bundle / "gui" / "qt" / "assets"
            assets_path.mkdir(parents=True)
            for filename in REQUIRED_ASSET_FILENAMES:
                (assets_path / filename).write_text("x", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "check_packaged_assets.py"),
                    str(bundle),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[ok] packaged assets present:", result.stdout)


class TestPackagingConfiguration(unittest.TestCase):
    def test_icon_generator_can_write_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "icon.png"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "make-macos-icon.py"),
                    "--output",
                    str(output),
                    "--size",
                    "512",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    @unittest.skipUnless(sys.platform == "darwin", "icns generation is macOS-only")
    def test_icon_generator_can_write_icns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "icon.icns"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "make-macos-icon.py"),
                    "--output",
                    str(output),
                    "--size",
                    "1024",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_build_scripts_bundle_qt_assets_and_no_longer_reference_font_dir(self) -> None:
        macos_script = (REPO_ROOT / "scripts" / "build-macos.sh").read_text(
            encoding="utf-8"
        )
        windows_script = (REPO_ROOT / "scripts" / "build-windows.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn('--add-data "gui/qt/assets:gui/qt/assets"', macos_script)
        self.assertIn("--osx-bundle-identifier", macos_script)
        self.assertIn('--icon "build/yt-dlp-gui-icon.icns"', macos_script)
        self.assertIn('--add-data "gui/qt/assets;gui/qt/assets"', windows_script)
        self.assertIn('--icon "build/yt-dlp-gui-icon.ico"', windows_script)
        self.assertIn('--version-file "build/pyinstaller-version-info.txt"', windows_script)
        self.assertIn("pip install pyinstaller pillow", macos_script)
        self.assertIn("-m pip install pyinstaller pillow", windows_script)
        self.assertNotIn("font:font", macos_script)
        self.assertNotIn("font;font", windows_script)

    def test_windows_version_info_includes_product_metadata(self) -> None:
        payload = write_pyinstaller_version_info.build_version_info()

        self.assertIn("ProductName", payload)
        self.assertIn("yt-dlp-gui", payload)
        self.assertIn("FileDescription", payload)

    def test_ci_workflow_runs_packaging_smoke_check_via_build_scripts(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("shell: bash", workflow)
        self.assertIn("shell: pwsh", workflow)
        self.assertIn("scripts/build-macos.sh", workflow)
        self.assertIn("scripts/build-windows.ps1", workflow)
        self.assertIn("python scripts/check_packaged_assets.py", workflow)


if __name__ == "__main__":
    unittest.main()
