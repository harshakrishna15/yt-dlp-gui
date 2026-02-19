import types
import unittest
from unittest.mock import patch

try:
    from gui.tkinter.widgets import Tooltip
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Tk frontend module not available") from exc


class _FakeRoot:
    def __init__(self) -> None:
        self._seq = 0
        self.after_calls: list[tuple[str, int]] = []
        self.after_cancel_calls: list[str] = []
        self._callbacks: dict[str, object] = {}

    def after(self, delay_ms: int, callback):
        self._seq += 1
        after_id = f"after-{self._seq}"
        self.after_calls.append((after_id, delay_ms))
        self._callbacks[after_id] = callback
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self.after_cancel_calls.append(after_id)
        self._callbacks.pop(after_id, None)

    def run_after(self, after_id: str) -> None:
        callback = self._callbacks.pop(after_id, None)
        if callback is None:
            return
        callback()


class _FakeWidget:
    def __init__(self) -> None:
        self.bindings: dict[str, object] = {}

    def bind(self, event_name: str, callback, add: bool = False) -> None:
        self.bindings[event_name] = callback


class _FakeTopLevel:
    def __init__(self, _root) -> None:
        self.destroyed = False
        self.geometry_value = ""

    def wm_overrideredirect(self, _value: bool) -> None:
        return None

    def attributes(self, *_args) -> None:
        return None

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def destroy(self) -> None:
        self.destroyed = True


class _FakeLabel:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def pack(self) -> None:
        return None


class TestTooltip(unittest.TestCase):
    def test_auto_hide_then_motion_reschedules_tooltip(self) -> None:
        root = _FakeRoot()
        widget = _FakeWidget()
        with patch("gui.tkinter.widgets.tk.Toplevel", _FakeTopLevel), patch(
            "gui.tkinter.widgets.tk.Label", _FakeLabel
        ):
            tooltip = Tooltip(root, widget, "hello", delay_ms=10, visible_ms=15)
            tooltip._on_enter(types.SimpleNamespace(x_root=100, y_root=120))

            first_show_id = tooltip._after_id
            self.assertIsNotNone(first_show_id)
            root.run_after(str(first_show_id))

            self.assertIsNotNone(tooltip._tip)
            first_hide_id = tooltip._hide_after_id
            self.assertIsNotNone(first_hide_id)
            root.run_after(str(first_hide_id))

            self.assertIsNone(tooltip._tip)
            tooltip._on_motion(types.SimpleNamespace(x_root=102, y_root=124))
            second_show_id = tooltip._after_id
            self.assertIsNotNone(second_show_id)

            root.run_after(str(second_show_id))
            self.assertIsNotNone(tooltip._tip)

    def test_leave_cancels_pending_show_and_active_hide(self) -> None:
        root = _FakeRoot()
        widget = _FakeWidget()
        with patch("gui.tkinter.widgets.tk.Toplevel", _FakeTopLevel), patch(
            "gui.tkinter.widgets.tk.Label", _FakeLabel
        ):
            tooltip = Tooltip(root, widget, "hello", delay_ms=10, visible_ms=15)
            tooltip._on_enter(types.SimpleNamespace(x_root=50, y_root=60))
            pending_show_id = tooltip._after_id
            self.assertIsNotNone(pending_show_id)

            tooltip._on_leave(types.SimpleNamespace())
            self.assertIn(str(pending_show_id), root.after_cancel_calls)
            self.assertIsNone(tooltip._tip)

            tooltip._on_enter(types.SimpleNamespace(x_root=50, y_root=60))
            show_id = tooltip._after_id
            root.run_after(str(show_id))
            self.assertIsNotNone(tooltip._tip)
            active_hide_id = tooltip._hide_after_id
            self.assertIsNotNone(active_hide_id)

            tooltip._on_leave(types.SimpleNamespace())
            self.assertIn(str(active_hide_id), root.after_cancel_calls)
            self.assertIsNone(tooltip._tip)


if __name__ == "__main__":
    unittest.main()
