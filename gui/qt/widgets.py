from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
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


QUEUE_SOURCE_INDEX_ROLE = Qt.ItemDataRole.UserRole
QUEUE_TITLE_ROLE = Qt.ItemDataRole.UserRole + 1
QUEUE_META_ROLE = Qt.ItemDataRole.UserRole + 2


@dataclass(frozen=True)
class NativeComboBoxConfig:
    minimum_width: int
    items: tuple[tuple[str, object], ...] = ()
    hint_text: str = ""
    maximum_width: int | None = None
    fixed_height: int = 45


@dataclass(frozen=True)
class SourceToastRefs:
    card: QFrame
    title_label: QLabel
    message_label: QLabel
    dismiss_button: QPushButton


@dataclass(frozen=True)
class ButtonSpec:
    text: str
    object_name: str | None = None
    on_click: Callable[[], None] | None = None
    on_toggled: Callable[[bool], None] | None = None
    checkable: bool = False
    auto_exclusive: bool = False
    tooltip: str = ""
    size_policy: tuple[QSizePolicy.Policy, QSizePolicy.Policy] | None = None
    minimum_width: int | None = None
    maximum_width: int | None = None
    fixed_width: int | None = None
    minimum_height: int | None = None
    maximum_height: int | None = None
    fixed_height: int | None = None
    focus_policy: Qt.FocusPolicy | None = None
    cursor: Qt.CursorShape | None = None
    stretch: int = 0


@dataclass(frozen=True)
class SegmentedRailSpec:
    object_name: str
    button_specs: Sequence[ButtonSpec]
    selection_frame_object_name: str = "topNavSelection"
    selection_rect_getter: Callable[[QAbstractButton], QRect] | None = None
    size_policy: tuple[QSizePolicy.Policy, QSizePolicy.Policy] = (
        QSizePolicy.Policy.Fixed,
        QSizePolicy.Policy.Fixed,
    )
    layout_margins: tuple[int, int, int, int] = (0, 0, 0, 0)
    layout_spacing: int = 0
    trailing_stretch: bool = False


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


class StableSizeHintButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._stable_width: int | None = None

    def stable_width(self) -> int | None:
        return self._stable_width

    def set_stable_width(self, width: int | None) -> None:
        self._stable_width = None if width is None else max(0, int(width))
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        if self._stable_width is not None:
            hint.setWidth(self._stable_width)
        return hint

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        if self._stable_width is not None:
            hint.setWidth(self._stable_width)
        return hint


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


def _apply_widget_size(
    widget: QWidget,
    *,
    size_policy: tuple[QSizePolicy.Policy, QSizePolicy.Policy] | None = None,
    minimum_width: int | None = None,
    maximum_width: int | None = None,
    fixed_width: int | None = None,
    minimum_height: int | None = None,
    maximum_height: int | None = None,
    fixed_height: int | None = None,
) -> None:
    if size_policy is not None:
        widget.setSizePolicy(*size_policy)

    if fixed_width is not None:
        widget.setFixedWidth(fixed_width)
    else:
        if minimum_width is not None:
            widget.setMinimumWidth(minimum_width)
        if maximum_width is not None:
            widget.setMaximumWidth(maximum_width)

    if fixed_height is not None:
        widget.setFixedHeight(fixed_height)
    else:
        if minimum_height is not None:
            widget.setMinimumHeight(minimum_height)
        if maximum_height is not None:
            widget.setMaximumHeight(maximum_height)


def build_button(parent: QWidget, *, spec: ButtonSpec) -> QPushButton:
    button = StableSizeHintButton(spec.text, parent)
    if spec.object_name:
        button.setObjectName(spec.object_name)
    button.setCheckable(spec.checkable)
    if spec.auto_exclusive:
        button.setAutoExclusive(True)
    if spec.tooltip:
        button.setToolTip(spec.tooltip)
    if spec.focus_policy is not None:
        button.setFocusPolicy(spec.focus_policy)
    if spec.cursor is not None:
        button.setCursor(spec.cursor)
    _apply_widget_size(
        button,
        size_policy=spec.size_policy,
        minimum_width=spec.minimum_width,
        maximum_width=spec.maximum_width,
        fixed_width=spec.fixed_width,
        minimum_height=spec.minimum_height,
        maximum_height=spec.maximum_height,
        fixed_height=spec.fixed_height,
    )
    if spec.on_click is not None:
        button.clicked.connect(spec.on_click)
    if spec.on_toggled is not None:
        button.toggled.connect(spec.on_toggled)
    return button


def build_segmented_rail(
    parent: QWidget,
    *,
    spec: SegmentedRailSpec,
) -> tuple[AnimatedSegmentedRail, tuple[QPushButton, ...]]:
    rail = AnimatedSegmentedRail(
        parent,
        selection_frame_object_name=spec.selection_frame_object_name,
        selection_rect_getter=spec.selection_rect_getter,
    )
    rail.setObjectName(spec.object_name)
    _apply_widget_size(rail, size_policy=spec.size_policy)

    layout = rail.layout()
    if isinstance(layout, QHBoxLayout):
        left, top, right, bottom = spec.layout_margins
        layout.setContentsMargins(left, top, right, bottom)
        layout.setSpacing(spec.layout_spacing)

    buttons: list[QPushButton] = []
    for button_spec in spec.button_specs:
        button = build_button(rail, spec=button_spec)
        rail.add_button(button, stretch=button_spec.stretch)
        buttons.append(button)

    if spec.trailing_stretch and isinstance(layout, QHBoxLayout):
        layout.addStretch(1)

    return rail, tuple(buttons)


class _QueueItemDelegate(QStyledItemDelegate):
    edit_requested = Signal(int)
    remove_requested = Signal(int)

    _ITEM_HEIGHT = 58
    _TEXT_MARGIN = 12
    _ITEM_PADDING = 7
    _REMOVE_MARGIN = 10
    _REMOVE_GAP = 10
    _EDIT_GAP = 8
    _EDIT_WIDTH = 54
    _EDIT_HEIGHT = 24
    _REMOVE_SIZE = 22
    _REMOVE_BG = QColor("#322523")
    _REMOVE_BORDER = QColor("#6e4741")
    _REMOVE_TEXT = QColor("#f2d6cf")
    _EDIT_BG = QColor("#223a34")
    _EDIT_BORDER = QColor("#347c66")
    _EDIT_TEXT = QColor("#86d7b7")

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        if size.height() < self._ITEM_HEIGHT:
            size.setHeight(self._ITEM_HEIGHT)
        return size

    def remove_button_rect(self, rect: QRect) -> QRect:
        x = rect.x() + rect.width() - self._REMOVE_MARGIN - self._REMOVE_SIZE
        y = rect.y() + max(0, (rect.height() - self._REMOVE_SIZE) // 2)
        return QRect(x, y, self._REMOVE_SIZE, self._REMOVE_SIZE)

    def edit_button_rect(self, rect: QRect) -> QRect:
        remove_rect = self.remove_button_rect(rect)
        x = remove_rect.left() - self._EDIT_GAP - self._EDIT_WIDTH
        y = rect.y() + max(0, (rect.height() - self._EDIT_HEIGHT) // 2)
        return QRect(x, y, self._EDIT_WIDTH, self._EDIT_HEIGHT)

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
        title_text = str(index.data(QUEUE_TITLE_ROLE) or view_option.text or "")
        meta_text = str(index.data(QUEUE_META_ROLE) or "")
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
        text_rect.adjust(
            self._TEXT_MARGIN,
            self._ITEM_PADDING,
            -self._TEXT_MARGIN,
            -self._ITEM_PADDING,
        )
        if editable:
            edit_rect = self.edit_button_rect(view_option.rect)
            text_rect.setRight(edit_rect.left() - self._REMOVE_GAP)
        if text_rect.width() > 0:
            title_color = (
                view_option.palette.highlightedText().color()
                if view_option.state & QStyle.StateFlag.State_Selected
                else view_option.palette.text().color()
            )
            meta_color = QColor(title_color)
            meta_color.setAlpha(
                188 if view_option.state & QStyle.StateFlag.State_Selected else 168
            )

            title_font = painter.font()
            title_font.setBold(True)
            meta_font = painter.font()
            meta_font.setPointSize(max(10, meta_font.pointSize() - 1))

            title_rect = QRect(text_rect)
            title_rect.setHeight(max(0, int(text_rect.height() * 0.55)))
            meta_rect = QRect(text_rect)
            meta_rect.setTop(title_rect.bottom() - 1)

            painter.save()
            painter.setFont(title_font)
            painter.setPen(title_color)
            shown_title = painter.fontMetrics().elidedText(
                title_text,
                Qt.TextElideMode.ElideRight,
                title_rect.width(),
            )
            painter.drawText(
                title_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                shown_title,
            )
            if meta_text:
                painter.setFont(meta_font)
                painter.setPen(meta_color)
                shown_meta = painter.fontMetrics().elidedText(
                    meta_text,
                    Qt.TextElideMode.ElideRight,
                    meta_rect.width(),
                )
                painter.drawText(
                    meta_rect,
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    shown_meta,
                )
            painter.restore()

        if editable:
            edit_rect = self.edit_button_rect(view_option.rect)
            remove_rect = self.remove_button_rect(view_option.rect)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(self._EDIT_BORDER))
            painter.setBrush(self._EDIT_BG)
            painter.drawRoundedRect(edit_rect.adjusted(0, 0, -1, -1), 12, 12)
            painter.setPen(self._EDIT_TEXT)
            painter.drawText(
                edit_rect,
                int(Qt.AlignmentFlag.AlignCenter),
                "Edit",
            )
            remove_frame = QRectF(remove_rect).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(self._REMOVE_BORDER))
            painter.setBrush(self._REMOVE_BG)
            painter.drawEllipse(remove_frame)
            icon_pen = QPen(self._REMOVE_TEXT, 1.8)
            icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(icon_pen)
            icon_bounds = remove_frame.adjusted(5.4, 5.4, -5.4, -5.4)
            painter.drawLine(icon_bounds.topLeft(), icon_bounds.bottomRight())
            painter.drawLine(icon_bounds.bottomLeft(), icon_bounds.topRight())
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
            if self.edit_button_rect(option.rect).contains(pos):
                if event.type() == QEvent.Type.MouseButtonRelease:
                    self.edit_requested.emit(index.row())
                return True
            if self.remove_button_rect(option.rect).contains(pos):
                if event.type() == QEvent.Type.MouseButtonRelease:
                    self.remove_requested.emit(index.row())
                return True
        return super().editorEvent(event, model, option, index)


class QueueListWidget(QListWidget):
    _DRAG_EDGE_AUTOSCROLL_MARGIN = 56

    edit_requested = Signal(int)
    remove_requested = Signal(int)
    items_reordered = Signal(list)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._queue_editable = True
        self._delegate = _QueueItemDelegate(self)
        self.setItemDelegate(self._delegate)
        self._delegate.edit_requested.connect(self._emit_edit_requested)
        self._delegate.remove_requested.connect(self._emit_remove_requested)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAutoScroll(True)
        self.setAutoScrollMargin(self._DRAG_EDGE_AUTOSCROLL_MARGIN)
        self.set_queue_editable(True)

    def _emit_edit_requested(self, row: int) -> None:
        self.edit_requested.emit(int(row))

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

    def edit_button_rect(self, row: int) -> QRect:
        item = self.item(int(row))
        if item is None:
            return QRect()
        return self._delegate.edit_button_rect(self.visualItemRect(item))

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

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", str(tone or "default"))
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        for child in self.findChildren(QWidget):
            child_style = child.style()
            child_style.unpolish(child)
            child_style.polish(child)
            child.update()
        self.update()

    def set_progress_percent(self, percent: float | None) -> None:
        visible = percent is not None
        self._progress_bar.setVisible(visible)
        if not visible:
            return
        clamped = max(0.0, min(100.0, float(percent)))
        self._progress_bar.setValue(int(round(clamped * 10)))


class QueueEmptyStateWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(10)
        root_layout.addStretch(1)

        placeholder_card = QFrame(self)
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
        root_layout.addWidget(
            placeholder_card,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        root_layout.addStretch(1)


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
        QListView#nativeComboView::item:disabled {{
            background: transparent;
            color: #7a7a73;
        }}
        QListView#nativeComboView::item:disabled:hover {{
            background: transparent;
            color: #7a7a73;
        }}
        QListView#nativeComboView::item:disabled:selected {{
            background: #30302c;
            color: #7a7a73;
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

    def set_item_enabled(
        self,
        value: object,
        enabled: bool,
        *,
        disabled_tooltip: str = "",
    ) -> None:
        index = self.findData(value)
        if index < 0:
            return
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            return
        item = model.item(index)
        if item is None:
            return
        item.setEnabled(enabled)
        item.setToolTip("" if enabled else disabled_tooltip)
        self.view().update()


def build_native_combo(
    parent: QWidget,
    *,
    register_native_combo: Callable[[_NativeComboBox], None],
    config: NativeComboBoxConfig,
) -> _NativeComboBox:
    combo = _NativeComboBox(parent)
    register_native_combo(combo)
    _apply_widget_size(
        combo,
        minimum_width=config.minimum_width,
        maximum_width=config.maximum_width,
        fixed_height=config.fixed_height,
    )
    if config.hint_text:
        combo.setPlaceholderText(config.hint_text)
    for label, value in config.items:
        combo.addItem(label, value)
    return combo


def build_source_feedback_toast(parent: QWidget) -> SourceToastRefs:
    source_toast = QFrame(parent)
    source_toast.setObjectName("sourceToastCard")
    source_toast.setProperty("tone", "success")
    source_toast.setMinimumWidth(260)
    source_toast.setMaximumWidth(340)

    shadow = QGraphicsDropShadowEffect(source_toast)
    shadow.setBlurRadius(28)
    shadow.setOffset(0, 10)
    shadow.setColor(QColor(15, 33, 45, 48))
    source_toast.setGraphicsEffect(shadow)

    source_toast_layout = QVBoxLayout(source_toast)
    source_toast_layout.setContentsMargins(16, 12, 16, 14)
    source_toast_layout.setSpacing(4)

    header = QWidget(source_toast)
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(8)

    title_label = QLabel("Formats ready", header)
    title_label.setObjectName("sourceToastTitle")

    dismiss_button = build_button(
        header,
        spec=ButtonSpec(
            text="×",
            object_name="sourceToastDismissButton",
            tooltip="Dismiss notification",
            fixed_width=24,
            fixed_height=24,
            focus_policy=Qt.FocusPolicy.NoFocus,
            cursor=Qt.CursorShape.PointingHandCursor,
        ),
    )

    message_label = QLabel("", source_toast)
    message_label.setObjectName("sourceToastMessage")
    message_label.setWordWrap(True)

    header_layout.addWidget(title_label)
    header_layout.addStretch(1)
    header_layout.addWidget(dismiss_button)
    source_toast_layout.addWidget(header)
    source_toast_layout.addWidget(message_label)
    source_toast.hide()

    return SourceToastRefs(
        card=source_toast,
        title_label=title_label,
        message_label=message_label,
        dismiss_button=dismiss_button,
    )
