#!/usr/bin/env python3
"""Generate app icons for yt-dlp-gui packaging."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    HAS_QT = True
except ModuleNotFoundError:  # pragma: no cover - optional build path
    HAS_QT = False

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - build-only dependency
    Image = None


def _icon_source_svg_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "gui"
        / "qt"
        / "assets"
        / "app-icon-source.svg"
    )


def _render_svg_icon(size: int) -> QImage:
    if not HAS_QT:
        raise RuntimeError("PySide6 with QtSvg is required for direct SVG rendering")
    svg_path = _icon_source_svg_path()
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Failed to load SVG icon source: {svg_path}")
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return image


def _master_png_path() -> Path:
    return Path(__file__).resolve().parent.parent / "gui" / "qt" / "assets" / "tmp-mac-app-icon.png"


def _resize_png_with_sips(source_png: Path, output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "sips",
            "-z",
            str(int(size)),
            str(int(size)),
            str(source_png),
            "-o",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"sips failed to resize icon PNG: {details}")


def _resize_png_with_pillow(source_png: Path, output_path: Path, size: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required to resize PNG icons on this platform")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_png) as source:
        resized = source.resize((int(size), int(size)), Image.Resampling.LANCZOS)
        resized.save(output_path, format="PNG")


def write_icon_png(output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if HAS_QT:
        if not _render_svg_icon(size).save(str(output_path), "PNG"):
            raise RuntimeError(f"Failed to write {output_path}")
        return
    master_png = _master_png_path()
    if not master_png.is_file():
        raise RuntimeError(f"Missing master icon PNG: {master_png}")
    if master_png.resolve() == output_path.resolve():
        return
    if int(size) == 1024:
        output_path.write_bytes(master_png.read_bytes())
        return
    if sys.platform == "darwin":
        _resize_png_with_sips(master_png, output_path, size)
        return
    if Image is not None:
        _resize_png_with_pillow(master_png, output_path, size)
        return
    raise RuntimeError("PySide6 or Pillow is required to generate resized PNG icons on this platform")


def write_icon_ico(output_path: Path, size: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required to generate .ico files")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png_path = Path(tmp) / "icon.png"
        write_icon_png(png_path, size)
        with Image.open(png_path) as image:
            image.save(
                output_path,
                format="ICO",
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
            )


def write_icon_icns(output_path: Path, size: int) -> None:
    if HAS_QT and Image is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "icon.png"
            write_icon_png(png_path, size)
            with Image.open(png_path) as image:
                image.save(output_path, format="ICNS")
        return
    if sys.platform != "darwin":
        raise RuntimeError("ICNS generation without PySide6/Pillow is only supported on macOS")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    icns_entries = (
        ("icp4", 16),
        ("icp5", 32),
        ("icp6", 64),
        ("ic07", 128),
        ("ic08", 256),
        ("ic09", 512),
        ("ic10", 1024),
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        chunks: list[bytes] = []
        for chunk_type, target_size in icns_entries:
            png_path = tmp_path / f"{chunk_type}.png"
            write_icon_png(png_path, target_size)
            data = png_path.read_bytes()
            chunks.append(
                chunk_type.encode("ascii")
                + struct.pack(">I", len(data) + 8)
                + data
            )
        body = b"".join(chunks)
        output_path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def write_icon(output_path: Path, size: int) -> None:
    suffix = output_path.suffix.lower()
    if suffix == ".ico":
        write_icon_ico(output_path, size)
        return
    if suffix == ".icns":
        write_icon_icns(output_path, size)
        return
    write_icon_png(output_path, size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate app icon assets for yt-dlp-gui")
    parser.add_argument(
        "--output",
        default="build/yt-dlp-gui-icon.png",
        help="Output path for the generated icon (.png or .ico)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Square icon size in pixels (default: 1024)",
    )
    args = parser.parse_args()

    write_icon(Path(args.output), int(args.size))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
