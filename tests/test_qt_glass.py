import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QAbstractAnimation, QPoint, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from gui.qt import glass, style
    from gui.qt.widgets import ButtonSpec, SegmentedRailSpec, build_button, build_segmented_rail

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is required for glass rendering tests")
class TestQtGlass(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {
            "YT_DLP_GUI_OPAQUE": "0",
            "YT_DLP_GUI_REDUCE_MOTION": "0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = QWidget()
        self.root.setStyleSheet(style.build_stylesheet("/tmp/unused-arrow.svg"))
        self.root.resize(440, 240)
        self.root.show()
        self.addCleanup(self.root.deleteLater)
        self.addCleanup(self.root.close)

    def button(self, object_name="primaryActionButton", text="Download"):
        button = build_button(self.root, spec=ButtonSpec(text, object_name=object_name))
        button.setGeometry(20, 20, 180, 76)
        button.show()
        QApplication.processEvents()
        button.clearFocus()
        QTest.mouseMove(self.root, QPoint(420, 220))
        button._hover_animation.stop()
        button._set_hover_amount(0)
        return button

    def test_reflections_are_clipped_and_do_not_change_opacity(self) -> None:
        image = QImage(180, 60, QImage.Format.Format_ARGB32)
        base = QColor("#23755b")
        image.fill(base)
        painter = QPainter(image)
        glass.paint_glass(painter, QRectF(0, 0, 180, 60), 16)
        painter.end()
        self.assertEqual(image.pixelColor(0, 0), base)
        self.assertEqual(image.pixelColor(0, 30), base)
        self.assertGreater(image.pixelColor(90, 3).lightness(), base.lightness())
        self.assertEqual(image.pixelColor(90, 30).alpha(), 255)

    def test_higher_contrast_and_opaque_override_disable_glass(self) -> None:
        for preference, expected in (
            (Qt.ContrastPreference.NoPreference, True),
            (Qt.ContrastPreference.HighContrast, False),
        ):
            hints = (None, SimpleNamespace(contrastPreference=lambda: preference))
            with patch.object(self.app, "_glass_accessibility_hints", hints, create=True):
                self.assertEqual(glass.glass_enabled(), expected)
                with patch.dict(os.environ, {"YT_DLP_GUI_OPAQUE": "1"}):
                    self.assertFalse(glass.glass_enabled())

    def test_accessibility_wrappers_survive_repeated_paints(self) -> None:
        for _ in range(10):
            self.assertIsInstance(glass.glass_enabled(), bool)
            QApplication.processEvents()

    def test_glass_keeps_button_geometry_and_text_pixels(self) -> None:
        button = self.button()
        geometry, hint = button.geometry(), button.sizeHint()
        with patch("gui.qt.glass.glass_enabled", return_value=True):
            glossy = button.grab().toImage()
        with patch("gui.qt.glass.glass_enabled", return_value=False):
            matte = button.grab().toImage()
        self.assertNotEqual(glossy, matte)
        self.assertEqual(button.geometry(), geometry)
        self.assertEqual(button.sizeHint(), hint)
        # Fully covered text pixels must be identical, not tinted by the reflection.
        text_pixels = 0
        for y in range(matte.height() // 3, matte.height() * 2 // 3):
            for x in range(20, matte.width() - 20):
                color = matte.pixelColor(x, y)
                if color == QColor(style._PALETTE["text_inverse"]):
                    text_pixels += 1
                    self.assertEqual(glossy.pixelColor(x, y), color)
        self.assertGreater(text_pixels, 20)

    def test_disabled_buttons_remain_matte(self) -> None:
        button = self.button()
        button.setEnabled(False)
        with patch("gui.qt.glass.glass_enabled", return_value=True):
            glossy = button.grab().toImage()
        with patch("gui.qt.glass.glass_enabled", return_value=False):
            matte = button.grab().toImage()
        self.assertEqual(glossy, matte)

    def test_action_text_contrast_across_interaction_states(self) -> None:
        def luminance(color):
            channels = (color.redF(), color.greenF(), color.blueF())
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                      for value in channels]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        button = self.button(text="")
        foreground = luminance(QColor(style._PALETTE["text_inverse"]))
        with patch("gui.qt.glass.glass_enabled", return_value=True), patch(
            "gui.qt.glass.motion_enabled", return_value=False
        ):
            for hover, pressed in ((False, False), (True, False), (True, True)):
                with self.subTest(hover=hover, pressed=pressed):
                    button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, hover)
                    button._set_hover_amount(float(hover))
                    button.setDown(pressed)
                    image = button.grab().toImage()
                    for y in range(image.height() // 2 - 8, image.height() // 2 + 8):
                        background = luminance(image.pixelColor(image.width() // 2, y))
                        self.assertGreaterEqual((foreground + 0.05) / (background + 0.05), 4.5)

    def test_other_buttons_do_not_gain_glass(self) -> None:
        button = self.button("ghostButton", "Browse")
        self.assertEqual(button.property("glassRadius"), -1.0)
        with patch("gui.qt.glass.glass_enabled", return_value=True):
            glossy = button.grab().toImage()
        with patch("gui.qt.glass.glass_enabled", return_value=False):
            matte = button.grab().toImage()
        self.assertEqual(glossy, matte)

    def test_hover_animation_finishes_and_stops_when_hidden_or_disabled(self) -> None:
        button = self.button()
        with patch("gui.qt.glass.motion_enabled", return_value=True), patch(
            "gui.qt.glass.glass_enabled", return_value=True
        ):
            button._animate_hover(1.0)
            QTest.qWait(220)
            self.assertAlmostEqual(button._hover_amount, 1.0)
            self.assertEqual(button._hover_animation.state(), QAbstractAnimation.State.Stopped)
            button._animate_hover(0.0)
            button.hide()
            self.assertEqual(button._hover_amount, 0.0)
            self.assertEqual(button._hover_animation.state(), QAbstractAnimation.State.Stopped)
            button.show()
            button._animate_hover(1.0)
            button.setEnabled(False)
            self.assertEqual(button._hover_amount, 0.0)
            self.assertEqual(button._hover_animation.state(), QAbstractAnimation.State.Stopped)

    def test_reduced_motion_uses_instant_hover_and_selection(self) -> None:
        button = self.button()
        rail, buttons = build_segmented_rail(self.root, spec=SegmentedRailSpec(
            object_name="topNavRail",
            button_specs=tuple(ButtonSpec(name, object_name="topNavButton", checkable=True,
                                         auto_exclusive=True) for name in ("One", "Two")),
        ))
        rail.move(20, 130)
        rail.show()
        buttons[0].setChecked(True)
        QApplication.processEvents()
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}), patch(
            "gui.qt.glass.glass_enabled", return_value=True
        ):
            button._animate_hover(1.0)
            self.assertEqual(button._hover_amount, 1.0)
            self.assertEqual(button._hover_animation.state(), QAbstractAnimation.State.Stopped)
            buttons[1].setChecked(True)
            rail.sync_selection()
            self.assertIsNone(rail._selection_anim)
            self.assertEqual(rail._selection_rect, buttons[1].geometry())

    def test_native_animation_hint_is_respected(self) -> None:
        button = self.button()
        with patch.object(button, "style", return_value=SimpleNamespace(styleHint=lambda *args: 0)):
            self.assertFalse(glass.motion_enabled(button))

    def test_keyboard_and_mouse_activation_still_work(self) -> None:
        button = self.button()
        clicked = []
        button.clicked.connect(lambda: clicked.append(True))
        button.setFocus(Qt.FocusReason.TabFocusReason)
        QApplication.processEvents()
        self.assertTrue(button.hasFocus())
        with patch("gui.qt.glass.glass_enabled", return_value=True):
            focused = button.grab().toImage()
            QTest.keyClick(button, Qt.Key.Key_Space)
            button.clearFocus()
            self.assertNotEqual(focused, button.grab().toImage())
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertEqual(len(clicked), 2)


if __name__ == "__main__":
    unittest.main()
