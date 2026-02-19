import unittest

try:
    from gui.tkinter.ui import _HeaderPanelSwitcher
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Tk frontend module not available") from exc


class _FakePanel:
    def __init__(self, open_state: bool = False) -> None:
        self._open = open_state
        self.open_calls = 0
        self.close_calls = 0

    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True
        self.open_calls += 1

    def close(self) -> None:
        self._open = False
        self.close_calls += 1


class _FakeButton:
    def __init__(self) -> None:
        self.command = None
        self.states: set[str] = set()

    def configure(self, **kwargs) -> None:
        command = kwargs.get("command")
        if command is not None:
            self.command = command

    def state(self, specs: list[str]) -> None:
        for state in specs:
            if state.startswith("!"):
                self.states.discard(state[1:])
                continue
            self.states.add(state)


class TestHeaderPanelSwitcher(unittest.TestCase):
    def _build_switcher(self) -> tuple[_HeaderPanelSwitcher, dict[str, _FakePanel], dict[str, _FakeButton]]:
        panels = {
            "queue": _FakePanel(),
            "history": _FakePanel(),
            "logs": _FakePanel(),
        }
        buttons = {
            "queue": _FakeButton(),
            "history": _FakeButton(),
            "logs": _FakeButton(),
        }
        switcher = _HeaderPanelSwitcher(panels=panels, buttons=buttons)
        switcher.bind()
        return switcher, panels, buttons

    def test_bind_sets_commands_and_clears_pressed_state(self) -> None:
        _switcher, _panels, buttons = self._build_switcher()
        self.assertIsNotNone(buttons["queue"].command)
        self.assertIsNotNone(buttons["history"].command)
        self.assertIsNotNone(buttons["logs"].command)
        self.assertNotIn("pressed", buttons["queue"].states)
        self.assertNotIn("pressed", buttons["history"].states)
        self.assertNotIn("pressed", buttons["logs"].states)

    def test_toggle_opens_target_and_closes_others(self) -> None:
        switcher, panels, buttons = self._build_switcher()
        switcher.toggle("history")

        self.assertTrue(panels["history"].is_open())
        self.assertFalse(panels["queue"].is_open())
        self.assertFalse(panels["logs"].is_open())
        self.assertEqual(panels["history"].open_calls, 1)
        self.assertEqual(panels["queue"].close_calls, 1)
        self.assertEqual(panels["logs"].close_calls, 1)
        self.assertIn("pressed", buttons["history"].states)
        self.assertNotIn("pressed", buttons["queue"].states)
        self.assertNotIn("pressed", buttons["logs"].states)

    def test_toggle_closes_active_panel_and_clears_active_button(self) -> None:
        switcher, panels, buttons = self._build_switcher()
        switcher.toggle("logs")
        switcher.toggle("logs")

        self.assertFalse(panels["logs"].is_open())
        self.assertEqual(panels["logs"].close_calls, 1)
        self.assertNotIn("pressed", buttons["queue"].states)
        self.assertNotIn("pressed", buttons["history"].states)
        self.assertNotIn("pressed", buttons["logs"].states)

    def test_button_command_routes_to_toggle(self) -> None:
        _switcher, panels, buttons = self._build_switcher()
        buttons["queue"].command()

        self.assertTrue(panels["queue"].is_open())

    def test_open_forces_panel_visible(self) -> None:
        switcher, panels, _buttons = self._build_switcher()
        switcher.open("logs")
        self.assertTrue(panels["logs"].is_open())
        switcher.open("queue")
        self.assertTrue(panels["queue"].is_open())
        self.assertFalse(panels["logs"].is_open())

    def test_close_active_closes_current_panel(self) -> None:
        switcher, panels, _buttons = self._build_switcher()
        switcher.open("history")
        switcher.close_active()
        self.assertFalse(panels["history"].is_open())


if __name__ == "__main__":
    unittest.main()
