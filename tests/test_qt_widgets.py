import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget

    from gui.qt.widgets import (
        ButtonSpec,
        LayoutConfig,
        SegmentedRailSpec,
        WidgetConfig,
        build_button,
        build_grid,
        build_segmented_rail,
        build_vbox,
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

    def test_build_vbox_applies_widget_and_layout_config(self) -> None:
        parent = QWidget()

        shell = build_vbox(
            parent,
            widget_config=WidgetConfig(
                object_name="testShell",
                minimum_width=120,
                fixed_height=44,
                visible=False,
            ),
            layout_config=LayoutConfig(
                margins=(1, 2, 3, 4),
                spacing=9,
            ),
        )

        widget = shell.widget
        layout = shell.layout
        margins = layout.contentsMargins()

        self.assertEqual(widget.objectName(), "testShell")
        self.assertEqual(widget.minimumWidth(), 120)
        self.assertEqual(widget.minimumHeight(), 44)
        self.assertEqual(widget.maximumHeight(), 44)
        self.assertTrue(widget.isHidden())
        self.assertEqual(
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            (1, 2, 3, 4),
        )
        self.assertEqual(layout.spacing(), 9)

    def test_build_grid_supports_axis_specific_spacing(self) -> None:
        parent = QWidget()

        shell = build_grid(
            parent,
            widget_config=WidgetConfig(
                size_policy=(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            layout_config=LayoutConfig(
                margins=(5, 6, 7, 8),
                horizontal_spacing=11,
                vertical_spacing=13,
            ),
        )

        widget = shell.widget
        layout = shell.layout
        margins = layout.contentsMargins()

        self.assertEqual(
            widget.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Expanding,
        )
        self.assertEqual(
            widget.sizePolicy().verticalPolicy(),
            QSizePolicy.Policy.Fixed,
        )
        self.assertEqual(
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            (5, 6, 7, 8),
        )
        self.assertEqual(layout.horizontalSpacing(), 11)
        self.assertEqual(layout.verticalSpacing(), 13)


if __name__ == "__main__":
    unittest.main()
