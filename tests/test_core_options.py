import unittest

from gui.core import options


class TestCoreOptions(unittest.TestCase):
    def test_parse_int_setting_clamps(self) -> None:
        self.assertEqual(
            options.parse_int_setting("999", default=10, minimum=1, maximum=100),
            100,
        )
        self.assertEqual(
            options.parse_int_setting("bad", default=10, minimum=1, maximum=100),
            10,
        )

    def test_parse_float_setting_clamps(self) -> None:
        self.assertAlmostEqual(
            options.parse_float_setting("40.7", default=1.0, minimum=0.0, maximum=30.0),
            30.0,
        )
        self.assertAlmostEqual(
            options.parse_float_setting("x", default=1.5, minimum=0.0, maximum=30.0),
            1.5,
        )

    def test_sanitize_custom_filename(self) -> None:
        self.assertEqual(options.sanitize_custom_filename("  foo/bar.mp4 "), "foo bar")
        self.assertEqual(options.sanitize_custom_filename(".."), "")

    def test_parse_and_coerce_subtitle_languages(self) -> None:
        self.assertEqual(
            options.parse_subtitle_languages(" en,ES, en , fr "),
            ["en", "es", "fr"],
        )
        self.assertEqual(
            options.coerce_subtitle_languages(["EN", " en ", "", "es"]),
            ["en", "es"],
        )
        self.assertEqual(
            options.coerce_subtitle_languages("de, DE ,it"),
            ["de", "it"],
        )

    def test_normalize_edit_friendly_encoder_preference_aliases(self) -> None:
        self.assertEqual(options.normalize_edit_friendly_encoder_preference("nvenc"), "nvidia")
        self.assertEqual(
            options.normalize_edit_friendly_encoder_preference("videotoolbox"),
            "apple",
        )
        self.assertEqual(options.normalize_edit_friendly_encoder_preference("qsv"), "intel")
        self.assertEqual(options.normalize_edit_friendly_encoder_preference("x264"), "cpu")
        self.assertEqual(
            options.normalize_edit_friendly_encoder_preference("unknown"),
            "auto",
        )

    def test_build_download_options_uses_supported_defaults(self) -> None:
        result = options.build_download_options(
            custom_filename_raw=" my:file.mp4 ",
            edit_friendly_encoder_raw="nvenc",
            timeout_default=20,
            retries_default=1,
            backoff_default=1.5,
            fragments_default=4,
        )
        self.assertEqual(result["network_timeout_s"], 20)
        self.assertEqual(result["network_retries"], 1)
        self.assertEqual(result["retry_backoff_s"], 1.5)
        self.assertEqual(result["concurrent_fragments"], 4)
        self.assertEqual(result["subtitle_languages"], [])
        self.assertFalse(result["write_subtitles"])
        self.assertFalse(result["embed_subtitles"])
        self.assertEqual(result["audio_language"], "")
        self.assertEqual(result["custom_filename"], "my file")
        self.assertEqual(result["edit_friendly_encoder"], "nvidia")

    def test_build_queue_settings_copies_option_fields(self) -> None:
        result = options.build_queue_settings(
            mode="video",
            format_filter="mp4",
            codec_filter="avc1",
            convert_to_mp4=False,
            format_label="1080p",
            estimated_size="1.2 GiB",
            output_dir="/tmp",
            playlist_items="",
            options={
                "network_timeout_s": 20,
                "network_retries": 1,
                "retry_backoff_s": 1.5,
                "concurrent_fragments": 2,
                "subtitle_languages": ["en"],
                "write_subtitles": True,
                "embed_subtitles": False,
                "audio_language": "en",
                "custom_filename": "x",
                "edit_friendly_encoder": "cpu",
            },
        )
        self.assertEqual(result["mode"], "video")
        self.assertEqual(result["network_timeout_s"], 20)
        self.assertEqual(result["concurrent_fragments"], 2)
        self.assertEqual(result["subtitle_languages"], ["en"])
        self.assertEqual(result["edit_friendly_encoder"], "cpu")


if __name__ == "__main__":
    unittest.main()
