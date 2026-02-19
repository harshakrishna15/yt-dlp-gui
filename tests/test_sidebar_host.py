import unittest

try:
    from gui.tkinter.sidebar_host import SidebarHost
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Tk frontend module not available") from exc


class TestSidebarWidthPolicy(unittest.TestCase):
    def test_full_width_ratio_takes_entire_available_width(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=1000,
            content_width=320,
            width_ratio=1.0,
            min_width=720,
            max_width=None,
            margin=0,
            manual_width=None,
        )
        self.assertEqual(width, 1000)

    def test_ratio_target_used_for_wide_root(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=1000,
            content_width=220,
            width_ratio=0.9,
            min_width=480,
            max_width=None,
            margin=0,
            manual_width=None,
        )
        self.assertEqual(width, 900)

    def test_max_width_caps_target(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=1400,
            content_width=180,
            width_ratio=0.42,
            min_width=260,
            max_width=420,
            margin=0,
            manual_width=None,
        )
        self.assertEqual(width, 420)

    def test_content_width_can_expand_target(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=1000,
            content_width=760,
            width_ratio=0.5,
            min_width=420,
            max_width=None,
            margin=0,
            manual_width=None,
        )
        self.assertEqual(width, 760)

    def test_manual_width_overrides_ratio_and_min(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=1000,
            content_width=760,
            width_ratio=0.5,
            min_width=420,
            max_width=None,
            margin=0,
            manual_width=640,
        )
        self.assertEqual(width, 640)

    def test_margin_limited_root_clamps_target(self) -> None:
        width = SidebarHost.compute_target_width(
            root_width=620,
            content_width=500,
            width_ratio=0.9,
            min_width=480,
            max_width=None,
            margin=20,
            manual_width=None,
        )
        self.assertEqual(width, 558)


if __name__ == "__main__":
    unittest.main()
