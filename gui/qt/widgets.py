from __future__ import annotations

from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
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
    record_output = Signal(str, str, object)


QUEUE_SOURCE_INDEX_ROLE = Qt.ItemDataRole.UserRole


class StableStackedWidget(QStackedWidget):
    def sizeHint(self) -> QSize:
        return self._largest_hint(super().sizeHint(), minimum=False)

    def minimumSizeHint(self) -> QSize:
        return self._largest_hint(super().minimumSizeHint(), minimum=True)

    def _largest_hint(self, fallback: QSize, *, minimum: bool) -> QSize:
        width = max(0, fallback.width())
        height = max(0, fallback.height())
        for index in range(self.count()):
            widget = self.widget(index)
            if widget is None:
                continue
            hint = widget.minimumSizeHint() if minimum else widget.sizeHint()
            width = max(width, hint.width())
            height = max(height, hint.height())
        return QSize(width, height)


class AnimatedSegmentedRail(QWidget):
    _ANIMATION_MS = 220

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        selection_frame_object_name: str = "topNavSelection",
        selection_rect_getter: Callable[[QAbstractButton], QRect] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._buttons: list[QAbstractButton] = []
        self._selected_button: QAbstractButton | None = None
        self._selection_anim: QPropertyAnimation | None = None
        self._sync_queued = False
        self._selection_rect_getter = selection_rect_getter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._selection_frame = QFrame(self)
        self._selection_frame.setObjectName(selection_frame_object_name)
        self._selection_frame.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._selection_frame.hide()

    def add_button(self, button: QAbstractButton, *, stretch: int = 0) -> None:
        if button in self._buttons:
            return
        button.setParent(self)
        self._buttons.append(button)
        layout = self.layout()
        if isinstance(layout, QHBoxLayout):
            layout.addWidget(button, stretch=stretch)
        button.installEventFilter(self)
        button.toggled.connect(self._queue_selection_sync)
        button.raise_()

    def sync_selection(self, *, animate: bool = True) -> None:
        target = self._visible_checked_button()
        if target is None:
            self._stop_selection_animation()
            self._selected_button = None
            self._selection_frame.hide()
            return

        target_rect = self._selection_target_rect(target)
        if target_rect.width() <= 0 or target_rect.height() <= 0:
            self._selection_frame.hide()
            return

        self._selection_frame.lower()
        for button in self._buttons:
            button.raise_()

        if self._selected_button is None or not self._selection_frame.isVisible():
            self._stop_selection_animation()
            self._selection_frame.setGeometry(target_rect)
            self._selection_frame.show()
            self._selected_button = target
            return

        previous = self._selected_button
        active_animation = self._selection_anim
        self._selected_button = target
        if previous is target:
            if active_animation is not None and animate:
                end_rect = active_animation.endValue()
                if isinstance(end_rect, QRect) and end_rect == target_rect:
                    self._selection_frame.show()
                    return
            if not animate or not self.isVisible():
                self._stop_selection_animation()
                self._selection_frame.setGeometry(target_rect)
                self._selection_frame.show()
                return
        elif not animate or not self.isVisible():
            self._stop_selection_animation()
            self._selection_frame.setGeometry(target_rect)
            self._selection_frame.show()
            return

        start_rect = self._selection_frame.geometry()
        if start_rect == target_rect:
            self._selection_frame.show()
            return

        self._stop_selection_animation()
        self._selection_anim = QPropertyAnimation(self._selection_frame, b"geometry", self)
        self._selection_anim.setDuration(self._ANIMATION_MS)
        self._selection_anim.setStartValue(start_rect)
        self._selection_anim.setEndValue(target_rect)
        self._selection_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._selection_anim.finished.connect(self._clear_selection_animation)
        self._selection_frame.show()
        self._selection_anim.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._buttons and event.type() in {
            QEvent.Type.Hide,
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
        }:
            self.sync_selection(animate=self._selection_anim is not None or self._sync_queued)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.sync_selection(animate=self._selection_anim is not None or self._sync_queued)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_without_animation)

    def _visible_checked_button(self) -> QAbstractButton | None:
        for button in self._buttons:
            if button.isVisible() and button.isChecked():
                return button
        return None

    def _selection_target_rect(self, button: QAbstractButton) -> QRect:
        if self._selection_rect_getter is not None:
            return self._selection_rect_getter(button)
        return button.geometry()

    def _queue_selection_sync(self, _checked: bool = False) -> None:
        if self._sync_queued:
            return
        self._sync_queued = True
        QTimer.singleShot(0, self._run_queued_selection_sync)

    def _run_queued_selection_sync(self) -> None:
        self._sync_queued = False
        self.sync_selection()

    def _sync_without_animation(self) -> None:
        self.sync_selection(animate=False)

    def _stop_selection_animation(self) -> None:
        if self._selection_anim is None:
            return
        self._selection_anim.stop()
        self._selection_anim.deleteLater()
        self._selection_anim = None

    def _clear_selection_animation(self) -> None:
        animation = self.sender()
        if isinstance(animation, QPropertyAnimation):
            animation.deleteLater()
        self._selection_anim = None


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


class RecentDownloadRowWidget(QFrame):
    again_requested = Signal(int)

    def __init__(
        self,
        *,
        history_index: int,
        badge_text: str,
        title: str,
        meta: str,
        can_requeue: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history_index = int(history_index)
        self.setObjectName("recentDownloadCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        badge_label = QLabel(str(badge_text or "VID"), self)
        badge_label.setObjectName("recentDownloadBadge")
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setFixedSize(48, 48)
        layout.addWidget(badge_label, alignment=Qt.AlignmentFlag.AlignTop)

        copy_col = QWidget(self)
        copy_col.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        copy_col_layout = QVBoxLayout(copy_col)
        copy_col_layout.setContentsMargins(0, 0, 0, 0)
        copy_col_layout.setSpacing(3)

        title_label = QLabel(str(title or "Downloaded item"), copy_col)
        title_label.setObjectName("recentDownloadTitle")
        title_label.setWordWrap(True)
        meta_label = QLabel(str(meta or ""), copy_col)
        meta_label.setObjectName("recentDownloadMeta")
        meta_label.setWordWrap(True)
        meta_label.setVisible(bool(str(meta or "").strip()))
        copy_col_layout.addWidget(title_label)
        copy_col_layout.addWidget(meta_label)
        layout.addWidget(copy_col, stretch=1)

        again_button = QPushButton("↓ Again", self)
        again_button.setObjectName("historyAgainButton")
        again_button.setEnabled(bool(can_requeue))
        again_button.clicked.connect(self._emit_again_requested)
        layout.addWidget(again_button, alignment=Qt.AlignmentFlag.AlignVCenter)

    def _emit_again_requested(self) -> None:
        self.again_requested.emit(self._history_index)


class QueueEmptyStateWidget(QWidget):
    again_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        root_layout.addWidget(self._stack, stretch=1)

        placeholder_page = QWidget(self._stack)
        placeholder_layout = QVBoxLayout(placeholder_page)
        placeholder_layout.setContentsMargins(24, 24, 24, 24)
        placeholder_layout.setSpacing(10)
        placeholder_layout.addStretch(1)

        placeholder_card = QFrame(placeholder_page)
        placeholder_card.setObjectName("queueEmptyPlaceholder")
        placeholder_card.setMaximumWidth(360)
        placeholder_card.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        placeholder_card_layout = QVBoxLayout(placeholder_card)
        placeholder_card_layout.setContentsMargins(24, 24, 24, 24)
        placeholder_card_layout.setSpacing(8)

        self.placeholder_icon = QLabel("↓", placeholder_card)
        self.placeholder_icon.setObjectName("queueEmptyIcon")
        self.placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_icon.setFixedSize(64, 64)
        self.placeholder_title = QLabel("Queue is empty", placeholder_card)
        self.placeholder_title.setObjectName("queueEmptyTitle")
        self.placeholder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_description = QLabel(
            "Paste a URL above to get started",
            placeholder_card,
        )
        self.placeholder_description.setObjectName("queueEmptyDescription")
        self.placeholder_description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder_card_layout.addWidget(
            self.placeholder_icon,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        placeholder_card_layout.addWidget(self.placeholder_title)
        placeholder_card_layout.addWidget(self.placeholder_description)
        placeholder_layout.addWidget(
            placeholder_card,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        placeholder_layout.addStretch(1)
        self._placeholder_index = self._stack.addWidget(placeholder_page)

        recent_page = QWidget(self._stack)
        recent_layout = QVBoxLayout(recent_page)
        recent_layout.setContentsMargins(0, 8, 0, 0)
        recent_layout.setSpacing(12)

        recent_title = QLabel("Recent downloads", recent_page)
        recent_title.setObjectName("recentDownloadsTitle")
        recent_layout.addWidget(recent_title)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(10)
        recent_layout.addLayout(self._rows_layout)
        recent_layout.addStretch(1)
        self._recent_index = self._stack.addWidget(recent_page)

    def set_recent_items(self, items: list[dict[str, object]]) -> None:
        while self._rows_layout.count():
            child = self._rows_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        if not items:
            self._stack.setCurrentIndex(self._placeholder_index)
            return
        for item in items:
            row = RecentDownloadRowWidget(
                history_index=int(item.get("history_index", -1)),
                badge_text=str(item.get("badge_text", "VID")),
                title=str(item.get("title", "Downloaded item")),
                meta=str(item.get("meta", "")),
                can_requeue=bool(item.get("can_requeue", False)),
                parent=self,
            )
            row.again_requested.connect(
                lambda history_index, signal=self.again_requested: signal.emit(history_index)
            )
            self._rows_layout.addWidget(row)
        self._stack.setCurrentIndex(self._recent_index)


def _style_combo_popup(combo: QComboBox, *, border_color: str = "#42423d") -> None:
    popup = combo.view().window()
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    popup.setAutoFillBackground(True)
    popup.setContentsMargins(0, 0, 0, 0)
    popup.setStyleSheet(
        f"""
        QWidget {{
            background: #111210;
            border: none;
            border-radius: 24px;
        }}
        QListView#nativeComboView {{
            background: #272724;
            border: 1px solid {border_color};
            border-radius: 20px;
            padding: 6px;
            outline: 0;
            margin: 0px;
        }}
        QListView#nativeComboView::item {{
            background: transparent;
            min-height: 30px;
            padding: 7px 12px;
            border-radius: 12px;
            color: #f2ede5;
            font-weight: 600;
        }}
        QListView#nativeComboView::item:hover {{
            background: #30302c;
            color: #f1eee7;
        }}
        QListView#nativeComboView::item:selected {{
            background: #314d45;
            color: #86d7b7;
        }}
        QListView#nativeComboView QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px 0px 2px 0px;
            border: none;
        }}
        QListView#nativeComboView QScrollBar::handle:vertical {{
            background: #62625c;
            border-radius: 5px;
            min-height: 24px;
        }}
        QListView#nativeComboView QScrollBar::handle:vertical:hover {{
            background: #7d7d75;
        }}
        QListView#nativeComboView QScrollBar::sub-line:vertical,
        QListView#nativeComboView QScrollBar::add-line:vertical,
        QListView#nativeComboView QScrollBar::up-arrow:vertical,
        QListView#nativeComboView QScrollBar::down-arrow:vertical {{
            height: 0px;
            width: 0px;
        }}
        QListView#nativeComboView QScrollBar::add-page:vertical,
        QListView#nativeComboView QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
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
