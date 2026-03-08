import unittest

from gui.core import error_feedback


class TestCoreErrorFeedback(unittest.TestCase):
    def test_error_text_from_log_extracts_known_prefixes(self) -> None:
        self.assertEqual(
            error_feedback.error_text_from_log("[error] HTTP Error 403: Forbidden"),
            "HTTP Error 403: Forbidden",
        )
        self.assertEqual(
            error_feedback.error_text_from_log("[queue] failed: timed out"),
            "timed out",
        )
        self.assertIsNone(error_feedback.error_text_from_log("[status] Downloading..."))

    def test_download_feedback_handles_common_network_error(self) -> None:
        feedback = error_feedback.download_failed_feedback(
            "Temporary failure in name resolution"
        )
        self.assertEqual(feedback.reason, "network issue")
        self.assertIn("network", feedback.status.lower())
        self.assertIn("connection", feedback.message.lower())

    def test_download_feedback_handles_ffmpeg_missing(self) -> None:
        feedback = error_feedback.download_failed_feedback(
            "ffmpeg not found. Please install"
        )
        self.assertEqual(feedback.reason, "required media tools not found")
        self.assertIn("required media tools", feedback.status.lower())
        self.assertIn("missing components", feedback.message.lower())

    def test_formats_feedback_uses_unknown_fallback(self) -> None:
        feedback = error_feedback.formats_fetch_failed_feedback("random unexpected error")
        self.assertEqual(feedback.reason, "unknown error")
        self.assertIn("could not fetch formats", feedback.status.lower())
        self.assertIn("try again", feedback.message.lower())


if __name__ == "__main__":
    unittest.main()
