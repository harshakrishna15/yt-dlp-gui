import unittest
from unittest.mock import patch

from gui import cli


class TestCliDispatch(unittest.TestCase):
    def test_parser_only_includes_qt_frontend(self) -> None:
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

    def test_main_rejects_invalid_frontend(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            cli.main(["--ui", "invalid"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
