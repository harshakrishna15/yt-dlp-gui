from __future__ import annotations

import subprocess
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from gui import app_meta
from gui.qt.assets_manifest import REQUIRED_ASSET_FILENAMES, assets_dir
from scripts import check_packaged_assets
from scripts import write_pyinstaller_version_info


REPO_ROOT = Path(__file__).resolve().parents[1]


def _paeth_predictor(left: int, up: int, up_left: int) -> int:
    base = left + up - up_left
    left_dist = abs(base - left)
    up_dist = abs(base - up)
    up_left_dist = abs(base - up_left)
    if left_dist <= up_dist and left_dist <= up_left_dist:
        return left
    if up_dist <= up_left_dist:
        return up
    return up_left


def _unfilter_png_scanline(
    filter_type: int, scanline: bytes, previous: bytes, bytes_per_pixel: int
) -> bytearray:
    output = bytearray(scanline)
    if filter_type == 0:
        return output
    for index in range(len(output)):
        left = output[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index] if previous else 0
        up_left = previous[index - bytes_per_pixel] if previous and index >= bytes_per_pixel else 0
        if filter_type == 1:
            output[index] = (output[index] + left) & 0xFF
        elif filter_type == 2:
            output[index] = (output[index] + up) & 0xFF
        elif filter_type == 3:
            output[index] = (output[index] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            output[index] = (output[index] + _paeth_predictor(left, up, up_left)) & 0xFF
        else:
            raise AssertionError(f"Unsupported PNG filter type: {filter_type}")
    return output


def _png_alpha_samples(
    path: Path, points: tuple[tuple[int, int], ...]
) -> dict[tuple[int, int], int]:
    # Keep this parser stdlib-only so packaging tests still run without Qt or Pillow.
    payload = path.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")

    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    idat = bytearray()
    offset = 8
    while offset < len(payload):
        chunk_length = struct.unpack(">I", payload[offset : offset + 4])[0]
        offset += 4
        chunk_type = payload[offset : offset + 4]
        offset += 4
        chunk_data = payload[offset : offset + chunk_length]
        offset += chunk_length + 4
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = (
                struct.unpack(">IIBBBBB", chunk_data)
            )
            assert compression == 0
            assert filter_method == 0
            assert interlace == 0
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    assert width > 0
    assert height > 0
    assert bit_depth == 8
    bytes_per_pixel = {2: 3, 6: 4}.get(color_type)
    assert bytes_per_pixel is not None, f"Unsupported PNG color type: {color_type}"

    decompressed = zlib.decompress(bytes(idat))
    stride = width * bytes_per_pixel
    previous = b""
    rows: list[bytearray] = []
    cursor = 0
    for _ in range(height):
        filter_type = decompressed[cursor]
        cursor += 1
        row = decompressed[cursor : cursor + stride]
        cursor += stride
        decoded = _unfilter_png_scanline(filter_type, row, previous, bytes_per_pixel)
        rows.append(decoded)
        previous = decoded

    result: dict[tuple[int, int], int] = {}
    for x, y in points:
        pixel_offset = x * bytes_per_pixel
        if color_type == 6:
            result[(x, y)] = rows[y][pixel_offset + 3]
        else:
            result[(x, y)] = 255
    return result


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

    def test_generated_png_uses_rounded_dock_silhouette(self) -> None:
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
            samples = _png_alpha_samples(
                output,
                (
                    (0, 0),
                    (511, 0),
                    (0, 511),
                    (511, 511),
                    (180, 180),
                    (256, 256),
                ),
            )
            for (x, y), alpha in samples.items():
                with self.subTest(x=x, y=y):
                    if (x, y) in {(0, 0), (511, 0), (0, 511), (511, 511)}:
                        self.assertEqual(alpha, 0)
                    else:
                        self.assertEqual(alpha, 255)

    def test_generated_windows_png_fills_canvas(self) -> None:
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
                    "--variant",
                    "windows",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            samples = _png_alpha_samples(
                output,
                (
                    (0, 0),
                    (511, 0),
                    (0, 511),
                    (511, 511),
                    (256, 256),
                ),
            )
            for (x, y), alpha in samples.items():
                with self.subTest(x=x, y=y):
                    self.assertEqual(alpha, 255)

    def test_icon_generator_can_write_windows_ico_without_explicit_pillow_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "icon.ico"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "make-macos-icon.py"),
                    "--output",
                    str(output),
                    "--size",
                    "1024",
                    "--variant",
                    "windows",
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
        self.assertIn("--variant macos", macos_script)
        self.assertIn('--add-data "gui/qt/assets;gui/qt/assets"', windows_script)
        self.assertIn('--icon "build/yt-dlp-gui-icon.ico"', windows_script)
        self.assertIn("--variant windows", windows_script)
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

    def test_app_icon_filename_changes_for_windows(self) -> None:
        self.assertEqual(
            app_meta.app_icon_filename_for_platform("win32"),
            app_meta.WINDOWS_APP_ICON_FILENAME,
        )
        self.assertEqual(
            app_meta.app_icon_filename_for_platform("darwin"),
            app_meta.MACOS_APP_ICON_FILENAME,
        )

if __name__ == "__main__":
    unittest.main()
