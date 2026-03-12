#!/usr/bin/env python3
"""Generate app icons for yt-dlp-gui packaging."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

try:
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import (
        QBrush,
        QColor,
        QImage,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
        QPolygonF,
        QRadialGradient,
    )

    HAS_QT = True
except ModuleNotFoundError:  # pragma: no cover - optional build path
    HAS_QT = False

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - build-only dependency
    Image = None


def _draw_icon(size: int) -> QImage:
    if not HAS_QT:
        raise RuntimeError("PySide6 is required for direct icon drawing")
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # Big Sur style tile with a floating badge and dock.
    pad = size * 0.090
    tile = QRectF(pad, pad, size - (2 * pad), size - (2 * pad))
    radius = size * 0.192
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile, radius, radius)

    shadow_rect = tile.adjusted(size * 0.028, size * 0.055, -size * 0.028, size * 0.040)
    shadow_path = QPainterPath()
    shadow_path.addRoundedRect(shadow_rect, radius * 1.05, radius * 1.05)
    shadow_grad = QLinearGradient(
        shadow_rect.center().x(),
        shadow_rect.top(),
        shadow_rect.center().x(),
        shadow_rect.bottom(),
    )
    shadow_grad.setColorAt(0.0, QColor(13, 43, 38, 0))
    shadow_grad.setColorAt(0.62, QColor(13, 43, 38, 28))
    shadow_grad.setColorAt(1.0, QColor(13, 43, 38, 58))
    p.fillPath(shadow_path, QBrush(shadow_grad))

    base_grad = QLinearGradient(tile.topLeft(), QPointF(tile.right(), tile.bottom()))
    base_grad.setColorAt(0.0, QColor("#f4fbf8"))
    base_grad.setColorAt(0.52, QColor("#dcebe5"))
    base_grad.setColorAt(1.0, QColor("#9cc2b8"))
    p.fillPath(tile_path, QBrush(base_grad))

    p.save()
    p.setClipPath(tile_path)

    sky_glow = QRadialGradient(QPointF(size * 0.300, size * 0.180), size * 0.580)
    sky_glow.setColorAt(0.0, QColor(255, 255, 255, 235))
    sky_glow.setColorAt(0.45, QColor(255, 255, 255, 72))
    sky_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(tile_path, QBrush(sky_glow))

    top_sheen = QRectF(tile.left(), tile.top(), tile.width(), tile.height() * 0.392)
    p.fillRect(top_sheen, QColor(255, 255, 255, 14))

    bottom_tint = QRectF(tile.left(), size * 0.668, tile.width(), tile.bottom() - (size * 0.668))
    p.fillRect(bottom_tint, QColor(95, 155, 144, 20))

    dock_rect = QRectF(size * 0.244, size * 0.666, size * 0.512, size * 0.119)
    dock_radius = dock_rect.height() * 0.50
    dock_shadow_rect = dock_rect.adjusted(size * 0.006, size * 0.021, -size * 0.006, size * 0.021)
    dock_shadow_path = QPainterPath()
    dock_shadow_path.addRoundedRect(
        dock_shadow_rect,
        dock_shadow_rect.height() * 0.50,
        dock_shadow_rect.height() * 0.50,
    )
    dock_shadow_grad = QLinearGradient(
        dock_shadow_rect.center().x(),
        dock_shadow_rect.top(),
        dock_shadow_rect.center().x(),
        dock_shadow_rect.bottom(),
    )
    dock_shadow_grad.setColorAt(0.0, QColor(11, 49, 45, 48))
    dock_shadow_grad.setColorAt(1.0, QColor(11, 49, 45, 0))
    p.fillPath(dock_shadow_path, QBrush(dock_shadow_grad))

    dock_path = QPainterPath()
    dock_path.addRoundedRect(dock_rect, dock_radius, dock_radius)
    dock_grad = QLinearGradient(dock_rect.topLeft(), dock_rect.bottomLeft())
    dock_grad.setColorAt(0.0, QColor("#f8fcfa"))
    dock_grad.setColorAt(1.0, QColor("#cfdfd9"))
    p.fillPath(dock_path, QBrush(dock_grad))

    dock_gloss = QPainterPath()
    dock_gloss.moveTo(size * 0.279, size * 0.689)
    dock_gloss.cubicTo(size * 0.320, size * 0.675, size * 0.405, size * 0.666, size * 0.500, size * 0.666)
    dock_gloss.cubicTo(size * 0.595, size * 0.666, size * 0.680, size * 0.675, size * 0.721, size * 0.689)
    dock_gloss.lineTo(size * 0.721, size * 0.709)
    dock_gloss.lineTo(size * 0.279, size * 0.709)
    dock_gloss.closeSubpath()
    p.fillPath(dock_gloss, QColor(255, 255, 255, 72))

    slot_rect = QRectF(size * 0.340, size * 0.719, size * 0.320, size * 0.0215)
    slot_path = QPainterPath()
    slot_path.addRoundedRect(slot_rect, slot_rect.height() * 0.50, slot_rect.height() * 0.50)
    p.fillPath(slot_path, QColor(108, 167, 155, 72))
    p.setPen(QPen(QColor(255, 255, 255, 86), max(2.0, size * 0.008)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(dock_path)

    badge_shadow = QRadialGradient(QPointF(size * 0.50, size * 0.547), size * 0.210)
    badge_shadow.setColorAt(0.0, QColor(10, 45, 41, 62))
    badge_shadow.setColorAt(1.0, QColor(10, 45, 41, 0))
    badge_shadow_path = QPainterPath()
    badge_shadow_path.addEllipse(QRectF(size * 0.326, size * 0.496, size * 0.348, size * 0.102))
    p.fillPath(badge_shadow_path, QBrush(badge_shadow))

    badge_rect = QRectF(size * 0.316, size * 0.232, size * 0.368, size * 0.368)
    badge_path = QPainterPath()
    badge_path.addEllipse(badge_rect)
    badge_grad = QLinearGradient(badge_rect.topLeft(), badge_rect.bottomRight())
    badge_grad.setColorAt(0.0, QColor("#25a08f"))
    badge_grad.setColorAt(0.58, QColor("#147267"))
    badge_grad.setColorAt(1.0, QColor("#0a514c"))
    p.setPen(Qt.PenStyle.NoPen)
    p.fillPath(badge_path, QBrush(badge_grad))

    badge_glow = QRadialGradient(QPointF(size * 0.432, size * 0.336), size * 0.220)
    badge_glow.setColorAt(0.0, QColor(158, 244, 224, 142))
    badge_glow.setColorAt(0.40, QColor(158, 244, 224, 35))
    badge_glow.setColorAt(1.0, QColor(158, 244, 224, 0))
    p.fillPath(badge_path, QBrush(badge_glow))

    badge_highlight_path = QPainterPath()
    badge_highlight_path.addEllipse(QRectF(size * 0.305, size * 0.234, size * 0.258, size * 0.203))
    p.fillPath(badge_highlight_path, QColor(197, 255, 241, 32))
    p.setPen(QPen(QColor(216, 255, 246, 46), max(2.0, size * 0.012)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(badge_path)

    glyph_grad = QLinearGradient(QPointF(size * 0.50, size * 0.292), QPointF(size * 0.50, size * 0.623))
    glyph_grad.setColorAt(0.0, QColor("#f8fffd"))
    glyph_grad.setColorAt(1.0, QColor("#dbece6"))

    stem_rect = QRectF(size * 0.473, size * 0.293, size * 0.0547, size * 0.174)
    stem_path = QPainterPath()
    stem_path.addRoundedRect(stem_rect, size * 0.027, size * 0.027)
    head = QPainterPath()
    head.addPolygon(
        QPolygonF(
            [
                QPointF(size * 0.398, size * 0.445),
                QPointF(size * 0.50, size * 0.549),
                QPointF(size * 0.602, size * 0.445),
            ]
        )
    )
    tray_rect = QRectF(size * 0.400, size * 0.578, size * 0.199, size * 0.045)
    tray_path = QPainterPath()
    tray_path.addRoundedRect(tray_rect, tray_rect.height() * 0.50, tray_rect.height() * 0.50)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(8, 60, 54, 52))
    p.save()
    p.translate(0, size * 0.012)
    p.drawPath(stem_path)
    p.drawPath(head)
    p.drawPath(tray_path)
    p.restore()

    p.setBrush(QBrush(glyph_grad))
    p.drawPath(stem_path)
    p.drawPath(head)
    p.drawPath(tray_path)

    p.restore()

    p.setPen(QPen(QColor(249, 255, 253, 163), max(2.0, size * 0.008)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(tile_path)

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
        if not _draw_icon(size).save(str(output_path), "PNG"):
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
    image = _draw_icon(size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Failed to render icon image")
    buffer.seek(0)
    pil = Image.open(buffer)
    pil.save(
        output_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )


def write_icon_icns(output_path: Path, size: int) -> None:
    if HAS_QT and Image is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            write_icon_png(Path(tmp.name), size)
            pil = Image.open(tmp.name)
            pil.save(output_path, format="ICNS")
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
