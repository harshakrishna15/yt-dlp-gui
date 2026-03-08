from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.ui_state import ControlState

if TYPE_CHECKING:
    from .app import QtYtDlpGui


def apply_control_state(
    window: "QtYtDlpGui",
    state: ControlState,
    *,
    pending_mixed_url: str,
) -> None:
    window.start_button.setEnabled(state.can_start_single)
    window.add_queue_button.setEnabled(state.can_add_queue)
    window.start_queue_button.setEnabled(state.can_start_queue)
    window.cancel_button.setEnabled(state.can_cancel)

    window.video_radio.setEnabled(state.mode_enabled)
    window.audio_radio.setEnabled(state.mode_enabled)

    window.container_combo.setEnabled(state.container_enabled)
    window.codec_combo.setEnabled(state.codec_enabled)
    window.convert_check.setEnabled(state.convert_enabled)
    if not window.convert_check.isEnabled():
        window.convert_check.setChecked(False)

    window.format_combo.setEnabled(state.format_enabled)
    window.playlist_items_edit.setEnabled(state.playlist_items_enabled)
    window.filename_edit.setEnabled(state.filename_enabled)

    window.url_edit.setEnabled(state.input_fields_enabled)
    window.paste_button.setEnabled(state.input_fields_enabled)
    window.analyze_button.setEnabled(state.can_fetch_formats)
    window.browse_button.setEnabled(state.input_fields_enabled)
    mixed_actions_enabled = state.input_fields_enabled and bool(pending_mixed_url)
    window.use_single_video_url_button.setEnabled(mixed_actions_enabled)
    window.use_playlist_url_button.setEnabled(mixed_actions_enabled)

    window.subtitle_languages_edit.setEnabled(state.subtitle_controls_enabled)
    window.write_subtitles_check.setEnabled(state.subtitle_controls_enabled)
    window.embed_subtitles_check.setEnabled(state.embed_allowed)
    if not state.embed_allowed:
        window.embed_subtitles_check.setChecked(False)

    window.audio_language_combo.setEnabled(state.input_fields_enabled)
    window.network_timeout_edit.setEnabled(state.input_fields_enabled)
    window.network_retries_edit.setEnabled(state.input_fields_enabled)
    window.retry_backoff_edit.setEnabled(state.input_fields_enabled)
    window.concurrent_fragments_edit.setEnabled(state.input_fields_enabled)
