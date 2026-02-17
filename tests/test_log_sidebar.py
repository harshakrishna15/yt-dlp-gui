import queue
import unittest
from unittest.mock import Mock, patch

from gui.log_sidebar import LogSidebar, POLL_MS


class _FakeRoot:
    def __init__(self) -> None:
        self.calls: list[tuple[int, object]] = []

    def after(self, delay: int, callback: object) -> str:
        self.calls.append((delay, callback))
        return "after-id"


class _FakeText:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.state = "disabled"

    def configure(self, **kwargs) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]

    def insert(self, _pos: str, text: str) -> None:
        incoming = text.split("\n")
        if incoming and incoming[-1] == "":
            incoming = incoming[:-1]
        self.lines.extend(incoming)

    def index(self, _spec: str) -> str:
        line_count = max(1, len(self.lines))
        return f"{line_count}.0"

    def delete(self, _start: str, end: str) -> None:
        # end is expected like "<line>.0"; remove up to line-1.
        line_s = end.split(".", 1)[0]
        line_i = int(line_s)
        delete_count = max(0, line_i - 1)
        self.lines = self.lines[delete_count:]

    def see(self, _pos: str) -> None:
        return None


class TestLogSidebarPolling(unittest.TestCase):
    def test_poll_queue_limits_batch_and_reschedules_immediately_for_backlog(self) -> None:
        sidebar = object.__new__(LogSidebar)
        sidebar._shutdown = False
        sidebar._queue = queue.Queue()
        sidebar._queue.put("a")
        sidebar._queue.put("b")
        sidebar._queue.put("c")
        sidebar._append_batch = Mock()
        sidebar.root = _FakeRoot()
        sidebar._poll_after_id = None

        with patch("gui.log_sidebar.LOG_BATCH_MAX", 2):
            sidebar._poll_queue()

        sidebar._append_batch.assert_called_once_with(["a", "b"])
        self.assertEqual(sidebar._queue.qsize(), 1)
        self.assertEqual(sidebar.root.calls[-1][0], 0)
        self.assertEqual(sidebar._poll_after_id, "after-id")

    def test_poll_queue_uses_default_interval_when_empty(self) -> None:
        sidebar = object.__new__(LogSidebar)
        sidebar._shutdown = False
        sidebar._queue = queue.Queue()
        sidebar._append_batch = Mock()
        sidebar.root = _FakeRoot()
        sidebar._poll_after_id = None

        sidebar._poll_queue()

        sidebar._append_batch.assert_not_called()
        self.assertEqual(sidebar.root.calls[-1][0], POLL_MS)


class TestLogSidebarAppend(unittest.TestCase):
    def test_append_delegates_to_batch(self) -> None:
        sidebar = object.__new__(LogSidebar)
        sidebar._append_batch = Mock()
        sidebar._append("hello")
        sidebar._append_batch.assert_called_once_with(["hello"])

    def test_append_batch_trims_old_lines(self) -> None:
        sidebar = object.__new__(LogSidebar)
        sidebar._log_sidebar_open = True
        sidebar._set_unread = Mock()
        sidebar.text = _FakeText()

        with patch("gui.log_sidebar.LOG_MAX_LINES", 3):
            sidebar._append_batch(["l1", "l2", "l3", "l4"])

        self.assertEqual(sidebar.text.lines, ["l2", "l3", "l4"])
        sidebar._set_unread.assert_not_called()

    def test_append_batch_sets_unread_when_closed(self) -> None:
        sidebar = object.__new__(LogSidebar)
        sidebar._log_sidebar_open = False
        sidebar._set_unread = Mock()
        sidebar.text = _FakeText()

        with patch("gui.log_sidebar.LOG_MAX_LINES", 10):
            sidebar._append_batch(["x", "y"])

        sidebar._set_unread.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
