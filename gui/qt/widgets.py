from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QSizePolicy,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)


class _QtSignals(QObject):
    formats_loaded = Signal(int, str, object, bool, bool)
    progress = Signal(object)
    log = Signal(str)
    download_done = Signal(str)
    queue_item_done = Signal(bool, bool)
    record_output = Signal(str, str)


QUEUE_SOURCE_INDEX_ROLE = Qt.ItemDataRole.UserRole


class _QueueItemDelegate(QStyledItemDelegate):
    remove_requested = Signal(int)

    _ITEM_HEIGHT = 40
    _TEXT_MARGIN = 12
    _REMOVE_MARGIN = 10
    _REMOVE_GAP = 10
    _REMOVE_SIZE = 22
    _REMOVE_BG = QColor("#ffffff")
    _REMOVE_BORDER = QColor("#cad6e1")
    _REMOVE_TEXT = QColor("#5d7082")

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        if size.height() < self._ITEM_HEIGHT:
            size.setHeight(self._ITEM_HEIGHT)
        return size

    def remove_button_rect(self, rect: QRect) -> QRect:
        x = rect.x() + rect.width() - self._REMOVE_MARGIN - self._REMOVE_SIZE
        y = rect.y() + max(0, (rect.height() - self._REMOVE_SIZE) // 2)
        return QRect(x, y, self._REMOVE_SIZE, self._REMOVE_SIZE)

    def _queue_editable(self, widget: object) -> bool:
        checker = getattr(widget, "queue_editable", None)
        if callable(checker):
            return bool(checker())
        parent_getter = getattr(widget, "parentWidget", None)
        if callable(parent_getter):
            parent = parent_getter()
            checker = getattr(parent, "queue_editable", None)
            if callable(checker):
                return bool(checker())
        return True

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        text = str(view_option.text or "")
        view_option.text = ""
        style = (
            view_option.widget.style()
            if view_option.widget is not None
            else QApplication.style()
        )
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            view_option.widget,
        )

        editable = self._queue_editable(view_option.widget)
        text_rect = QRect(view_option.rect)
        text_rect.adjust(self._TEXT_MARGIN, 0, -self._TEXT_MARGIN, 0)
        if editable:
            remove_rect = self.remove_button_rect(view_option.rect)
            text_rect.setRight(remove_rect.left() - self._REMOVE_GAP)
        if text_rect.width() > 0:
            shown_text = view_option.fontMetrics.elidedText(
                text,
                Qt.TextElideMode.ElideMiddle,
                text_rect.width(),
            )
            text_color = (
                view_option.palette.highlightedText().color()
                if view_option.state & QStyle.StateFlag.State_Selected
                else view_option.palette.text().color()
            )
            painter.save()
            painter.setPen(text_color)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                shown_text,
            )
            painter.restore()

        if editable:
            remove_rect = self.remove_button_rect(view_option.rect)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(self._REMOVE_BORDER))
            painter.setBrush(self._REMOVE_BG)
            painter.drawRoundedRect(remove_rect.adjusted(0, 0, -1, -1), 8, 8)
            painter.setPen(self._REMOVE_TEXT)
            painter.drawText(
                remove_rect,
                int(Qt.AlignmentFlag.AlignCenter),
                "X",
            )
            painter.restore()

    def editorEvent(self, event, model, option: QStyleOptionViewItem, index) -> bool:
        if (
            self._queue_editable(option.widget)
            and event.type()
            in {
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
            }
            and hasattr(event, "position")
            and event.button() == Qt.MouseButton.LeftButton
        ):
            pos = event.position().toPoint()
            if self.remove_button_rect(option.rect).contains(pos):
                if event.type() == QEvent.Type.MouseButtonRelease:
                    self.remove_requested.emit(index.row())
                return True
        return super().editorEvent(event, model, option, index)


class QueueListWidget(QListWidget):
    remove_requested = Signal(int)
    items_reordered = Signal(list)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._queue_editable = True
        self._delegate = _QueueItemDelegate(self)
        self.setItemDelegate(self._delegate)
        self._delegate.remove_requested.connect(self._emit_remove_requested)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.set_queue_editable(True)

    def _emit_remove_requested(self, row: int) -> None:
        self.remove_requested.emit(int(row))

    def queue_editable(self) -> bool:
        return self._queue_editable

    def set_queue_editable(self, editable: bool) -> None:
        self._queue_editable = bool(editable)
        drag_drop_mode = (
            QAbstractItemView.DragDropMode.InternalMove
            if self._queue_editable
            else QAbstractItemView.DragDropMode.NoDragDrop
        )
        self.setDragEnabled(self._queue_editable)
        self.setAcceptDrops(self._queue_editable)
        self.viewport().setAcceptDrops(self._queue_editable)
        self.setDropIndicatorShown(self._queue_editable)
        self.setDragDropMode(drag_drop_mode)
        self.viewport().update()

    def remove_button_rect(self, row: int) -> QRect:
        item = self.item(int(row))
        if item is None:
            return QRect()
        return self._delegate.remove_button_rect(self.visualItemRect(item))

    def item_order(self) -> list[int]:
        order: list[int] = []
        for row in range(self.count()):
            item = self.item(row)
            value = item.data(QUEUE_SOURCE_INDEX_ROLE) if item is not None else row
            try:
                order.append(int(value))
            except (TypeError, ValueError):
                order.append(row)
        return order

    def dropEvent(self, event) -> None:
        before = self.item_order()
        super().dropEvent(event)
        after = self.item_order()
        if after != before:
            self.items_reordered.emit(after)


class WorkspaceSummaryWidget(QFrame):
    def __init__(
        self,
        *,
        badge_text: str,
        title: str,
        meta: str,
        status_text: str = "",
        progress_percent: float | None = None,
        tone: str = "default",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspaceSummaryCard")
        self.setProperty("tone", str(tone or "default"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_row = QWidget(self)
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(12)

        badge_label = QLabel(str(badge_text or "VID"), top_row)
        badge_label.setObjectName("workspaceSummaryBadge")
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setFixedSize(52, 52)

        copy_col = QWidget(top_row)
        copy_col.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        copy_col_layout = QVBoxLayout(copy_col)
        copy_col_layout.setContentsMargins(0, 0, 0, 0)
        copy_col_layout.setSpacing(3)

        title_label = QLabel(str(title or "-"), copy_col)
        title_label.setObjectName("workspaceSummaryTitle")
        title_label.setWordWrap(False)
        title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        meta_label = QLabel(str(meta or ""), copy_col)
        meta_label.setObjectName("workspaceSummaryMeta")
        meta_label.setWordWrap(False)
        meta_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        meta_label.setVisible(bool(str(meta or "").strip()))

        copy_col_layout.addWidget(title_label)
        copy_col_layout.addWidget(meta_label)

        top_row_layout.addWidget(
            badge_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )
        top_row_layout.addWidget(copy_col, stretch=1)

        self._status_label = QLabel(str(status_text or ""), top_row)
        self._status_label.setObjectName("workspaceSummaryStatus")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(bool(str(status_text or "").strip()))
        top_row_layout.addWidget(
            self._status_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setObjectName("workspaceSummaryProgress")
        self._progress_bar.setRange(0, 1000)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(progress_percent is not None)
        if progress_percent is not None:
            clamped = max(0.0, min(100.0, float(progress_percent)))
            self._progress_bar.setValue(int(round(clamped * 10)))

        layout.addWidget(top_row)
        layout.addWidget(self._progress_bar)

    def set_status_text(self, text: str) -> None:
        clean = str(text or "")
        self._status_label.setText(clean)
        self._status_label.setVisible(bool(clean.strip()))

    def set_progress_percent(self, percent: float | None) -> None:
        visible = percent is not None
        self._progress_bar.setVisible(visible)
        if not visible:
            return
        clamped = max(0.0, min(100.0, float(percent)))
        self._progress_bar.setValue(int(round(clamped * 10)))


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
