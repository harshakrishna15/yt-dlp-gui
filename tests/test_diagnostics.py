from datetime import datetime
import unittest

from gui import diagnostics


class TestDiagnostics(unittest.TestCase):
    def test_sanitize_url_for_report_keeps_only_whitelisted_query_keys(self) -> None:
        url = "https://www.youtube.com/watch?v=abc123&list=PL123&t=60&token=secret#frag"
        sanitized = diagnostics.sanitize_url_for_report(url)
        self.assertIn("watch?v=abc123&list=PL123", sanitized)
        self.assertNotIn("token=secret", sanitized)
        self.assertNotIn("t=60", sanitized)
        self.assertNotIn("#frag", sanitized)

    def test_build_report_payload_includes_sections_and_sanitized_urls(self) -> None:
        payload = diagnostics.build_report_payload(
            generated_at=datetime(2026, 2, 17, 12, 0, 0),
            status="Idle",
            simple_state="Idle",
            url="https://www.youtube.com/watch?v=abc123&token=secret",
            mode="video",
            container="mp4",
            codec="avc1",
            format_label="1080p",
            queue_items=[
                {
                    "url": "https://www.youtube.com/watch?v=queue123&token=secret",
                    "settings": {"mode": "video", "format_filter": "mp4"},
                }
            ],
            queue_active=False,
            is_downloading=False,
            preview_title="Example",
            options={
                "network_timeout_s": 20,
                "network_retries": 1,
                "retry_backoff_s": 1.5,
                "write_subtitles": False,
                "embed_subtitles": False,
                "subtitle_languages": [],
                "audio_language": "",
                "custom_filename": "",
            },
            history_items=[
                {
                    "timestamp": "2026-02-17 12:00:00",
                    "name": "a.mp4",
                    "path": "/tmp/a.mp4",
                    "source_url": "https://www.youtube.com/watch?v=hist123&token=secret",
                }
            ],
            logs_text="line one\nline two",
        )

        self.assertIn("generated_at=2026-02-17T12:00:00", payload)
        self.assertIn("[queue]", payload)
        self.assertIn("[history]", payload)
        self.assertIn("[logs]", payload)
        self.assertIn("watch?v=abc123", payload)
        self.assertIn("watch?v=queue123", payload)
        self.assertIn("watch?v=hist123", payload)
        self.assertNotIn("token=secret", payload)
        self.assertTrue(payload.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
