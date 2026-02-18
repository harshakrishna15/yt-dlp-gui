import unittest

from gui.core import urls


class TestCoreUrls(unittest.TestCase):
    def test_strip_url_whitespace(self) -> None:
        self.assertEqual(
            urls.strip_url_whitespace(" https://x.com/watch?v=abc \n\t"),
            "https://x.com/watch?v=abc",
        )

    def test_playlist_and_mixed_detection(self) -> None:
        self.assertTrue(urls.is_playlist_url("https://www.youtube.com/playlist?list=PL123"))
        self.assertTrue(
            urls.is_mixed_url("https://www.youtube.com/watch?v=abc123&list=PL123")
        )
        self.assertFalse(urls.is_mixed_url("https://www.youtube.com/watch?v=abc123"))

    def test_strip_list_param(self) -> None:
        self.assertEqual(
            urls.strip_list_param(
                "https://www.youtube.com/watch?v=abc123&list=PL123&index=4&start=20"
            ),
            "https://www.youtube.com/watch?v=abc123",
        )

    def test_to_playlist_url(self) -> None:
        self.assertEqual(
            urls.to_playlist_url("https://www.youtube.com/watch?v=abc123&list=PL123"),
            "https://www.youtube.com/playlist?list=PL123",
        )


if __name__ == "__main__":
    unittest.main()

