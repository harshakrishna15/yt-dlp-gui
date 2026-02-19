from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QComboBox


class _QtSignals(QObject):
    formats_loaded = Signal(int, str, object, bool, bool)
    progress = Signal(object)
    log = Signal(str)
    download_done = Signal(str)
    queue_item_done = Signal(bool, bool)
    record_output = Signal(str, str)


def _style_combo_popup(combo: QComboBox, *, border_color: str = "#cec6b9") -> None:
    popup = combo.view().window()
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    popup.setAutoFillBackground(True)
    popup.setContentsMargins(0, 0, 0, 0)
    popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    popup.setStyleSheet(
        f"""
        background: #fcfaf6;
        border: 1px solid {border_color};
        border-radius: 10px;
        """
    )


class _NativeComboBox(QComboBox):
    def showPopup(self) -> None:
        super().showPopup()
        _style_combo_popup(self)


class _PanelSelectorComboBox(_NativeComboBox):
    pass
