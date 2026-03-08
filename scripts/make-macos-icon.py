#!/usr/bin/env python3
"""Generate app icons for yt-dlp-gui packaging."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

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

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - build-only dependency
    Image = None


def _draw_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # Rounded glass tile tuned to the app's mint glass theme.
    pad = size * 0.075
    tile = QRectF(pad, pad, size - (2 * pad), size - (2 * pad))
    radius = size * 0.225
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile, radius, radius)

    shadow_rect = tile.adjusted(size * 0.014, size * 0.030, -size * 0.014, size * 0.052)
    shadow_path = QPainterPath()
    shadow_path.addRoundedRect(shadow_rect, radius * 0.98, radius * 0.98)
    shadow_grad = QLinearGradient(
        shadow_rect.center().x(),
        shadow_rect.top(),
        shadow_rect.center().x(),
        shadow_rect.bottom(),
    )
    shadow_grad.setColorAt(0.0, QColor(6, 46, 39, 0))
    shadow_grad.setColorAt(0.42, QColor(6, 46, 39, 22))
    shadow_grad.setColorAt(1.0, QColor(6, 46, 39, 74))
    p.fillPath(shadow_path, QBrush(shadow_grad))

    base_grad = QLinearGradient(tile.topLeft(), QPointF(tile.right(), tile.bottom()))
    base_grad.setColorAt(0.0, QColor(246, 253, 251, 250))
    base_grad.setColorAt(0.26, QColor(226, 246, 240, 244))
    base_grad.setColorAt(0.67, QColor(184, 228, 218, 242))
    base_grad.setColorAt(1.0, QColor(138, 199, 188, 246))
    p.fillPath(tile_path, QBrush(base_grad))

    p.save()
    p.setClipPath(tile_path)

    glow = QRadialGradient(QPointF(size * 0.31, size * 0.23), size * 0.58)
    glow.setColorAt(0.0, QColor(255, 255, 255, 164))
    glow.setColorAt(0.42, QColor(255, 255, 255, 52))
    glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(tile, QBrush(glow))

    lower_pool = QRadialGradient(QPointF(size * 0.73, size * 0.86), size * 0.54)
    lower_pool.setColorAt(0.0, QColor(84, 182, 162, 84))
    lower_pool.setColorAt(0.45, QColor(84, 182, 162, 26))
    lower_pool.setColorAt(1.0, QColor(96, 181, 164, 0))
    p.fillRect(tile, QBrush(lower_pool))

    lens_path = QPainterPath()
    lens_path.addEllipse(
        QRectF(
            tile.left() - (size * 0.13),
            tile.top() - (size * 0.08),
            tile.width() * 0.84,
            tile.height() * 0.44,
        )
    )
    p.fillPath(lens_path, QColor(255, 255, 255, 54))

    sweep_path = QPainterPath()
    sweep_path.addEllipse(
        QRectF(
            tile.right() - (tile.width() * 0.52),
            tile.top() + (tile.height() * 0.08),
            tile.width() * 0.82,
            tile.height() * 0.82,
        )
    )
    p.fillPath(sweep_path, QColor(116, 214, 193, 42))

    orb_rect = QRectF(size * 0.235, size * 0.225, size * 0.53, size * 0.53)
    orb_path = QPainterPath()
    orb_path.addEllipse(orb_rect)
    orb_grad = QRadialGradient(
        QPointF(orb_rect.left() + (orb_rect.width() * 0.34), orb_rect.top() + (orb_rect.height() * 0.28)),
        orb_rect.width() * 0.70,
    )
    orb_grad.setColorAt(0.0, QColor(255, 255, 255, 214))
    orb_grad.setColorAt(0.34, QColor(240, 251, 247, 132))
    orb_grad.setColorAt(1.0, QColor(223, 243, 236, 72))
    p.fillPath(orb_path, QBrush(orb_grad))

    orb_tint = QRadialGradient(
        QPointF(orb_rect.center().x() + (size * 0.08), orb_rect.center().y() + (size * 0.10)),
        orb_rect.width() * 0.72,
    )
    orb_tint.setColorAt(0.0, QColor(97, 185, 165, 46))
    orb_tint.setColorAt(1.0, QColor(97, 185, 165, 0))
    p.fillPath(orb_path, QBrush(orb_tint))

    orb_gloss_rect = QRectF(
        orb_rect.left() + (size * 0.040),
        orb_rect.top() + (size * 0.032),
        orb_rect.width() - (size * 0.080),
        orb_rect.height() * 0.36,
    )
    orb_gloss_path = QPainterPath()
    orb_gloss_path.addEllipse(orb_gloss_rect)
    orb_gloss_grad = QLinearGradient(orb_gloss_rect.topLeft(), orb_gloss_rect.bottomLeft())
    orb_gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 124))
    orb_gloss_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(orb_gloss_path, QBrush(orb_gloss_grad))

    p.setPen(QPen(QColor(255, 255, 255, 176), max(2.0, size * 0.009)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(orb_path)

    glyph_grad = QLinearGradient(
        QPointF(size * 0.50, size * 0.34),
        QPointF(size * 0.50, size * 0.76),
    )
    glyph_grad.setColorAt(0.0, QColor("#196d62"))
    glyph_grad.setColorAt(1.0, QColor("#0d4f47"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(glyph_grad))

    stem_w = size * 0.088
    stem_h = size * 0.220
    stem_rect = QRectF((size - stem_w) / 2, size * 0.336, stem_w, stem_h)
    stem_path = QPainterPath()
    stem_radius = size * 0.020
    stem_path.addRoundedRect(stem_rect, stem_radius, stem_radius)
    p.drawPath(stem_path)

    head = QPolygonF(
        [
            QPointF(size * 0.382, size * 0.548),
            QPointF(size * 0.50, size * 0.682),
            QPointF(size * 0.618, size * 0.548),
        ]
    )
    p.drawPolygon(head)

    tray_h = size * 0.070
    tray_rect = QRectF(size * 0.328, size * 0.718, size * 0.344, tray_h)
    tray_path = QPainterPath()
    tray_path.addRoundedRect(tray_rect, tray_h * 0.46, tray_h * 0.46)
    p.drawPath(tray_path)

    glyph_gloss = QLinearGradient(stem_rect.topLeft(), stem_rect.bottomLeft())
    glyph_gloss.setColorAt(0.0, QColor(255, 255, 255, 78))
    glyph_gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(glyph_gloss))
    p.drawPath(stem_path)

    caustic_rect = QRectF(tile.left() + (size * 0.12), size * 0.77, tile.width() * 0.48, size * 0.10)
    caustic_path = QPainterPath()
    caustic_path.addEllipse(caustic_rect)
    caustic_grad = QLinearGradient(caustic_rect.topLeft(), caustic_rect.bottomLeft())
    caustic_grad.setColorAt(0.0, QColor(255, 255, 255, 32))
    caustic_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(caustic_path, QBrush(caustic_grad))

    p.restore()

    p.setPen(QPen(QColor(255, 255, 255, 176), max(2.0, size * 0.011)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(tile_path)

    p.end()
    return image


def write_icon_png(output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not _draw_icon(size).save(str(output_path), "PNG"):
        raise RuntimeError(f"Failed to write {output_path}")


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
    if Image is None:
        raise RuntimeError("Pillow is required to generate .icns files")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        write_icon_png(Path(tmp.name), size)
        pil = Image.open(tmp.name)
        pil.save(output_path, format="ICNS")


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
