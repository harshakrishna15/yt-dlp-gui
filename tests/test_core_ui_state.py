import unittest

from gui.core import ui_state


class TestUiState(unittest.TestCase):
    def test_audio_mode_allows_queue_input_context(self) -> None:
        state = ui_state.compute_control_state(
            url_present=False,
            has_formats_data=True,
            mode="audio",
            container_value="mp3",
            codec_value="",
            format_available=True,
            format_selected=True,
            queue_ready=True,
            queue_active=False,
            is_fetching=False,
            is_downloading=False,
            cancel_requested=False,
            is_playlist_url=False,
            mixed_prompt_active=False,
            playlist_items_requested=False,
            write_subtitles_requested=False,
            allow_queue_input_context=True,
            audio_containers=("m4a", "mp3"),
            video_containers=("mp4", "webm"),
        )
        self.assertTrue(state.container_enabled)
        self.assertFalse(state.can_start_single)
        self.assertTrue(state.can_start_queue)

    def test_video_mode_enables_start_when_required_inputs_present(self) -> None:
        state = ui_state.compute_control_state(
            url_present=True,
            has_formats_data=True,
            mode="video",
            container_value="mp4",
            codec_value="avc1",
            format_available=True,
            format_selected=True,
            queue_ready=False,
            queue_active=False,
            is_fetching=False,
            is_downloading=False,
            cancel_requested=False,
            is_playlist_url=False,
            mixed_prompt_active=False,
            playlist_items_requested=False,
            write_subtitles_requested=True,
            allow_queue_input_context=False,
            audio_containers=("m4a", "mp3"),
            video_containers=("mp4", "webm"),
        )
        self.assertTrue(state.can_start_single)
        self.assertTrue(state.can_add_queue)
        self.assertTrue(state.codec_enabled)
        self.assertTrue(state.subtitle_controls_enabled)
        self.assertTrue(state.embed_allowed)

    def test_downloading_state_disables_inputs(self) -> None:
        state = ui_state.compute_control_state(
            url_present=True,
            has_formats_data=True,
            mode="video",
            container_value="webm",
            codec_value="av01",
            format_available=True,
            format_selected=True,
            queue_ready=True,
            queue_active=True,
            is_fetching=False,
            is_downloading=True,
            cancel_requested=False,
            is_playlist_url=False,
            mixed_prompt_active=False,
            playlist_items_requested=True,
            write_subtitles_requested=True,
            allow_queue_input_context=False,
            audio_containers=("m4a", "mp3"),
            video_containers=("mp4", "webm"),
        )
        self.assertTrue(state.can_cancel)
        self.assertFalse(state.input_fields_enabled)
        self.assertFalse(state.filename_enabled)
        self.assertFalse(state.playlist_items_enabled)
        self.assertFalse(state.subtitle_controls_enabled)


if __name__ == "__main__":
    unittest.main()
