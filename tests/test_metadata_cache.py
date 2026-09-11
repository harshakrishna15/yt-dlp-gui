import unittest

from gui.common.metadata_cache import MetadataPreviewCache


def preview(title="Example"):
    return {
        "preview_title": title,
        "collections": {
            "video_labels": ["1080p"],
            "video_lookup": {"1080p": {
                "format_id": "137", "vcodec": "avc1", "acodec": "none",
                "ext": "mp4", "height": 1080, "filesize": 100,
                "url": "https://private.test/signed-stream",
                "http_headers": {"Cookie": "sensitive"}, "fragments": [1, 2],
            }},
        },
        "cacheable": True,
    }


class TestMetadataPreviewCache(unittest.TestCase):
    def test_cache_strips_stream_details_and_returns_independent_values(self):
        cache = MetadataPreviewCache()
        original = preview()
        self.assertTrue(cache.put("url", original))
        original["preview_title"] = "Changed"
        cached = cache.get("url")
        self.assertEqual(cached["preview_title"], "Example")
        self.assertNotIn("cacheable", cached)
        fmt = cached["collections"]["video_lookup"]["1080p"]
        self.assertEqual(fmt["format_id"], "137")
        for field in ("url", "http_headers", "fragments"):
            self.assertNotIn(field, fmt)
        fmt["height"] = 0
        self.assertEqual(cache.get("url")["collections"]["video_lookup"]["1080p"]["height"], 1080)

    def test_reads_do_not_extend_expiration(self):
        now = [0]
        cache = MetadataPreviewCache(clock=lambda: now[0])
        cache.put("url", preview())
        now[0] = 119
        self.assertIsNotNone(cache.get("url"))
        now[0] = 120
        self.assertIsNone(cache.get("url"))

    def test_evicts_least_recently_used_preview(self):
        cache = MetadataPreviewCache(max_entries=2)
        cache.put("a", preview())
        cache.put("b", preview())
        cache.get("a")
        cache.put("c", preview())
        self.assertIsNone(cache.get("b"))
        self.assertIsNotNone(cache.get("a"))
        self.assertIsNotNone(cache.get("c"))

    def test_byte_budget_and_oversized_replacement_are_bounded(self):
        cache = MetadataPreviewCache(max_bytes=800)
        cache.put("a", preview("a" * 150))
        cache.put("b", preview("b" * 150))
        self.assertIsNone(cache.get("a"))
        self.assertIsNotNone(cache.get("b"))
        self.assertFalse(cache.put("b", preview("b" * 1000)))
        self.assertIsNone(cache.get("b"))

    def test_clear_and_new_session_remove_previews(self):
        cache = MetadataPreviewCache()
        cache.put("url", preview())
        self.assertIsNone(MetadataPreviewCache().get("url"))
        cache.clear()
        self.assertIsNone(cache.get("url"))

    def test_excessive_format_counts_and_invalid_json_are_not_cached(self):
        cache = MetadataPreviewCache()
        payload = preview()
        payload["collections"]["video_lookup"] = {str(i): {} for i in range(1001)}
        self.assertFalse(cache.put("url", payload))
        payload = preview()
        payload["preview_title"] = float("nan")
        self.assertFalse(cache.put("url", payload))
