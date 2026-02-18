import unittest
from unittest.mock import patch

from gui import cli


class TestCliDispatch(unittest.TestCase):
    def test_main_defaults_to_tk_frontend(self) -> None:
        with patch("gui.cli._run_tk", return_value=0) as run_tk, patch(
            "gui.cli._run_qt", return_value=0
        ) as run_qt:
            rc = cli.main([])
        self.assertEqual(rc, 0)
        run_tk.assert_called_once_with()
        run_qt.assert_not_called()

    def test_main_uses_qt_frontend_when_requested(self) -> None:
        with patch("gui.cli._run_tk", return_value=0) as run_tk, patch(
            "gui.cli._run_qt", return_value=0
        ) as run_qt:
            rc = cli.main(["--ui", "qt"])
        self.assertEqual(rc, 0)
        run_qt.assert_called_once_with()
        run_tk.assert_not_called()


if __name__ == "__main__":
    unittest.main()

