import unittest

from gui.queue_sidebar import QueueSidebar


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


class _FailingScrollbar(_FakeScrollbar):
    def set(self, first: str, last: str) -> None:
        super().set(first, last)
        raise RuntimeError("set failed")


class TestQueueSidebarScrolling(unittest.TestCase):
    def test_autohide_scrollbar_hides_when_not_needed(self) -> None:
        sidebar = object.__new__(QueueSidebar)
        sidebar._scrollbar = _FakeScrollbar()
        sidebar._scrollbar._mapped = True

        sidebar._autohide_list_scrollbar("0.0", "1.0")

        self.assertFalse(sidebar._scrollbar.winfo_ismapped())
        self.assertIn(("grid_remove", ()), sidebar._scrollbar.calls)

    def test_autohide_scrollbar_shows_when_needed(self) -> None:
        sidebar = object.__new__(QueueSidebar)
        sidebar._scrollbar = _FakeScrollbar()

        sidebar._autohide_list_scrollbar("0.1", "0.8")

        self.assertTrue(sidebar._scrollbar.winfo_ismapped())
        self.assertIn(("grid", ()), sidebar._scrollbar.calls)

    def test_autohide_scrollbar_ignores_scrollbar_set_failure(self) -> None:
        sidebar = object.__new__(QueueSidebar)
        sidebar._scrollbar = _FailingScrollbar()
        sidebar._autohide_list_scrollbar("0.1", "0.8")
        self.assertFalse(sidebar._scrollbar.winfo_ismapped())


if __name__ == "__main__":
    unittest.main()
