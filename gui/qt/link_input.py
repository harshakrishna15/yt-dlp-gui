from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
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
    row = QWidget(parent)
    row.setObjectName("commandBar")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 1, 0)
    row_layout.setSpacing(10)

    url_edit = QLineEdit(row)
    url_edit.setObjectName("urlInputField")
    url_edit.setFrame(False)
    url_edit.setMinimumWidth(0)
    url_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    url_edit.setPlaceholderText("Paste a video or playlist URL")
    url_edit.textChanged.connect(on_url_changed)
    url_edit.returnPressed.connect(on_fetch_formats)

    paste_button = QPushButton("Paste", row)
    paste_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    paste_button.clicked.connect(on_paste_url)

    analyze_button = QPushButton("Analyze URL", row)
    analyze_button.setObjectName("analyzeUrlButton")
    analyze_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    analyze_button.clicked.connect(on_analyze_url)

    row_layout.addWidget(url_edit, stretch=1)
    row_layout.addWidget(paste_button)
    row_layout.addWidget(analyze_button)

    return LinkInputRefs(
        row=row,
        url_edit=url_edit,
        paste_button=paste_button,
        analyze_button=analyze_button,
    )
