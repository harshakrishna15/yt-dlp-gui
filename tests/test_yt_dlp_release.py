from __future__ import annotations

import io
import itertools
import unittest
from unittest.mock import patch

from gui.common import yt_dlp_release as release


class DownloadResponse(io.BytesIO):
    def __init__(self, payload, headers):
        super().__init__(payload)
        self.headers = headers
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class TestYtDlpReleaseProgress(unittest.TestCase):
    def download(self, payload, headers, *, clock=None):
        response = DownloadResponse(payload, headers)
        events = []
        ticks = clock or itertools.count(0, 0.25)
        with patch.object(release.urllib.request, "urlopen", return_value=response), patch.object(
            release.time, "monotonic", side_effect=lambda: next(ticks)
        ):
            result = release.download_bytes("https://example.test/yt-dlp", on_progress=events.append)
        return result, events, response

    def test_reads_chunks_and_reports_actual_bytes(self):
        payload = b"x" * (1024 * 1024)
        result, events, response = self.download(payload, {"Content-Length": str(len(payload))})
        self.assertEqual(result, payload)
        self.assertEqual(set(response.read_sizes), {256 * 1024})
        self.assertEqual(events[-1].downloaded_bytes, len(payload))
        self.assertEqual(events[-1].total_bytes, len(payload))
        self.assertGreater(events[-1].elapsed_seconds, 0)
        counts = [event.downloaded_bytes for event in events]
        self.assertEqual(counts, sorted(counts))
        self.assertTrue(any(0 < value < len(payload) for value in counts))

    def test_missing_invalid_or_nonpositive_lengths_remain_unknown(self):
        for value in (None, "invalid", "0", "-1"):
            with self.subTest(value=value):
                headers = {} if value is None else {"Content-Length": value}
                result, events, _ = self.download(b"download", headers)
                self.assertEqual(result, b"download")
                self.assertTrue(all(event.total_bytes is None for event in events))
                self.assertTrue(all(event.eta_seconds is None for event in events))

    def test_reports_final_progress_even_when_intermediate_updates_are_throttled(self):
        payload = b"x" * (1024 * 1024)
        _, events, _ = self.download(payload, {}, clock=itertools.repeat(0.0))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[-1].downloaded_bytes, len(payload))

    def test_incomplete_download_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete download"):
            self.download(b"short", {"Content-Length": "100"})

    def test_eta_requires_known_length_and_a_rate_sample(self):
        progress = release.YtDlpUpdateProgress("downloading", 25, 100, 5)
        self.assertEqual(progress.bytes_per_second, 5)
        self.assertEqual(progress.eta_seconds, 15)
        for received, total, elapsed in ((0, 100, 2), (10, 100, 0.5), (10, None, 2), (100, 100, 5)):
            with self.subTest(received=received, total=total, elapsed=elapsed):
                self.assertIsNone(release.YtDlpUpdateProgress("downloading", received, total, elapsed).eta_seconds)

    def test_release_reports_checking_and_verifying_without_skipping_checksum(self):
        payload = b"verified binary"
        checksum = release.sha256_bytes(payload)
        events = []
        with patch.object(release, "download_bytes", side_effect=(
            f"{checksum}  yt-dlp_macos\n".encode(), payload,
        )) as download:
            asset = release.fetch_latest_release_asset(platform="macos", on_progress=events.append)
        self.assertEqual(asset.payload, payload)
        self.assertEqual([event.stage for event in events], ["checking", "verifying"])
        self.assertEqual(download.call_args.kwargs["on_progress"], events.append)


if __name__ == "__main__":
    unittest.main()
