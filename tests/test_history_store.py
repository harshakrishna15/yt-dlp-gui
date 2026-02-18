import unittest
from pathlib import Path

from gui import history_store


class TestHistoryStore(unittest.TestCase):
    def test_normalize_output_path_fallback(self) -> None:
        # Smoke-test normalization keeps a usable string path.
        raw = Path("/tmp/example.mp4")
        normalized = history_store.normalize_output_path(raw)
        self.assertTrue(normalized.endswith("example.mp4"))

    def test_upsert_history_entry_deduplicates_epoch_suffix(self) -> None:
        history: list[dict[str, str]] = []
        seen: set[str] = set()

        history_store.upsert_history_entry(
            history,
            seen,
            normalized_path="/tmp/clip_1700000000.mp4",
            source_url="https://example.com/a",
            timestamp="2026-02-17 12:00:00",
            max_entries=10,
        )
        history_store.upsert_history_entry(
            history,
            seen,
            normalized_path="/tmp/clip_1700000999.mp4",
            source_url="https://example.com/a",
            timestamp="2026-02-17 12:05:00",
            max_entries=10,
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["name"], "clip_1700000999.mp4")
        self.assertEqual(history[0]["timestamp"], "2026-02-17 12:05:00")

    def test_upsert_history_entry_respects_max_entries(self) -> None:
        history: list[dict[str, str]] = []
        seen: set[str] = set()

        history_store.upsert_history_entry(
            history,
            seen,
            normalized_path="/tmp/a.mp4",
            source_url="https://example.com/a",
            timestamp="2026-02-17 12:00:00",
            max_entries=1,
        )
        history_store.upsert_history_entry(
            history,
            seen,
            normalized_path="/tmp/b.mp4",
            source_url="https://example.com/b",
            timestamp="2026-02-17 12:01:00",
            max_entries=1,
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["name"], "b.mp4")
        self.assertNotIn("/tmp/a.mp4", seen)


if __name__ == "__main__":
    unittest.main()
