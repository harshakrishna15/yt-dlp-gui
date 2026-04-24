from __future__ import annotations

from tempfile import gettempdir
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .assets_manifest import asset_path


def _resolved_size(renderer: QSvgRenderer, size: QSize | None) -> QSize:
    if size is not None and size.isValid():
        return QSize(max(1, size.width()), max(1, size.height()))
    default_size = renderer.defaultSize()
    if default_size.isValid():
        return QSize(max(1, default_size.width()), max(1, default_size.height()))
    return QSize(16, 16)


def render_svg_pixmap(filename: str, *, size: QSize | None = None) -> QPixmap:
    path = asset_path(filename)
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return QPixmap()

    render_size = _resolved_size(renderer, size)
    pixmap = QPixmap(render_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(
            painter,
            QRectF(0, 0, float(render_size.width()), float(render_size.height())),
        )
    finally:
        painter.end()
    return pixmap


def load_icon_asset(filename: str, *, size: QSize | None = None) -> QIcon:
    path = asset_path(filename)
    if not path.exists():
        return QIcon()

    icon = QIcon(path.as_posix())
    if not icon.isNull():
        return icon

    if path.suffix.lower() != ".svg":
        return QIcon()

    pixmap = render_svg_pixmap(filename, size=size)
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def style_asset_path(filename: str, *, size: QSize | None = None) -> str:
    path = asset_path(filename)
    if path.suffix.lower() != ".svg":
        return path.as_posix()

    pixmap = render_svg_pixmap(filename, size=size)
    if pixmap.isNull():
        return path.as_posix()

    render_size = pixmap.size()
    cache_dir = Path(gettempdir()) / "yt-dlp-gui" / "qt-assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / (
        f"{path.stem}-{render_size.width()}x{render_size.height()}.png"
    )
    if not output_path.exists():
        pixmap.save(str(output_path), "PNG")
    return output_path.as_posix()
