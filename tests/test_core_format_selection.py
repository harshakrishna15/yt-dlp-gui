import unittest

from gui.common import format_pipeline
from gui.core import format_selection


class TestCoreFormatSelection(unittest.TestCase):
    def test_codec_matches_preference(self) -> None:
        self.assertTrue(format_selection.codec_matches_preference("avc1.640028", "avc1"))
        self.assertTrue(format_selection.codec_matches_preference("av01.0.05M.08", "av01"))
        self.assertFalse(format_selection.codec_matches_preference("vp9", "avc1"))

    def test_select_mode_formats_audio_fallback(self) -> None:
        result = format_selection.select_mode_formats(
            mode="audio",
            container="mp3",
            codec="",
            video_labels=[],
            video_lookup={},
            audio_labels=[],
            audio_lookup={},
        )
        self.assertEqual(result.labels, [format_pipeline.BEST_AUDIO_LABEL])
        self.assertIn(format_pipeline.BEST_AUDIO_LABEL, result.lookup)

    def test_select_mode_formats_video_codec_fallback(self) -> None:
        result = format_selection.select_mode_formats(
            mode="video",
            container="mp4",
            codec="av01",
            video_labels=["A", "B"],
            video_lookup={
                "A": {"ext": "mp4", "vcodec": "avc1.640028"},
                "B": {"ext": "mp4", "vcodec": "h264"},
            },
            audio_labels=[],
            audio_lookup={},
        )
        self.assertTrue(result.codec_fallback_used)
        self.assertEqual(result.labels, ["A", "B"])

    def test_resolve_format_for_info(self) -> None:
        logs: list[str] = []
        info = {
            "title": "Demo",
            "_type": "video",
            "formats": [
                {"format_id": "1", "ext": "mp4", "vcodec": "avc1.640028", "acodec": "mp4a.40.2"},
                {"format_id": "2", "ext": "webm", "vcodec": "vp9", "acodec": "opus"},
                {"format_id": "a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2"},
            ],
        }
        result = format_selection.resolve_format_for_info(
            info=info,
            formats=info["formats"],
            settings={
                "mode": "video",
                "format_filter": "mp4",
                "codec_filter": "avc1",
                "format_label": "",
            },
            log=logs.append,
        )
        self.assertEqual(result["format_filter"], "mp4")
        self.assertEqual(result["title"], "Demo")
        self.assertIn("fmt_info", result)


if __name__ == "__main__":
    unittest.main()

