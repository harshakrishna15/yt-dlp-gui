import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget

    from gui.qt.widgets import (
        ButtonSpec,
        SegmentedRailSpec,
        build_button,
        build_segmented_rail,
    )

    HAS_QT = True
except ModuleNotFoundError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is required for Qt widget tests")
class TestQtWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_build_button_applies_text_size_and_actions(self) -> None:
        parent = QWidget()
        clicked: list[str] = []
        toggled: list[bool] = []

        button = build_button(
            parent,
            spec=ButtonSpec(
                text="Download",
                object_name="primaryActionButton",
                on_click=lambda: clicked.append("clicked"),
                on_toggled=lambda checked: toggled.append(bool(checked)),
                checkable=True,
                size_policy=(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                ),
                minimum_width=160,
                fixed_height=36,
            ),
        )

        self.assertEqual(button.text(), "Download")
        self.assertEqual(button.objectName(), "primaryActionButton")
        self.assertTrue(button.isCheckable())
        self.assertEqual(
            button.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Expanding,
        )
        self.assertEqual(
            button.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Fixed,
        )
        self.assertEqual(button.minimumWidth(), 160)
        self.assertEqual(button.minimumHeight(), 36)
        self.assertEqual(button.maximumHeight(), 36)

        button.click()

        self.assertEqual(clicked, ["clicked"])
        self.assertEqual(toggled, [True])

    def test_build_segmented_rail_uses_shared_button_specs(self) -> None:
        parent = QWidget()
        toggled: list[tuple[str, bool]] = []

        rail, buttons = build_segmented_rail(
            parent,
            spec=SegmentedRailSpec(
                object_name="contentModeSegment",
                layout_margins=(3, 4, 5, 6),
                layout_spacing=7,
                trailing_stretch=True,
                button_specs=(
                    ButtonSpec(
                        text="Video and Audio",
                        object_name="contentModeButton",
                        checkable=True,
                        auto_exclusive=True,
                        on_toggled=lambda checked: toggled.append(("video", bool(checked))),
                    ),
                    ButtonSpec(
                        text="Audio only",
                        object_name="contentModeButton",
                        checkable=True,
                        auto_exclusive=True,
                        on_toggled=lambda checked: toggled.append(("audio", bool(checked))),
                    ),
                ),
            ),
        )

        first_button, second_button = buttons
        layout = rail.layout()

        self.assertEqual(rail.objectName(), "contentModeSegment")
        self.assertIsNotNone(layout)
        assert layout is not None
        margins = layout.contentsMargins()
        self.assertEqual((margins.left(), margins.top(), margins.right(), margins.bottom()), (3, 4, 5, 6))
        self.assertEqual(layout.spacing(), 7)
        self.assertEqual(first_button.text(), "Video and Audio")
        self.assertEqual(second_button.text(), "Audio only")
        self.assertTrue(first_button.isCheckable())
        self.assertTrue(first_button.autoExclusive())
        self.assertEqual(layout.count(), 3)
        self.assertIsNotNone(layout.itemAt(2).spacerItem())

        first_button.click()
        second_button.click()

        self.assertEqual(
            toggled,
            [("video", True), ("video", False), ("audio", True)],
        )


if __name__ == "__main__":
    unittest.main()
