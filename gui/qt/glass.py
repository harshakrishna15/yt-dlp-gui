from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QEvent, Property, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QWidget,
)


def glass_enabled() -> bool:
    if os.environ.get("YT_DLP_GUI_OPAQUE") == "1":
        return False
    app = QApplication.instance()
    if app is None:
        return True
    # Keep both wrappers alive: PySide can otherwise dispose of the child hints.
    hints = getattr(app, "_glass_accessibility_hints", None)
    if hints is None:
        style_hints = app.styleHints()
        hints = (style_hints, style_hints.accessibility())
        setattr(app, "_glass_accessibility_hints", hints)
    return hints[1].contrastPreference() != Qt.ContrastPreference.HighContrast


def motion_enabled(widget: QWidget) -> bool:
    return (
        os.environ.get("YT_DLP_GUI_REDUCE_MOTION") != "1"
        and glass_enabled()
        and bool(widget.style().styleHint(QStyle.StyleHint.SH_Widget_Animate, None, widget))
    )


def paint_glass(
    painter: QPainter,
    rect: QRectF,
    radius: float,
    *,
    strength: float = 1.0,
    hover: float = 0.0,
    pressed: bool = False,
) -> None:
    if strength <= 0 or rect.isEmpty():
        return
    bounds = rect.adjusted(1.0, 1.0, -1.0, -1.0)
    radius = max(0.0, min(radius - 1.0, bounds.width() / 2, bounds.height() / 2))
    path = QPainterPath()
    path.addRoundedRect(bounds, radius, radius)
    strength *= 0.4 if pressed else 1.0

    def light(alpha: float) -> QColor:
        return QColor(235, 249, 255, round(alpha * strength))

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(path)

    # Reflections stay inside the control; the underlying surface remains opaque.
    sheen = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
    sheen.setColorAt(0.0, light(42 + hover * 22))
    sheen.setColorAt(0.32, light(12 + hover * 8))
    sheen.setColorAt(0.52, light(0))
    sheen.setColorAt(0.82, QColor(0, 0, 0, round(12 * strength)))
    sheen.setColorAt(1.0, light(9))
    painter.fillPath(path, sheen)

    if hover > 0:
        reflection = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        reflection.setColorAt(0, light(0))
        reflection.setColorAt(0.3, light(18 * hover))
        reflection.setColorAt(0.6, light(0))
        painter.fillPath(path, reflection)

    rim = QLinearGradient(bounds.topLeft(), bounds.bottomLeft())
    rim.setColorAt(0.0, light(125 + hover * 45))
    rim.setColorAt(0.3, light(35))
    rim.setColorAt(0.65, light(8))
    rim.setColorAt(1.0, light(42))
    painter.setPen(QPen(rim, 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.restore()


class GlassFrame(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._glass_radius = -1.0

    def _get_glass_radius(self) -> float:
        return self._glass_radius

    def _set_glass_radius(self, value: float) -> None:
        self._glass_radius = float(value)
        self.update()

    glassRadius = Property(float, _get_glass_radius, _set_glass_radius)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._glass_radius >= 0 and self.isEnabled() and glass_enabled():
            painter = QPainter(self)
            paint_glass(painter, QRectF(self.rect()), self._glass_radius)


class GlassButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._glass_radius = -1.0
        self._glass_hover_only = False
        self._hover_amount = 0.0
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(160)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover_amount)

    def _get_glass_radius(self) -> float:
        return self._glass_radius

    def _set_glass_radius(self, value: float) -> None:
        self._glass_radius = float(value)
        self.update()

    glassRadius = Property(float, _get_glass_radius, _set_glass_radius)

    def _get_glass_hover_only(self) -> bool:
        return self._glass_hover_only

    def _set_glass_hover_only(self, value: bool) -> None:
        self._glass_hover_only = bool(value)
        self.update()

    glassHoverOnly = Property(bool, _get_glass_hover_only, _set_glass_hover_only)

    def _set_hover_amount(self, value: float) -> None:
        self._hover_amount = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        if self._glass_radius < 0 or not self.isEnabled() or not glass_enabled():
            self._set_hover_amount(0.0)
        elif not motion_enabled(self):
            self._set_hover_amount(target)
        else:
            self._hover_animation.setStartValue(self._hover_amount)
            self._hover_animation.setEndValue(target)
            self._hover_animation.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._animate_hover(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate_hover(0.0)

    def hideEvent(self, event) -> None:
        self._hover_animation.stop()
        self._set_hover_amount(0.0)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.Type.EnabledChange, QEvent.Type.PaletteChange}:
            self._hover_animation.stop()
            self._set_hover_amount(0.0)

    def paintEvent(self, event) -> None:
        if self._glass_radius < 0 or not self.isEnabled() or not glass_enabled():
            super().paintEvent(event)
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        painter = QPainter(self)
        style = self.style()
        style.drawControl(QStyle.ControlElement.CE_PushButtonBevel, option, painter, self)
        paint_glass(
            painter,
            QRectF(self.rect()),
            self._glass_radius,
            strength=self._hover_amount * 0.6 if self._glass_hover_only else 1.0,
            hover=self._hover_amount,
            pressed=self.isDown(),
        )

        # Draw the label last, so the sheen never washes out text or icons.
        label = QStyleOptionButton(option)
        label.rect = style.subElementRect(QStyle.SubElement.SE_PushButtonContents, option, self)
        style.drawControl(QStyle.ControlElement.CE_PushButtonLabel, label, painter, self)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#a3e5cf"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            focus_rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
            radius = max(0.0, min(self._glass_radius - 3, focus_rect.height() / 2))
            painter.drawRoundedRect(focus_rect, radius, radius)
