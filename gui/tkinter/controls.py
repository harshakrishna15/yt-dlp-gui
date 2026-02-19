from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ..common import format_pipeline, formats as formats_mod, yt_dlp_helpers as helpers
from ..core import format_selection as core_format_selection
from ..core import ui_state as core_ui_state
from ..core import urls as core_urls
from .constants import AUDIO_CONTAINERS, FETCH_DEBOUNCE_MS, VIDEO_CONTAINERS


class ControlsMixin:
    def _set_combobox_enabled(self, combo: ttk.Combobox, enabled: bool) -> None:
        combo.configure(state="readonly" if enabled else "disabled")

    def _set_audio_language_values(self, languages: list[str]) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for value in languages:
            clean = str(value or "").strip().lower()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            unique.append(clean)
        values = ["Any"] + unique

        combo = getattr(self, "audio_language_combo", None)
        if combo is not None:
            try:
                combo.configure(values=values)
            except tk.TclError:
                pass

        var = getattr(self, "audio_language_var", None)
        if var is None:
            return
        try:
            current = str(var.get() or "").strip()
        except (tk.TclError, AttributeError, TypeError, ValueError):
            return
        if not current:
            var.set("Any")
            return
        if current.lower() in {"any", "auto"}:
            var.set("Any")
            return
        if current.lower() not in {item.lower() for item in values}:
            var.set("Any")

    def _configure_combobox(
        self,
        label: tk.Widget,
        combo: ttk.Combobox,
        *,
        show: bool,
        enabled: bool,
    ) -> None:
        self._set_widget_visible(label, show)
        self._set_widget_visible(combo, show)
        self._set_combobox_enabled(combo, enabled and show)

    def _set_mixed_prompt_ui(self, show: bool) -> None:
        self._mixed_prompt_active = show
        self._set_widget_visible(self.mixed_prompt_label, show)
        self._set_widget_visible(self.mixed_prompt_frame, show)

    def _on_mode_change(self) -> None:
        self._refresh_container_choices()
        self._apply_mode_formats()
        self._update_controls_state()

    def _refresh_container_choices(self) -> None:
        mode = self.mode_var.get()
        if mode == "audio":
            containers = list(AUDIO_CONTAINERS)
            if self.format_filter_var.get() not in containers:
                self.format_filter_var.set(containers[0])
            self.codec_filter_var.set("")
        elif mode == "video":
            containers = list(VIDEO_CONTAINERS)
            if self.format_filter_var.get() not in containers:
                self.format_filter_var.set("")
        else:
            containers = []
            self.format_filter_var.set("")
            self.codec_filter_var.set("")
            self.format_var.set("")
        self.container_combo.configure(values=containers)

    def _reset_format_selections(self) -> None:
        if self.mode_var.get() == "audio":
            self.format_filter_var.set(AUDIO_CONTAINERS[0])
            self.codec_filter_var.set("")
        elif self.mode_var.get() == "video":
            self.format_filter_var.set("")
            self.codec_filter_var.set("")
        else:
            self.format_filter_var.set("")
            self.codec_filter_var.set("")
        self.format_var.set("")

    def _on_url_change(self, force: bool = False) -> None:
        self._normalize_url_var()
        url = self.url_var.get().strip()
        if self._mixed_prompt_active and url == self._pending_mixed_url:
            return
        self._hide_mixed_prompt()
        # Reset settings whenever the URL changes.
        self.mode_var.set("")
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
        self.convert_to_mp4_var.set(False)
        self.playlist_items_var.set("")
        self.formats.preview_title = ""
        self.formats.audio_languages = []
        self.preview_title_var.set("")
        self._set_audio_language_values([])
        if url and core_urls.is_mixed_url(url):
            self._show_mixed_prompt(url)
            return
        if url and core_urls.is_playlist_url(url):
            self._set_playlist_ui(True)
        else:
            self._set_playlist_ui(False)
        # Debounce format fetching when the URL changes.
        self._reset_format_selections()
        self._update_controls_state()
        self._cancel_after("fetch_after_id", self.formats)
        if force:
            self._start_fetch_formats(force=True)
        else:
            self.formats.fetch_after_id = self._safe_after(
                FETCH_DEBOUNCE_MS, self._start_fetch_formats
            )

    def _start_fetch_formats(self, force: bool = False) -> None:
        self.formats.fetch_after_id = None
        url = self.url_var.get().strip()
        if not url or self.is_downloading or self.formats.is_fetching:
            return
        # Use cache if available.
        cached = self.formats.cache.get(url)
        if cached:
            self._load_cached_formats(url, cached)
            return
        if (
            url == self.formats.last_fetched_url
            and not force
            and not self.formats.last_fetch_failed
        ):
            return
        self.formats.is_fetching = True
        self.formats.last_fetched_url = url
        self.formats.last_fetch_failed = False
        self._fetch_request_seq += 1
        request_id = self._fetch_request_seq
        self._active_fetch_request_id = request_id
        self.status_var.set("Fetching formats...")
        self.start_button.state(["disabled"])
        self.format_combo.configure(state="disabled")
        self.convert_to_mp4_var.set(False)
        threading.Thread(
            target=self._fetch_formats_worker,
            args=(url, request_id),
            daemon=True,
        ).start()

    def _fetch_formats_worker(self, url: str, request_id: int) -> None:
        try:
            info = helpers.fetch_info(url)
        except Exception as exc:  # show error in UI
            self._log(f"Could not fetch formats: {exc}")
            self._post_ui(
                self._set_formats,
                [],
                error=True,
                fetch_url=url,
                request_id=request_id,
            )
            return
        entries = info.get("entries")
        is_playlist = info.get("_type") == "playlist" or entries is not None
        formats = formats_mod.formats_from_info(info)
        preview_title = format_pipeline.preview_title_from_info(info)
        self._post_ui(
            self._set_formats,
            formats,
            is_playlist=is_playlist,
            fetch_url=url,
            request_id=request_id,
            preview_title=preview_title,
        )

    def _set_formats(
        self,
        formats: list[dict],
        error: bool = False,
        is_playlist: bool = False,
        fetch_url: str = "",
        request_id: int | None = None,
        preview_title: str = "",
    ) -> None:
        if request_id is not None and request_id != self._active_fetch_request_id:
            return
        current_url = ""
        try:
            current_url = (self.url_var.get() or "").strip()  # type: ignore[attr-defined]
        except (tk.TclError, AttributeError, TypeError, ValueError):
            current_url = ""
        if fetch_url and current_url and fetch_url != current_url:
            self._active_fetch_request_id = None
            self.formats.is_fetching = False
            self._safe_after(0, self._start_fetch_formats)
            return
        if request_id is not None:
            self._active_fetch_request_id = None
        self.formats.is_fetching = False
        if fetch_url:
            self.formats.last_fetched_url = fetch_url
        self.formats.preview_title = (preview_title or "").strip()
        self.preview_title_var.set(self.formats.preview_title)
        if not error:
            if is_playlist:
                self._set_playlist_ui(True)
            else:
                self._set_playlist_ui(False)
        else:
            self._set_playlist_ui(False)
        if error or not formats:
            if error:
                self.formats.last_fetched_url = ""
                self.formats.last_fetch_failed = True
            self.formats.video_labels = []
            self.formats.video_lookup = {}
            self.formats.audio_labels = []
            self.formats.audio_lookup = {}
            self.formats.audio_languages = []
            self._set_audio_language_values([])
            if not self.formats.preview_title:
                self.preview_title_var.set("")
            self._apply_mode_formats()
            self._update_controls_state()
            return

        collections = format_pipeline.build_format_collections(formats)
        self.formats.video_labels = list(collections["video_labels"])
        self.formats.video_lookup = dict(collections["video_lookup"])
        self.formats.audio_labels = list(collections["audio_labels"])
        self.formats.audio_lookup = dict(collections["audio_lookup"])
        self.formats.audio_languages = list(collections["audio_languages"])
        self._set_audio_language_values(self.formats.audio_languages)
        # Cache processed formats for this URL.
        cache_key = fetch_url or self.formats.last_fetched_url
        self._cache_formats_entry(
            cache_key,
            {
                "video_labels": self.formats.video_labels,
                "video_lookup": self.formats.video_lookup,
                "audio_labels": self.formats.audio_labels,
                "audio_lookup": self.formats.audio_lookup,
                "audio_languages": self.formats.audio_languages,
                "preview_title": self.formats.preview_title,
            },
        )

        # Require user to pick a container after formats load.
        self._reset_format_selections()
        self._apply_mode_formats()
        self.formats.last_fetch_failed = False
        self.status_var.set("Formats loaded")
        self._update_controls_state()

    def _load_cached_formats(self, url: str, cached: dict) -> None:
        self._touch_cached_url(url)
        self.formats.last_fetched_url = url
        self.formats.video_labels = list(cached.get("video_labels", []))
        self.formats.video_lookup = dict(cached.get("video_lookup", {}))
        self.formats.audio_labels = list(cached.get("audio_labels", []))
        self.formats.audio_lookup = dict(cached.get("audio_lookup", {}))
        self.formats.audio_languages = list(cached.get("audio_languages", []))
        self.formats.preview_title = str(cached.get("preview_title", ""))
        self.preview_title_var.set(self.formats.preview_title)
        self._set_audio_language_values(self.formats.audio_languages)
        self._reset_format_selections()
        self._apply_mode_formats()
        self.status_var.set("Formats loaded (cached)")
        self._update_controls_state()

    def _apply_mode_formats(self) -> None:
        mode = self.mode_var.get()
        filter_val = self.format_filter_var.get()
        codec_raw = self.codec_filter_var.get()
        codec_val = codec_raw.lower()
        result = core_format_selection.select_mode_formats(
            mode=mode,
            container=filter_val,
            codec=codec_val,
            video_labels=list(self.formats.video_labels),
            video_lookup=dict(self.formats.video_lookup),
            audio_labels=list(self.formats.audio_labels),
            audio_lookup=dict(self.formats.audio_lookup),
            video_containers=VIDEO_CONTAINERS,
            required_video_codecs=("avc1", "av01"),
        )
        if (
            mode == "video"
            and filter_val in VIDEO_CONTAINERS
            and codec_val
            and result.codec_fallback_used
        ):
            msg = "Chosen codec not available for this container; showing all formats in container"
            self.status_var.set(msg)
            notice_key = (mode, filter_val, codec_raw)
            if notice_key != self.formats.last_codec_fallback_notice:
                self.formats.last_codec_fallback_notice = notice_key
                self._log(f"[info] {msg}")

        self.formats.filtered_labels = list(result.labels)
        self.formats.filtered_lookup = dict(result.lookup)
        self.format_combo.configure(values=self.formats.filtered_labels)
        if self.formats.filtered_labels:
            if self.format_var.get() not in self.formats.filtered_labels:
                self.format_var.set("")
        else:
            self.format_var.set("")
        self._update_controls_state()

    def _update_controls_state(self) -> None:
        url_present = bool(self.url_var.get().strip())
        has_formats_data = bool(self.formats.video_labels or self.formats.audio_labels)
        mode = self.mode_var.get()
        container_value = self.format_filter_var.get()
        if mode == "audio" and container_value not in AUDIO_CONTAINERS:
            self.format_filter_var.set(AUDIO_CONTAINERS[0])
            container_value = self.format_filter_var.get()
        is_playlist_url = self.is_playlist or (
            url_present and core_urls.is_playlist_url(self.url_var.get())
        )
        state = core_ui_state.compute_control_state(
            url_present=url_present,
            has_formats_data=has_formats_data,
            mode=mode,
            container_value=container_value,
            codec_value=self.codec_filter_var.get(),
            format_available=bool(self.formats.filtered_labels),
            format_selected=bool(self.format_var.get()),
            queue_ready=bool(self.queue_items),
            queue_active=self.queue_active,
            is_fetching=self.formats.is_fetching,
            is_downloading=self.is_downloading,
            cancel_requested=self._cancel_requested,
            is_playlist_url=is_playlist_url,
            mixed_prompt_active=self._mixed_prompt_active,
            playlist_items_requested=bool(self.playlist_enabled_var.get()),
            write_subtitles_requested=bool(self.write_subtitles_var.get()),
            allow_queue_input_context=True,
            audio_containers=AUDIO_CONTAINERS,
            video_containers=VIDEO_CONTAINERS,
        )

        # Keep all options visible; disable when not usable.
        self._configure_combobox(
            self.container_label,
            self.container_combo,
            show=True,
            enabled=state.container_enabled,
        )

        self._configure_combobox(
            self.codec_label,
            self.codec_combo,
            show=state.is_video_mode,
            enabled=state.codec_enabled,
        )

        # Convert checkbox only relevant when container is webm.
        self._set_widget_visible(self.convert_mp4_inline_label, state.show_convert)
        self._set_widget_visible(self.convert_mp4_check, state.show_convert)
        if state.convert_enabled:
            self.convert_mp4_check.state(["!disabled"])
        else:
            self.convert_to_mp4_var.set(False)
            self.convert_mp4_check.state(["disabled"])

        self._configure_combobox(
            self.format_label,
            self.format_combo,
            show=True,
            enabled=state.format_enabled,
        )

        if state.can_start_single:
            self.start_button.state(["!disabled"])
        else:
            self.start_button.state(["disabled"])
        if state.can_add_queue:
            self.add_queue_button.state(["!disabled"])
        else:
            self.add_queue_button.state(["disabled"])
        if state.can_start_queue:
            self.start_queue_button.state(["!disabled"])
        else:
            self.start_queue_button.state(["disabled"])

        # Cancel button (visible always; only enabled while a download is running).
        if state.can_cancel:
            self.cancel_button.state(["!disabled"])
        else:
            self.cancel_button.state(["disabled"])

        if state.playlist_items_enabled:
            self.playlist_items_entry.configure(state="normal")
        else:
            self.playlist_items_entry.configure(state="disabled")

        if state.mode_enabled:
            self.video_mode_radio.state(["!disabled"])
            self.audio_mode_radio.state(["!disabled"])
        else:
            self.video_mode_radio.state(["disabled"])
            self.audio_mode_radio.state(["disabled"])

        self._set_widget_visible(self.progress_item_label, self._show_progress_item)
        self._set_widget_visible(self.progress_item_value, self._show_progress_item)
        self._set_widget_visible(self.progress_frame, True)

        self._set_widget_visible(self.subtitle_languages_label, state.is_video_mode)
        self._set_widget_visible(self.subtitle_languages_entry, state.is_video_mode)
        self._set_widget_visible(self.subtitle_options_label, state.is_video_mode)
        self._set_widget_visible(self.write_subtitles_check, state.is_video_mode)
        self._set_widget_visible(self.embed_subtitles_check, state.is_video_mode)
        if state.subtitle_controls_enabled:
            self.subtitle_languages_entry.configure(state="normal")
            self.write_subtitles_check.state(["!disabled"])
        else:
            self.subtitle_languages_entry.configure(state="disabled")
            self.write_subtitles_check.state(["disabled"])
            self.embed_subtitles_var.set(False)
        if state.embed_allowed:
            self.embed_subtitles_check.state(["!disabled"])
        else:
            self.embed_subtitles_var.set(False)
            self.embed_subtitles_check.state(["disabled"])

        audio_language_combo = getattr(self, "audio_language_combo", None)
        if state.input_fields_enabled:
            self.browse_button.state(["!disabled"])
            self.paste_button.state(["!disabled"])
            if audio_language_combo is not None:
                try:
                    self._set_combobox_enabled(audio_language_combo, True)
                except (tk.TclError, RuntimeError):
                    audio_language_combo.configure(state="normal")
            self.network_timeout_entry.configure(state="normal")
            self.network_retries_entry.configure(state="normal")
            self.retry_backoff_entry.configure(state="normal")
        else:
            self.browse_button.state(["disabled"])
            self.paste_button.state(["disabled"])
            if audio_language_combo is not None:
                try:
                    self._set_combobox_enabled(audio_language_combo, False)
                except (tk.TclError, RuntimeError):
                    audio_language_combo.configure(state="disabled")
            self.network_timeout_entry.configure(state="disabled")
            self.network_retries_entry.configure(state="disabled")
            self.retry_backoff_entry.configure(state="disabled")

        custom_filename_entry = getattr(self, "custom_filename_entry", None)
        if custom_filename_entry is not None:
            if state.filename_enabled:
                custom_filename_entry.configure(state="normal")
            else:
                custom_filename_entry.configure(state="disabled")

        self.diagnostics_button.state(["!disabled"])
        self._update_history_buttons_state()

    def _set_playlist_ui(self, is_playlist: bool) -> None:
        self.is_playlist = is_playlist
        self._set_widget_visible(self.playlist_label, is_playlist)
        self._set_widget_visible(self.playlist_frame, is_playlist)
        if is_playlist:
            self.url_label.configure(text="Playlist URL")
            self.playlist_enabled_var.set(True)
        else:
            self.url_label.configure(text="Video URL")
            self.playlist_enabled_var.set(False)
            self.playlist_items_var.set("")
        self._update_controls_state()

    def _on_mixed_choose_playlist(self) -> None:
        if not self._pending_mixed_url:
            return
        resolved_url = core_urls.to_playlist_url(self._pending_mixed_url)
        self._hide_mixed_prompt()
        if resolved_url and resolved_url != self.url_var.get():
            self.url_var.set(resolved_url)

    def _on_mixed_choose_video(self) -> None:
        if not self._pending_mixed_url:
            return
        resolved_url = core_urls.strip_list_param(self._pending_mixed_url)
        self._hide_mixed_prompt()
        if resolved_url and resolved_url != self.url_var.get():
            self.url_var.set(resolved_url)
