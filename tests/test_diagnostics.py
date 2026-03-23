from datetime import datetime
import unittest

from gui.common import diagnostics


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
                "custom_filename": "",
                "edit_friendly_encoder": "auto",
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

    def test_build_report_payload_caps_preview_title_and_history_entries(self) -> None:
        long_title = "x" * 200
        history_items = [
            {
                "timestamp": f"2026-02-17 12:{idx:02d}:00",
                "name": f"file-{idx}.mp4",
                "path": f"/tmp/file-{idx}.mp4",
                "source_url": f"https://example.com/watch?v={idx}",
            }
            for idx in range(55)
        ]
        payload = diagnostics.build_report_payload(
            generated_at=datetime(2026, 2, 17, 12, 0, 0),
            status="Idle",
            simple_state="Idle",
            url="https://example.com/watch?v=abc",
            mode="video",
            container="mp4",
            codec="avc1",
            format_label="1080p",
            queue_items=[],
            queue_active=False,
            is_downloading=False,
            preview_title=long_title,
            options={
                "custom_filename": "",
                "edit_friendly_encoder": "auto",
            },
            history_items=history_items,
            logs_text="ok",
        )

        self.assertIn(f"preview_title={'x' * 120}", payload)
        self.assertNotIn(f"preview_title={'x' * 121}", payload)

        history_section = payload.split("[history]\n", 1)[1].split("\n\n[logs]\n", 1)[0]
        history_lines = [line for line in history_section.splitlines() if line.strip()]
        self.assertEqual(len(history_lines), 50)
        self.assertIn("file-0.mp4", history_lines[0])
        self.assertIn("file-49.mp4", history_lines[-1])


if __name__ == "__main__":
    unittest.main()
