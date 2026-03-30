from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import (
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from .widgets import (
    ButtonSpec,
    LayoutConfig,
    LineEditSpec,
    WidgetConfig,
    build_button,
    build_hbox,
    build_line_edit,
)


@dataclass(frozen=True)
class LinkInputRefs:
    row: QWidget
    url_edit: QLineEdit
    paste_button: QPushButton
    analyze_button: QPushButton


def build_link_input_module(
    parent: QWidget,
    *,
    on_url_changed: Callable[[], None],
    on_fetch_formats: Callable[[], None],
    on_paste_url: Callable[[], None],
    on_analyze_url: Callable[[], None],
) -> LinkInputRefs:
    row_shell = build_hbox(
        parent,
        widget_config=WidgetConfig(object_name="commandBar"),
        layout_config=LayoutConfig(margins=(0, 0, 1, 0), spacing=10),
    )
    row = row_shell.widget
    row_layout = row_shell.layout

    url_edit = build_line_edit(
        row,
        spec=LineEditSpec(
            widget_config=WidgetConfig(
                object_name="urlInputField",
                minimum_width=0,
                size_policy=(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                ),
            ),
            placeholder_text="Paste a video or playlist URL",
            frame=False,
            on_text_changed=on_url_changed,
            on_return_pressed=on_fetch_formats,
        ),
    )

    paste_button = build_button(
        row,
        spec=ButtonSpec(
            text="Paste",
            size_policy=(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed),
            on_click=on_paste_url,
        ),
    )

    analyze_button = build_button(
        row,
        spec=ButtonSpec(
            text="Analyze URL",
            object_name="analyzeUrlButton",
            size_policy=(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed),
            on_click=on_analyze_url,
        ),
    )

    row_layout.addWidget(url_edit, stretch=1)
    row_layout.addWidget(paste_button)
    row_layout.addWidget(analyze_button)

    return LinkInputRefs(
        row=row,
        url_edit=url_edit,
        paste_button=paste_button,
        analyze_button=analyze_button,
    )
