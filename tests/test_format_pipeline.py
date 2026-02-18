import unittest
from unittest.mock import patch

from gui import format_pipeline


class TestFormatPipeline(unittest.TestCase):
    def test_preview_title_from_info_prefers_top_level_title(self) -> None:
        info = {"title": "Top Title", "entries": [{"title": "Entry Title"}]}
        self.assertEqual(format_pipeline.preview_title_from_info(info), "Top Title")

    def test_preview_title_from_info_falls_back_to_first_entry(self) -> None:
        info = {"title": "", "entries": [{"title": "Entry Title"}]}
        self.assertEqual(format_pipeline.preview_title_from_info(info), "Entry Title")

    def test_preview_title_from_info_normalizes_whitespace(self) -> None:
        info = {"title": "  Hello \n  there\tworld  "}
        self.assertEqual(format_pipeline.preview_title_from_info(info), "Hello there world")

    def test_build_labeled_sets_inserts_best_audio_option(self) -> None:
        video_fmt = {"format_id": "137"}
        audio_fmt = {"format_id": "251"}
        with patch(
            "gui.format_pipeline.helpers.split_and_filter_formats",
            return_value=([video_fmt], [audio_fmt]),
        ), patch(
            "gui.format_pipeline.helpers.build_labeled_formats",
            side_effect=[
                [("Video 1080p", video_fmt)],
                [("Audio Opus", audio_fmt)],
            ],
        ):
            video_labeled, audio_labeled = format_pipeline.build_labeled_sets(
                [video_fmt, audio_fmt]
            )

        self.assertEqual(video_labeled[0][0], "Video 1080p")
        self.assertEqual(audio_labeled[0][0], format_pipeline.BEST_AUDIO_LABEL)
        self.assertEqual(audio_labeled[1][0], "Audio Opus")

    def test_build_format_collections_returns_lookup_and_languages(self) -> None:
        video_labeled = [("Video 1080p", {"format_id": "137"})]
        audio_labeled = [
            (format_pipeline.BEST_AUDIO_LABEL, dict(format_pipeline.BEST_AUDIO_INFO)),
            ("Audio Opus", {"format_id": "251"}),
        ]
        with patch(
            "gui.format_pipeline.build_labeled_sets",
            return_value=(video_labeled, audio_labeled),
        ), patch(
            "gui.format_pipeline.helpers.extract_audio_languages",
            return_value=["en", "es"],
        ):
            collections = format_pipeline.build_format_collections([{"format_id": "137"}])

        self.assertEqual(collections["video_labels"], ["Video 1080p"])
        self.assertIn("Video 1080p", collections["video_lookup"])
        self.assertEqual(collections["audio_labels"][0], format_pipeline.BEST_AUDIO_LABEL)
        self.assertEqual(collections["audio_languages"], ["en", "es"])


if __name__ == "__main__":
    unittest.main()
