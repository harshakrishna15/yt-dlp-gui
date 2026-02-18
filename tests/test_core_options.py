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

    def test_language_parsing_and_coerce(self) -> None:
        self.assertEqual(options.parse_subtitle_languages("en, es ,en"), ["en", "es"])
        self.assertEqual(options.coerce_subtitle_languages(["en", "ES", "en"]), ["en", "es"])
        self.assertEqual(options.coerce_subtitle_languages("fr, de"), ["fr", "de"])

    def test_sanitize_custom_filename(self) -> None:
        self.assertEqual(options.sanitize_custom_filename("  foo/bar.mp4 "), "foo bar")
        self.assertEqual(options.sanitize_custom_filename(".."), "")

    def test_build_download_options(self) -> None:
        result = options.build_download_options(
            network_timeout_raw="30",
            network_retries_raw="3",
            retry_backoff_raw="2.5",
            subtitle_languages_raw="en,es",
            write_subtitles_requested=True,
            embed_subtitles_requested=True,
            is_video_mode=True,
            audio_language_raw=" en ",
            custom_filename_raw=" my:file.mp4 ",
            timeout_default=20,
            retries_default=1,
            backoff_default=1.5,
        )
        self.assertEqual(result["network_timeout_s"], 30)
        self.assertEqual(result["network_retries"], 3)
        self.assertEqual(result["retry_backoff_s"], 2.5)
        self.assertEqual(result["subtitle_languages"], ["en", "es"])
        self.assertTrue(result["write_subtitles"])
        self.assertTrue(result["embed_subtitles"])
        self.assertEqual(result["audio_language"], "en")
        self.assertEqual(result["custom_filename"], "my file")

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
                "subtitle_languages": ["en"],
                "write_subtitles": True,
                "embed_subtitles": False,
                "audio_language": "en",
                "custom_filename": "x",
            },
        )
        self.assertEqual(result["mode"], "video")
        self.assertEqual(result["network_timeout_s"], 20)
        self.assertEqual(result["subtitle_languages"], ["en"])


if __name__ == "__main__":
    unittest.main()

