from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QComboBox


class _QtSignals(QObject):
    formats_loaded = Signal(int, str, object, bool, bool)
    progress = Signal(object)
    log = Signal(str)
    download_done = Signal(str)
    queue_item_done = Signal(bool, bool)
    record_output = Signal(str, str)


def _style_combo_popup(combo: QComboBox, *, border_color: str = "#bfdad1") -> None:
    popup = combo.view().window()
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    popup.setAutoFillBackground(True)
    popup.setContentsMargins(0, 0, 0, 0)
    popup.setStyleSheet(
        f"""
        background: #ffffff;
        border: 1px solid {border_color};
        border-radius: 8px;
        """
    )


class _NativeComboBox(QComboBox):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._before_popup_callback: Callable[[], None] | None = None

    def set_before_popup_callback(
        self, callback: Callable[[], None] | None
    ) -> None:
        self._before_popup_callback = callback

    def showPopup(self) -> None:
        if self._before_popup_callback is not None:
            self._before_popup_callback()
        super().showPopup()
        if self._before_popup_callback is not None:
            self._before_popup_callback()
        _style_combo_popup(self)
