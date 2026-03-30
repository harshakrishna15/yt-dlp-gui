#!/usr/bin/env python3
"""Generate app icons for yt-dlp-gui packaging."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter, QPainterPath
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


_ICON_VIEWBOX_SIZE = 1024.0
_ICON_TILE_X = 110.0
_ICON_TILE_Y = 90.0
_ICON_TILE_SIZE = 804.0
_ICON_TILE_RADIUS = 208.0


def _tile_clip_path(size: int) -> "QPainterPath":
    scale = float(size) / _ICON_VIEWBOX_SIZE
    path = QPainterPath()
    path.addRoundedRect(
        _ICON_TILE_X * scale,
        _ICON_TILE_Y * scale,
        _ICON_TILE_SIZE * scale,
        _ICON_TILE_SIZE * scale,
        _ICON_TILE_RADIUS * scale,
        _ICON_TILE_RADIUS * scale,
    )
    return path


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
    # Qt's SVG rasterizer can leak low-alpha pixels past rounded clipPaths.
    # Apply the final tile mask at the painter level so exported PNG/ICNS
    # never carry corner ghosting regardless of renderer behavior.
    p.setClipPath(_tile_clip_path(size))
    renderer.render(p)
    p.end()
    return image


def _master_png_path() -> Path:
    return Path(__file__).resolve().parent.parent / "gui" / "qt" / "assets" / "tmp-mac-app-icon.png"


def _render_svg_icon_with_appkit(output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = float(size) / _ICON_VIEWBOX_SIZE
    tile_x = _ICON_TILE_X * scale
    tile_y = _ICON_TILE_Y * scale
    tile_size = _ICON_TILE_SIZE * scale
    tile_radius = _ICON_TILE_RADIUS * scale
    swift_source = f"""
import AppKit
import Foundation

let input = URL(fileURLWithPath: {json.dumps(str(_icon_source_svg_path()))})
let output = URL(fileURLWithPath: {json.dumps(str(output_path))})
let size = NSSize(width: {int(size)}, height: {int(size)})
let tileRect = CGRect(x: {tile_x}, y: {tile_y}, width: {tile_size}, height: {tile_size})
let tileRadius = CGFloat({tile_radius})
guard let image = NSImage(contentsOf: input) else {{
    fputs("Failed to load SVG icon source: \\(input.path)\\n", stderr)
    exit(1)
}}
guard let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: Int(size.width),
    pixelsHigh: Int(size.height),
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
) else {{
    fputs("Failed to allocate bitmap for icon render\\n", stderr)
    exit(1)
}}
rep.size = size
NSGraphicsContext.saveGraphicsState()
guard let context = NSGraphicsContext(bitmapImageRep: rep) else {{
    fputs("Failed to create graphics context for icon render\\n", stderr)
    exit(1)
}}
NSGraphicsContext.current = context
context.cgContext.clear(CGRect(origin: .zero, size: size))
NSBezierPath(roundedRect: tileRect, xRadius: tileRadius, yRadius: tileRadius).addClip()
image.draw(in: CGRect(origin: .zero, size: size))
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()
guard let data = rep.representation(using: .png, properties: [:]) else {{
    fputs("Failed to encode icon render as PNG\\n", stderr)
    exit(1)
}}
do {{
    try data.write(to: output)
}} catch {{
    fputs("Failed to write icon PNG: \\(error.localizedDescription)\\n", stderr)
    exit(1)
}}
"""
    env = os.environ.copy()
    tmpdir = Path(tempfile.gettempdir())
    env.setdefault("SWIFT_MODULECACHE_PATH", str(tmpdir / "swift-module-cache"))
    env.setdefault("CLANG_MODULE_CACHE_PATH", str(tmpdir / "clang-module-cache"))
    result = subprocess.run(
        ["swift", "-e", swift_source],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"swift failed to render SVG icon: {details}")


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
    if sys.platform == "darwin":
        _render_svg_icon_with_appkit(output_path, size)
        return
    master_png = _master_png_path()
    if not master_png.is_file():
        raise RuntimeError(f"Missing master icon PNG: {master_png}")
    if int(size) == 1024:
        output_path.write_bytes(master_png.read_bytes())
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
