from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlState:
    is_audio_mode: bool
    is_video_mode: bool
    mode_chosen: bool
    filter_chosen: bool
    codec_chosen: bool
    base_ready: bool
    input_ready: bool
    single_ready: bool
    can_start_single: bool
    can_add_queue: bool
    can_start_queue: bool
    can_cancel: bool
    mode_enabled: bool
    container_enabled: bool
    codec_enabled: bool
    show_convert: bool
    convert_enabled: bool
    format_enabled: bool
    playlist_items_enabled: bool
    filename_enabled: bool
    subtitle_controls_enabled: bool
    embed_allowed: bool
    input_fields_enabled: bool


def compute_control_state(
    *,
    url_present: bool,
    has_formats_data: bool,
    mode: str,
    container_value: str,
    codec_value: str,
    format_available: bool,
    format_selected: bool,
    queue_ready: bool,
    queue_active: bool,
    is_fetching: bool,
    is_downloading: bool,
    cancel_requested: bool,
    is_playlist_url: bool,
    mixed_prompt_active: bool,
    playlist_items_requested: bool,
    write_subtitles_requested: bool,
    allow_queue_input_context: bool,
    audio_containers: tuple[str, ...],
    video_containers: tuple[str, ...],
) -> ControlState:
    is_audio_mode = mode == "audio"
    is_video_mode = mode == "video"
    mode_chosen = is_audio_mode or is_video_mode
    filter_chosen = container_value in (
        audio_containers if is_audio_mode else video_containers
    )
    codec_chosen = bool(codec_value)

    base_ready = (not is_fetching) and (not is_downloading) and mode_chosen
    input_ready = base_ready and (
        url_present or (allow_queue_input_context and queue_ready)
    )
    single_ready = base_ready and url_present and has_formats_data
    can_start_single = (
        single_ready
        and filter_chosen
        and format_selected
        and (is_audio_mode or codec_chosen)
        and (not mixed_prompt_active)
    )
    can_add_queue = can_start_single and (not is_playlist_url) and (not queue_active)
    can_start_queue = queue_ready and (not is_downloading) and (not mixed_prompt_active)
    can_cancel = is_downloading and (not cancel_requested)
    mode_enabled = url_present and (not is_downloading) and has_formats_data

    show_convert = container_value == "webm"
    convert_enabled = input_ready and filter_chosen and show_convert
    format_enabled = (
        single_ready and filter_chosen and format_available and (is_audio_mode or codec_chosen)
    )
    subtitle_controls_enabled = is_video_mode and (not is_downloading)
    embed_allowed = subtitle_controls_enabled and write_subtitles_requested

    return ControlState(
        is_audio_mode=is_audio_mode,
        is_video_mode=is_video_mode,
        mode_chosen=mode_chosen,
        filter_chosen=filter_chosen,
        codec_chosen=codec_chosen,
        base_ready=base_ready,
        input_ready=input_ready,
        single_ready=single_ready,
        can_start_single=can_start_single,
        can_add_queue=can_add_queue,
        can_start_queue=can_start_queue,
        can_cancel=can_cancel,
        mode_enabled=mode_enabled,
        container_enabled=input_ready,
        codec_enabled=is_video_mode and input_ready and filter_chosen,
        show_convert=show_convert,
        convert_enabled=convert_enabled,
        format_enabled=format_enabled,
        playlist_items_enabled=playlist_items_requested and (not is_downloading),
        filename_enabled=(not is_downloading) and (not is_playlist_url),
        subtitle_controls_enabled=subtitle_controls_enabled,
        embed_allowed=embed_allowed,
        input_fields_enabled=not is_downloading,
    )
