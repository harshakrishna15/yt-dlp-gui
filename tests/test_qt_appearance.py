import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QPoint, Qt, QVariantAnimation
    from PySide6.QtGui import QColor, QFontInfo
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget

    from gui.qt import style
    from gui.qt.widgets import ButtonSpec, SegmentedRailSpec, build_button, build_segmented_rail

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is required for appearance tests")
class TestQtAppearance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.root = QWidget()
        self.root.setStyleSheet(style.build_stylesheet("/tmp/unused-arrow.svg"))
        self.root.resize(440, 240)
        self.root.show()
        self.addCleanup(self.root.deleteLater)
        self.addCleanup(self.root.close)

    def button(self, text="Download"):
        button = build_button(self.root, spec=ButtonSpec(text, object_name="primaryActionButton"))
        button.setGeometry(20, 20, 180, 40)
        button.show()
        QApplication.processEvents()
        button.clearFocus()
        QTest.mouseMove(self.root, QPoint(420, 220))
        return button

    def test_controls_are_flat_without_hover_animations(self) -> None:
        button = self.button(text="")
        image = button.grab().toImage()
        pixels = {image.pixelColor(90, y).name() for y in range(8, 32)}
        self.assertEqual(len(pixels), 1)
        self.assertEqual(button.findChildren(QVariantAnimation), [])

    def test_styles_use_system_font_and_small_corners(self) -> None:
        stylesheet = self.root.styleSheet()
        self.assertNotIn("font-family", stylesheet)
        self.assertNotIn("glass", stylesheet)
        self.assertTrue(all(int(radius) <= 8 for radius in re.findall(
            r"border-radius: (\d+)px", stylesheet
        )))
        self.assertEqual(QFontInfo(self.button().font()).family(), QFontInfo(self.app.font()).family())

    def test_action_text_contrast_across_interaction_states(self) -> None:
        def luminance(color):
            channels = (color.redF(), color.greenF(), color.blueF())
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                      for value in channels]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        button = self.button(text="")
        foreground = luminance(QColor(style._PALETTE["text_inverse"]))
        for hover, pressed in ((False, False), (True, False), (True, True)):
            with self.subTest(hover=hover, pressed=pressed):
                button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, hover)
                button.setDown(pressed)
                image = button.grab().toImage()
                background = luminance(image.pixelColor(90, 20))
                self.assertGreaterEqual((foreground + 0.05) / (background + 0.05), 4.5)

    def test_keyboard_focus_and_activation_remain_visible_and_functional(self) -> None:
        button = self.button()
        clicked = []
        button.clicked.connect(lambda: clicked.append(True))
        button.setFocus(Qt.FocusReason.TabFocusReason)
        QApplication.processEvents()
        self.assertTrue(button.hasFocus())
        focused = button.grab().toImage()
        QTest.keyClick(button, Qt.Key.Key_Space)
        button.clearFocus()
        self.assertNotEqual(focused, button.grab().toImage())
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        button.setEnabled(False)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertEqual(len(clicked), 2)

    def rail(self):
        rail, buttons = build_segmented_rail(self.root, spec=SegmentedRailSpec(
            object_name="topNavRail",
            button_specs=tuple(ButtonSpec(name, object_name="topNavButton", checkable=True,
                                         auto_exclusive=True) for name in ("One", "Two")),
        ))
        rail.move(20, 130)
        rail.show()
        buttons[0].setChecked(True)
        QApplication.processEvents()
        return rail, buttons

    def test_reduced_motion_uses_instant_selection(self) -> None:
        rail, buttons = self.rail()
        with patch.dict(os.environ, {"YT_DLP_GUI_REDUCE_MOTION": "1"}):
            buttons[1].setChecked(True)
            rail.sync_selection()
            self.assertIsNone(rail._selection_anim)
            self.assertEqual(rail._selection_rect, buttons[1].geometry())

    def test_native_animation_hint_is_respected(self) -> None:
        rail, buttons = self.rail()
        with patch.object(rail, "style", return_value=SimpleNamespace(styleHint=lambda *args: 0)):
            buttons[1].setChecked(True)
            rail.sync_selection()
            self.assertIsNone(rail._selection_anim)
            self.assertEqual(rail._selection_rect, buttons[1].geometry())


if __name__ == "__main__":
    unittest.main()
