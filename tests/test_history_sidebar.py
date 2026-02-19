import types
import unittest
from unittest.mock import Mock

try:
    from gui.tkinter.history_sidebar import HistorySidebar
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Tk frontend module not available") from exc


class _FakeScrollbar:
    def __init__(self) -> None:
        self._mapped = False
        self.calls: list[tuple[str, tuple]] = []

    def set(self, first: str, last: str) -> None:
        self.calls.append(("set", (first, last)))

    def winfo_ismapped(self) -> bool:
        return self._mapped

    def grid(self) -> None:
        self.calls.append(("grid", ()))
        self._mapped = True

    def grid_remove(self) -> None:
        self.calls.append(("grid_remove", ()))
        self._mapped = False


class _FailingCanvas:
    def yview_scroll(self, _units: int, _mode: str) -> None:
        raise RuntimeError("scroll failed")


class TestHistorySidebarScrolling(unittest.TestCase):
    def test_autohide_scrollbar_hides_when_not_needed(self) -> None:
        sidebar = object.__new__(HistorySidebar)
        sidebar._scrollbar = _FakeScrollbar()
        sidebar._scrollbar._mapped = True

        sidebar._autohide_list_scrollbar("0.0", "1.0")

        self.assertFalse(sidebar._scrollbar.winfo_ismapped())
        self.assertIn(("grid_remove", ()), sidebar._scrollbar.calls)

    def test_autohide_scrollbar_shows_when_needed(self) -> None:
        sidebar = object.__new__(HistorySidebar)
        sidebar._scrollbar = _FakeScrollbar()

        sidebar._autohide_list_scrollbar("0.1", "0.8")

        self.assertTrue(sidebar._scrollbar.winfo_ismapped())
        self.assertIn(("grid", ()), sidebar._scrollbar.calls)

    def test_on_mousewheel_scrolls_canvas_from_delta(self) -> None:
        sidebar = object.__new__(HistorySidebar)
        sidebar.list_canvas = types.SimpleNamespace(yview_scroll=Mock())

        result = sidebar._on_mousewheel(types.SimpleNamespace(delta=120))

        self.assertEqual(result, "break")
        sidebar.list_canvas.yview_scroll.assert_called_once_with(-1, "units")

    def test_on_mousewheel_scrolls_canvas_from_button_events(self) -> None:
        sidebar = object.__new__(HistorySidebar)
        sidebar.list_canvas = types.SimpleNamespace(yview_scroll=Mock())

        sidebar._on_mousewheel(types.SimpleNamespace(num=5, delta=0))

        sidebar.list_canvas.yview_scroll.assert_called_once_with(1, "units")

    def test_on_mousewheel_ignores_canvas_scroll_errors(self) -> None:
        sidebar = object.__new__(HistorySidebar)
        sidebar.list_canvas = _FailingCanvas()

        result = sidebar._on_mousewheel(types.SimpleNamespace(delta=120))

        self.assertEqual(result, "break")


if __name__ == "__main__":
    unittest.main()
