import unittest
from unittest.mock import patch

from gui import cli


class TestCliDispatch(unittest.TestCase):
    def test_parser_includes_tk_when_legacy_frontend_exists(self) -> None:
        with patch("gui.cli._has_legacy_tk_frontend", return_value=True):
            parser = cli._build_parser()

        ui_action = next(action for action in parser._actions if action.dest == "ui")
        self.assertEqual(tuple(ui_action.choices), ("qt", "tk"))

    def test_parser_only_includes_qt_when_legacy_frontend_is_missing(self) -> None:
        with patch("gui.cli._has_legacy_tk_frontend", return_value=False):
            parser = cli._build_parser()

        ui_action = next(action for action in parser._actions if action.dest == "ui")
        self.assertEqual(tuple(ui_action.choices), ("qt",))

    def test_main_defaults_to_qt_frontend(self) -> None:
        with patch("gui.cli._run_qt", return_value=0) as run_qt:
            rc = cli.main([])
        self.assertEqual(rc, 0)
        run_qt.assert_called_once_with()

    def test_main_accepts_explicit_qt_frontend(self) -> None:
        with patch("gui.cli._run_qt", return_value=0) as run_qt:
            rc = cli.main(["--ui", "qt"])
        self.assertEqual(rc, 0)
        run_qt.assert_called_once_with()

    def test_main_accepts_explicit_tk_frontend(self) -> None:
        with patch("gui.cli._has_legacy_tk_frontend", return_value=True), patch(
            "gui.cli._run_tk", return_value=0
        ) as run_tk:
            rc = cli.main(["--ui", "tk"])
        self.assertEqual(rc, 0)
        run_tk.assert_called_once_with()

    def test_run_tk_returns_error_when_legacy_frontend_is_missing(self) -> None:
        with patch("gui.cli._has_legacy_tk_frontend", return_value=False):
            rc = cli._run_tk()
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
