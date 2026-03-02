#!/usr/bin/env python3
"""Generate a high-resolution macOS app icon PNG for yt-dlp-gui."""

from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPolygonF


def _draw_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # Base rounded tile.
    pad = size * 0.075
    tile = QRectF(pad, pad, size - (2 * pad), size - (2 * pad))
    radius = size * 0.22
    tile_path = QPainterPath()
    tile_path.addRoundedRect(tile, radius, radius)

    base_grad = QLinearGradient(tile.topLeft(), tile.bottomLeft())
    base_grad.setColorAt(0.0, QColor("#77a8e2"))
    base_grad.setColorAt(0.55, QColor("#4e86c8"))
    base_grad.setColorAt(1.0, QColor("#2f6fb5"))
    p.fillPath(tile_path, QBrush(base_grad))

    # Soft highlight at the top for depth.
    top_band = QRectF(tile.left(), tile.top(), tile.width(), tile.height() * 0.47)
    hi_path = QPainterPath()
    hi_path.addRoundedRect(top_band, radius, radius)
    hi_grad = QLinearGradient(top_band.topLeft(), top_band.bottomLeft())
    hi_grad.setColorAt(0.0, QColor(255, 255, 255, 92))
    hi_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(hi_path, QBrush(hi_grad))

    # Download glyph (arrow + tray).
    p.setPen(Qt.PenStyle.NoPen)
    white = QColor("#f9fcff")
    p.setBrush(white)

    stem_w = size * 0.105
    stem_h = size * 0.255
    stem_rect = QRectF((size - stem_w) / 2, size * 0.295, stem_w, stem_h)
    stem_path = QPainterPath()
    stem_radius = size * 0.018
    stem_path.addRoundedRect(stem_rect, stem_radius, stem_radius)
    p.drawPath(stem_path)

    head = QPolygonF(
        [
            QPointF(size * 0.37, size * 0.53),
            QPointF(size * 0.50, size * 0.68),
            QPointF(size * 0.63, size * 0.53),
        ]
    )
    p.drawPolygon(head)

    tray_h = size * 0.085
    tray_rect = QRectF(size * 0.29, size * 0.705, size * 0.42, tray_h)
    tray_path = QPainterPath()
    tray_path.addRoundedRect(tray_rect, tray_h * 0.45, tray_h * 0.45)
    p.drawPath(tray_path)

    # Small "play" badge nodding to video content.
    badge_r = size * 0.14
    badge_cx = tile.right() - (badge_r * 0.82)
    badge_cy = tile.top() + (badge_r * 0.9)
    p.setBrush(QColor("#ef4f4a"))
    p.drawEllipse(QPointF(badge_cx, badge_cy), badge_r, badge_r)

    p.setBrush(QColor("#fffaf8"))
    play = QPolygonF(
        [
            QPointF(badge_cx - badge_r * 0.33, badge_cy - badge_r * 0.45),
            QPointF(badge_cx - badge_r * 0.33, badge_cy + badge_r * 0.45),
            QPointF(badge_cx + badge_r * 0.50, badge_cy),
        ]
    )
    p.drawPolygon(play)

    p.end()
    return image


def write_icon_png(output_path: Path, size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not _draw_icon(size).save(str(output_path), "PNG"):
        raise RuntimeError(f"Failed to write {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a macOS icon PNG for yt-dlp-gui")
    parser.add_argument(
        "--output",
        default="build/yt-dlp-gui-icon.png",
        help="Output path for the generated PNG icon",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Square icon size in pixels (default: 1024)",
    )
    args = parser.parse_args()

    write_icon_png(Path(args.output), int(args.size))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
