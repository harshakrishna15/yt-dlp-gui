import re
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, urlparse

# Timing/layout constants (keep UI behavior consistent and readable).
FETCH_DEBOUNCE_MS = 600
PROGRESS_ANIM_MS = 33

VIDEO_CONTAINERS = ("mp4", "webm")
AUDIO_CONTAINERS = ("m4a", "mp3", "opus", "wav", "flac")

from . import download, formats as formats_mod, ui, yt_dlp_helpers as helpers
from .state import FormatState


class YtDlpGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("yt-dlp-gui")
        self.root.minsize(720, 550)
        self._progress_anim_after_id: str | None = None
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self.download_thread: threading.Thread | None = None
        self.is_downloading = False
        self._cancel_event: threading.Event | None = None
        self._cancel_requested = False
        self.formats = FormatState()
        self._normalizing_url = False
        self.is_playlist = False
        self._mixed_prompt_active = False
        self._pending_mixed_url = ""
        self.queue_items: list[dict] = []
        self.queue_active = False
        self.queue_index: int | None = None
        self.queue_settings: dict | None = None

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="")  # "video" or "audio"
        self.playlist_enabled_var = tk.BooleanVar(value=True)
        self.playlist_items_var = tk.StringVar(value="")
        # These are filled after probing a URL.
        self.format_filter_var = tk.StringVar(value="")  # must choose mp4 or webm
        self.codec_filter_var = tk.StringVar(value="")  # must choose avc1 or av01
        self.convert_to_mp4_var = tk.BooleanVar(
            value=False
        )  # convert WebM to MP4 after download (re-encode)
        self.format_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = tk.StringVar(value="Idle")
        self._last_status_logged = self.status_var.get()
        self.simple_state_var = tk.StringVar(value="Idle")
        self.progress_pct_var = tk.StringVar(value="—")
        self.progress_speed_var = tk.StringVar(value="—")
        self.progress_eta_var = tk.StringVar(value="—")
        self.progress_item_var = tk.StringVar(value="—")
        self._show_progress_item = False

        self.logs = ui.build_ui(self)
        self.queue_panel.refresh(self.queue_items)
        self._init_visibility_helpers()
        self._refresh_container_choices()
        self.status_var.trace_add("write", lambda *_: self._on_status_change())
        self.url_var.trace_add("write", lambda *_: self._on_url_change())
        self._update_controls_state()
        self.root.bind("<Configure>", self.logs.on_root_configure, add=True)
        self.root.bind("<Configure>", self.queue_panel.on_root_configure, add=True)
        self.logs.on_root_configure(tk.Event())
        self.queue_panel.on_root_configure(tk.Event())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _cancel_after(self, attr_name: str, obj: object | None = None) -> None:
        target = obj if obj is not None else self
        after_id = getattr(target, attr_name, None)
        if not after_id:
            setattr(target, attr_name, None)
            return
        try:
            self.root.after_cancel(after_id)
        except Exception:
            pass
        setattr(target, attr_name, None)

    def _init_visibility_helpers(self) -> None:
        # Cache grid info for widgets we may hide/show.
        self._widget_grid_info = {}
        for w in [
            self.mixed_prompt_label,
            self.mixed_prompt_frame,
            self.playlist_label,
            self.playlist_frame,
            self.container_label,
            self.container_combo,
            self.codec_label,
            self.codec_combo,
            self.convert_mp4_inline_label,
            self.convert_mp4_check,
            self.format_label,
            self.format_combo,
            self.progress_item_label,
            self.progress_item_value,
        ]:
            self._widget_grid_info[w] = w.grid_info()

        self._set_playlist_ui(False)
        self._set_mixed_prompt_ui(False)

    def _set_combobox_enabled(self, combo: ttk.Combobox, enabled: bool) -> None:
        combo.configure(state="readonly" if enabled else "disabled")

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

    def _set_widget_visible(self, widget: tk.Widget, show: bool) -> None:
        if show:
            if not widget.winfo_manager():
                info = self._widget_grid_info.get(widget) or {}
                widget.grid(**info)
            elif not widget.winfo_ismapped():
                widget.grid()
        else:
            try:
                widget.grid_remove()
            except Exception:
                pass

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            self.output_dir_var.set(chosen)

    def _on_status_change(self) -> None:
        value = (self.status_var.get() or "").strip()
        if not value or value == self._last_status_logged:
            return
        self._last_status_logged = value
        self._log(f"[status] {value}")

    def _paste_url(self) -> None:
        try:
            clip = self.root.clipboard_get()
        except Exception:
            clip = ""
        if clip:
            self.url_var.set(self._strip_url_whitespace(clip))
            self.status_var.set("URL pasted")
            # Force format fetch even if URL hasn't changed.
            self._on_url_change(force=True)
        else:
            self.status_var.set("Clipboard is empty")

    def _strip_url_whitespace(self, url: str) -> str:
        return re.sub(r"\s+", "", url or "")

    def _normalize_url_var(self) -> None:
        if self._normalizing_url:
            return
        current = self.url_var.get()
        normalized = self._strip_url_whitespace(current)
        if normalized == current:
            return
        self._normalizing_url = True
        try:
            self.url_var.set(normalized)
        finally:
            self._normalizing_url = False

    def _is_mixed_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
        except Exception:
            return False
        return bool(query.get("v")) and bool(query.get("list"))

    def _is_playlist_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
        except Exception:
            return False
        if parsed.path.startswith("/playlist") and query.get("list"):
            return True
        if query.get("list") and not query.get("v"):
            return True
        return False

    def _strip_list_param(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if "list" in query:
                query.pop("list", None)
            if "index" in query:
                query.pop("index", None)
            if "start" in query:
                query.pop("start", None)
            from urllib.parse import urlencode

            new_query = urlencode(query, doseq=True)
            return parsed._replace(query=new_query).geturl()
        except Exception:
            return url

    def _to_playlist_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            list_id = (query.get("list") or [None])[0]
            if not list_id:
                return url
            return parsed._replace(path="/playlist", query=f"list={list_id}").geturl()
        except Exception:
            return url

    def _set_mixed_prompt_ui(self, show: bool) -> None:
        self._mixed_prompt_active = show
        self._set_widget_visible(self.mixed_prompt_label, show)
        self._set_widget_visible(self.mixed_prompt_frame, show)

    def _show_mixed_prompt(self, url: str) -> None:
        self._pending_mixed_url = url
        self._set_mixed_prompt_ui(True)
        self._update_controls_state()

    def _hide_mixed_prompt(self) -> None:
        self._pending_mixed_url = ""
        self._set_mixed_prompt_ui(False)
        self._update_controls_state()

    def _log(self, message: str) -> None:
        self.logs.queue(message)

    def _on_mode_change(self) -> None:
        self._refresh_container_choices()
        self._apply_mode_formats()
        self._update_controls_state()

    def _queue_refresh(self) -> None:
        active_index = self.queue_index if self.queue_active else None
        self.queue_panel.refresh(self.queue_items, active_index=active_index)

    def _queue_remove_selected(self, indices: list[int]) -> None:
        if not indices:
            return
        removed = sorted(set(indices), reverse=True)
        for idx in removed:
            if 0 <= idx < len(self.queue_items):
                self.queue_items.pop(idx)
        if self.queue_active and self.queue_index is not None:
            for idx in removed:
                if idx < self.queue_index:
                    self.queue_index -= 1
            if self.queue_index >= len(self.queue_items):
                self.queue_index = max(0, len(self.queue_items) - 1)
        self._queue_refresh()
        self._update_controls_state()
        self._update_controls_state()

    def _queue_move_up(self, indices: list[int]) -> None:
        if not indices:
            return
        moved = False
        for idx in sorted(set(indices)):
            if idx <= 0 or idx >= len(self.queue_items):
                continue
            self.queue_items[idx - 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx - 1],
            )
            moved = True
        if moved:
            self._queue_refresh()

    def _queue_move_down(self, indices: list[int]) -> None:
        if not indices:
            return
        moved = False
        for idx in sorted(set(indices), reverse=True):
            if idx < 0 or idx >= len(self.queue_items) - 1:
                continue
            self.queue_items[idx + 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx + 1],
            )
            moved = True
        if moved:
            self._queue_refresh()

    def _queue_clear(self) -> None:
        if not self.queue_items:
            return
        self.queue_items.clear()
        self.queue_index = None
        self._queue_refresh()
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
        if url and self._is_mixed_url(url):
            self._show_mixed_prompt(url)
            return
        if url and self._is_playlist_url(url):
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
            self.formats.fetch_after_id = self.root.after(
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
        self.status_var.set("Fetching formats...")
        self.start_button.state(["disabled"])
        self.format_combo.configure(state="disabled")
        self.convert_to_mp4_var.set(False)
        threading.Thread(
            target=self._fetch_formats_worker, args=(url,), daemon=True
        ).start()

    def _fetch_formats_worker(self, url: str) -> None:
        try:
            info = helpers.fetch_info(url)
        except Exception as exc:  # show error in UI
            self._log(f"Could not fetch formats: {exc}")
            self.root.after(0, lambda: self._set_formats([], error=True))
            return
        entries = info.get("entries")
        is_playlist = info.get("_type") == "playlist" or entries is not None
        formats = formats_mod.formats_from_info(info)
        self.root.after(0, lambda: self._set_formats(formats, is_playlist=is_playlist))

    def _set_formats(
        self,
        formats: list[dict],
        error: bool = False,
        is_playlist: bool = False,
    ) -> None:
        self.formats.is_fetching = False
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
                # self.status_var.set("Formats failed to load. Check URL or network.")
            self.formats.video_labels = []
            self.formats.video_lookup = {}
            self.formats.audio_labels = []
            self.formats.audio_lookup = {}
            self._apply_mode_formats()
            # if not error:
            # self.status_var.set("No formats found")
            self._update_controls_state()
            return

        video_formats, audio_formats = helpers.split_and_filter_formats(formats)
        video_labeled = helpers.build_labeled_formats(video_formats)
        audio_labeled = helpers.build_labeled_formats(audio_formats)
        # Add top-level best options.
        audio_labeled.insert(
            0,
            (
                "Best audio only",
                {"custom_format": "bestaudio/best", "is_audio_only": True},
            ),
        )

        self.formats.video_labels = [label for label, _ in video_labeled]
        self.formats.video_lookup = {label: fmt for label, fmt in video_labeled}
        self.formats.audio_labels = [label for label, _ in audio_labeled]
        self.formats.audio_lookup = {label: fmt for label, fmt in audio_labeled}
        # Cache processed formats for this URL.
        self.formats.cache[self.formats.last_fetched_url] = {
            "video_labels": self.formats.video_labels,
            "video_lookup": self.formats.video_lookup,
            "audio_labels": self.formats.audio_labels,
            "audio_lookup": self.formats.audio_lookup,
        }

        # Require user to pick a container after formats load.
        self._reset_format_selections()
        self._apply_mode_formats()
        self.formats.last_fetch_failed = False
        self.status_var.set("Formats loaded")
        self._update_controls_state()

    def _load_cached_formats(self, url: str, cached: dict) -> None:
        self.formats.last_fetched_url = url
        self.formats.video_labels = cached.get("video_labels", [])
        self.formats.video_lookup = cached.get("video_lookup", {})
        self.formats.audio_labels = cached.get("audio_labels", [])
        self.formats.audio_lookup = cached.get("audio_lookup", {})
        self._reset_format_selections()
        self._apply_mode_formats()
        self.status_var.set("Formats loaded (cached)")
        self._update_controls_state()

    def _apply_mode_formats(self) -> None:
        mode = self.mode_var.get()
        if mode not in {"audio", "video"}:
            self.formats.filtered_labels = []
            self.formats.filtered_lookup = {}
            self.format_combo.configure(values=[])
            self.format_var.set("")
            self._update_controls_state()
            return

        if mode == "audio":
            labels = self.formats.audio_labels
            lookup = self.formats.audio_lookup
            # For audio-only, container selection controls output post-processing, not
            # which source formats are shown in the dropdown.
            if not labels:
                labels = ["Best audio only"]
                lookup = {
                    "Best audio only": {
                        "custom_format": "bestaudio/best",
                        "is_audio_only": True,
                    }
                }
            self.formats.filtered_labels = list(labels)
            self.formats.filtered_lookup = {label: lookup.get(label) or {} for label in labels}
            self.format_combo.configure(values=self.formats.filtered_labels)
            if self.formats.filtered_labels:
                if self.format_var.get() not in self.formats.filtered_labels:
                    self.format_var.set("")
            else:
                self.format_var.set("")
            self._update_controls_state()
            return
        else:
            labels = self.formats.video_labels
            lookup = self.formats.video_lookup

        filter_val = self.format_filter_var.get()
        codec_raw = self.codec_filter_var.get()
        codec_val = codec_raw.lower()
        if filter_val not in {"mp4", "webm"} or not codec_val:
            self.formats.filtered_labels = []
            self.formats.filtered_lookup = {}
            self.format_combo.configure(values=[])
            self.format_var.set("")
            self._update_controls_state()
            return
        filtered_labels: list[str] = []
        filtered_lookup: dict[str, dict] = {}

        def apply_filters(allow_any_codec: bool) -> None:
            filtered_labels.clear()
            filtered_lookup.clear()
            if filter_val in {"mp4", "webm"} and (allow_any_codec or codec_val):
                for label in labels:
                    info = lookup.get(label) or {}
                    if info.get("custom_format"):
                        filtered_labels.append(label)
                        filtered_lookup[label] = info
                        continue
                    ext = (info.get("ext") or "").lower()
                    if filter_val == "mp4" and ext != "mp4":
                        continue
                    if filter_val == "webm" and ext != "webm":
                        continue
                    if not allow_any_codec and codec_val != "any":
                        vcodec = (info.get("vcodec") or "").lower()
                        if codec_val.startswith("avc1") and "avc1" not in vcodec:
                            continue
                        if codec_val.startswith("av01") and "av01" not in vcodec:
                            continue
                    filtered_labels.append(label)
                    filtered_lookup[label] = info

        apply_filters(allow_any_codec=False)
        if (
            self.mode_var.get() == "video"
            and filter_val in {"mp4", "webm"}
            and codec_val
            and not filtered_labels
        ):
            # If codec filter wipes all video entries, fall back to any codec for this container.
            msg = "Chosen codec not available for this container; showing all formats in container"
            self.status_var.set(msg)
            notice_key = (self.mode_var.get(), filter_val, codec_raw)
            if notice_key != self.formats.last_codec_fallback_notice:
                self.formats.last_codec_fallback_notice = notice_key
                self._log(f"[info] {msg}")
            apply_filters(allow_any_codec=True)
        if not filtered_labels:
            # Add a fall-back "best" option if no exact matches exist.
            filtered_labels.append("Best available")
            filtered_lookup["Best available"] = {"custom_format": "bestvideo+bestaudio/best"}

        self.formats.filtered_labels = filtered_labels
        self.formats.filtered_lookup = filtered_lookup
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
        is_audio_mode = mode == "audio"
        is_video_mode = mode == "video"
        mode_chosen = is_audio_mode or is_video_mode
        container_value = self.format_filter_var.get()
        if is_audio_mode and container_value not in AUDIO_CONTAINERS:
            self.format_filter_var.set(AUDIO_CONTAINERS[0])
            container_value = self.format_filter_var.get()
        filter_chosen = (
            container_value in AUDIO_CONTAINERS if is_audio_mode else container_value in VIDEO_CONTAINERS
        )
        codec_chosen = bool(self.codec_filter_var.get())
        format_available = bool(self.formats.filtered_labels)
        format_selected = bool(self.format_var.get())
        queue_ready = bool(self.queue_items)
        base_ready = (
            not self.formats.is_fetching
            and not self.is_downloading
            and mode_chosen
        )
        input_ready = base_ready and (url_present or queue_ready)
        single_ready = base_ready and url_present and has_formats_data

        # Keep all options visible; disable when not usable.
        self._configure_combobox(
            self.container_label,
            self.container_combo,
            show=True,
            enabled=input_ready,
        )

        self._configure_combobox(
            self.codec_label,
            self.codec_combo,
            show=is_video_mode,
            enabled=is_video_mode and input_ready and filter_chosen,
        )

        # Convert checkbox only relevant when container is webm.
        is_webm = container_value == "webm"
        show_convert = is_webm
        self._set_widget_visible(self.convert_mp4_inline_label, show_convert)
        self._set_widget_visible(self.convert_mp4_check, show_convert)
        convert_enabled = input_ready and filter_chosen and is_webm
        if convert_enabled:
            self.convert_mp4_check.state(["!disabled"])
        else:
            self.convert_to_mp4_var.set(False)
            self.convert_mp4_check.state(["disabled"])

        self._configure_combobox(
            self.format_label,
            self.format_combo,
            show=True,
            enabled=(
                single_ready
                and filter_chosen
                and (format_available)
                and (True if is_audio_mode else codec_chosen)
            ),
        )

        # Main actions
        can_start_single = (
            single_ready
            and filter_chosen
            and format_selected
            and (is_audio_mode or codec_chosen)
            and not self._mixed_prompt_active
        )
        is_playlist_url = self.is_playlist or (url_present and self._is_playlist_url(self.url_var.get()))
        can_add_queue = can_start_single and not is_playlist_url
        can_start_queue = (
            queue_ready
            and not self.is_downloading
            and not self._mixed_prompt_active
        )
        if can_start_single:
            self.start_button.state(["!disabled"])
        else:
            self.start_button.state(["disabled"])
        if can_add_queue:
            self.add_queue_button.state(["!disabled"])
        else:
            self.add_queue_button.state(["disabled"])
        if can_start_queue:
            self.start_queue_button.state(["!disabled"])
        else:
            self.start_queue_button.state(["disabled"])

        # Cancel button (visible always; only enabled while a download is running).
        can_cancel = self.is_downloading and not self._cancel_requested
        if can_cancel:
            self.cancel_button.state(["!disabled"])
        else:
            self.cancel_button.state(["disabled"])

        playlist_items_enabled = self.playlist_enabled_var.get() and not self.is_downloading
        if playlist_items_enabled:
            self.playlist_items_entry.configure(state="normal")
        else:
            self.playlist_items_entry.configure(state="disabled")

        if url_present and not self.is_downloading and has_formats_data:
            self.video_mode_radio.state(["!disabled"])
            self.audio_mode_radio.state(["!disabled"])
        else:
            self.video_mode_radio.state(["disabled"])
            self.audio_mode_radio.state(["disabled"])

        self._set_widget_visible(self.progress_item_label, self._show_progress_item)
        self._set_widget_visible(self.progress_item_value, self._show_progress_item)

        if self.is_downloading:
            self.browse_button.state(["disabled"])
            self.paste_button.state(["disabled"])
        else:
            self.browse_button.state(["!disabled"])
            self.paste_button.state(["!disabled"])

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
        resolved_url = self._to_playlist_url(self._pending_mixed_url)
        self._hide_mixed_prompt()
        if resolved_url and resolved_url != self.url_var.get():
            self.url_var.set(resolved_url)

    def _on_mixed_choose_video(self) -> None:
        if not self._pending_mixed_url:
            return
        resolved_url = self._strip_list_param(self._pending_mixed_url)
        self._hide_mixed_prompt()
        if resolved_url and resolved_url != self.url_var.get():
            self.url_var.set(resolved_url)

    def _reset_progress_summary(self) -> None:
        self.progress_pct_var.set("—")
        self.progress_speed_var.set("—")
        self.progress_eta_var.set("—")
        self.progress_item_var.set("—")
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self._cancel_after("_progress_anim_after_id")

    def _on_progress_update(self, update: dict) -> None:
        status = update.get("status")
        if status == "downloading":
            pct = update.get("percent")
            if isinstance(pct, (int, float)):
                self._progress_pct_target = float(max(0.0, min(100.0, pct)))
                if self._progress_anim_after_id is None:
                    self._progress_anim_tick()
            speed = update.get("speed")
            eta = update.get("eta")
            if isinstance(speed, str):
                self.progress_speed_var.set(speed or "—")
            # Hold last known ETA if the new value is blank/unknown.
            if isinstance(eta, str):
                eta_clean = eta.strip()
                if eta_clean and eta_clean != "—":
                    self.progress_eta_var.set(eta_clean)
        elif status == "item":
            if not self._show_progress_item:
                return
            item = update.get("item")
            if isinstance(item, str) and item.strip():
                self.progress_item_var.set(item.strip())
        elif status == "finished":
            self._progress_pct_target = 100.0
            if self._progress_anim_after_id is None:
                self._progress_anim_tick()
        elif status == "cancelled":
            self._progress_pct_target = 0.0

    def _progress_anim_tick(self) -> None:
        ease = 0.22
        delta = self._progress_pct_target - self._progress_pct_display
        if abs(delta) < 0.05:
            self._progress_pct_display = self._progress_pct_target
            self.progress_pct_var.set(f"{self._progress_pct_display:.1f}%")
            self._progress_anim_after_id = None
            return
        self._progress_pct_display += delta * ease
        self.progress_pct_var.set(f"{self._progress_pct_display:.1f}%")
        self._progress_anim_after_id = self.root.after(
            PROGRESS_ANIM_MS, self._progress_anim_tick
        )

    def _on_start(self) -> None:
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please paste a video URL to download.")
            return
        if not self.formats.filtered_lookup:
            messagebox.showerror(
                "Formats unavailable", "Formats have not been loaded yet."
            )
            return
        output_dir = Path(self.output_dir_var.get()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        self.is_downloading = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self._show_progress_item = bool(self.playlist_enabled_var.get() and self.is_playlist)
        self.simple_state_var.set("Downloading")
        self.status_var.set("Downloading...")
        self.logs.clear()
        self._reset_progress_summary()
        self._update_controls_state()
        self.download_thread = threading.Thread(
            target=self._run_download,
            kwargs={
                "url": url,
                "output_dir": output_dir,
                "fmt_label": self.format_var.get(),
            },
            daemon=True,
        )
        self.download_thread.start()

    def _on_add_to_queue(self) -> None:
        if self.is_downloading:
            return
        url = self._strip_url_whitespace(self.url_var.get())
        if not url:
            self.status_var.set("Queue add failed: missing URL")
            self._log("[queue] missing URL")
            return
        if self.is_playlist or self._is_playlist_url(url):
            self.status_var.set("Queue add failed: playlists not allowed")
            self._log("[queue] playlists cannot be added (use single video URLs)")
            return
        if not self.formats.filtered_lookup:
            self.status_var.set("Queue add failed: formats not loaded")
            self._log("[queue] formats not loaded")
            return
        settings = self._capture_queue_settings()
        mode = settings.get("mode")
        if mode not in {"audio", "video"}:
            self.status_var.set("Queue add failed: choose audio or video mode first")
            self._log("[queue] missing mode (audio/video)")
            return
        if mode == "video" and not settings.get("codec_filter"):
            self.status_var.set("Queue add failed: choose a codec first")
            self._log("[queue] missing codec")
            return
        if not settings.get("format_filter"):
            self.status_var.set("Queue add failed: choose a container first")
            self._log("[queue] missing container")
            return
        if not settings.get("format_label"):
            self.status_var.set("Queue add failed: choose a format first")
            self._log("[queue] missing format")
            return

        self.queue_items.append({"url": url, "settings": settings})
        self._queue_refresh()
        self._update_controls_state()

    def _on_start_queue(self) -> None:
        self._start_queue_download()

    def _on_cancel(self) -> None:
        if not self.is_downloading or self._cancel_requested:
            return
        self._cancel_requested = True
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.simple_state_var.set("Cancelling…")
        self.status_var.set("Cancelling download…")
        self._log("[cancel] Cancellation requested.")
        self._update_controls_state()

    def _capture_queue_settings(self) -> dict:
        return {
            "mode": self.mode_var.get(),
            "format_filter": self.format_filter_var.get(),
            "codec_filter": self.codec_filter_var.get(),
            "convert_to_mp4": bool(self.convert_to_mp4_var.get()),
            "format_label": self.format_var.get(),
            "output_dir": self.output_dir_var.get(),
            "playlist_items": (self.playlist_items_var.get() or "").strip(),
        }

    def _resolve_format_for_url(self, url: str, settings: dict) -> dict:
        info = helpers.fetch_info(url)
        formats = formats_mod.formats_from_info(info)
        if not formats:
            raise RuntimeError("No formats found for URL.")

        mode = settings.get("mode")
        format_filter = settings.get("format_filter")
        codec_filter = settings.get("codec_filter") or ""
        desired_label = settings.get("format_label") or ""

        video_formats, audio_formats = helpers.split_and_filter_formats(formats)
        video_labeled = helpers.build_labeled_formats(video_formats)
        audio_labeled = helpers.build_labeled_formats(audio_formats)
        audio_labeled.insert(
            0,
            (
                "Best audio only",
                {"custom_format": "bestaudio/best", "is_audio_only": True},
            ),
        )

        if mode == "audio":
            labels = [label for label, _ in audio_labeled]
            lookup = {label: fmt for label, fmt in audio_labeled}
            if desired_label in labels:
                label = desired_label
            elif labels:
                label = labels[0]
                if desired_label:
                    self._log(
                        f"[queue] format '{desired_label}' missing; using '{label}'"
                    )
            else:
                label = "Best audio only"
            return {
                "fmt_label": label,
                "fmt_info": lookup.get(label) or {"custom_format": "bestaudio/best"},
                "format_filter": format_filter,
                "is_playlist": info.get("_type") == "playlist" or info.get("entries") is not None,
                "title": info.get("title") or url,
            }

        labels = [label for label, _ in video_labeled]
        lookup = {label: fmt for label, fmt in video_labeled}

        filtered_labels: list[str] = []
        filtered_lookup: dict[str, dict] = {}

        def apply_filters(allow_any_codec: bool) -> None:
            filtered_labels.clear()
            filtered_lookup.clear()
            if format_filter in {"mp4", "webm"} and (allow_any_codec or codec_filter):
                for label in labels:
                    info = lookup.get(label) or {}
                    if info.get("custom_format"):
                        filtered_labels.append(label)
                        filtered_lookup[label] = info
                        continue
                    ext = (info.get("ext") or "").lower()
                    if format_filter == "mp4" and ext != "mp4":
                        continue
                    if format_filter == "webm" and ext != "webm":
                        continue
                    if not allow_any_codec and codec_filter.lower() != "any":
                        vcodec = (info.get("vcodec") or "").lower()
                        if codec_filter.lower().startswith("avc1") and "avc1" not in vcodec:
                            continue
                        if codec_filter.lower().startswith("av01") and "av01" not in vcodec:
                            continue
                    filtered_labels.append(label)
                    filtered_lookup[label] = info

        apply_filters(allow_any_codec=False)
        if (
            format_filter in {"mp4", "webm"}
            and codec_filter
            and not filtered_labels
        ):
            self._log(
                "[queue] chosen codec not available; using any codec for container"
            )
            apply_filters(allow_any_codec=True)

        if not filtered_labels:
            filtered_labels.append("Best available")
            filtered_lookup["Best available"] = {
                "custom_format": "bestvideo+bestaudio/best"
            }

        if desired_label in filtered_labels:
            label = desired_label
        else:
            label = filtered_labels[0]
            if desired_label:
                self._log(
                    f"[queue] format '{desired_label}' missing; using '{label}'"
                )

        return {
            "fmt_label": label,
            "fmt_info": filtered_lookup.get(label) or {"custom_format": "best"},
            "format_filter": format_filter,
            "is_playlist": info.get("_type") == "playlist" or info.get("entries") is not None,
            "title": info.get("title") or url,
        }

    def _start_queue_download(self) -> None:
        if self.is_downloading or not self.queue_items:
            return
        for idx, item in enumerate(self.queue_items, start=1):
            settings = (item or {}).get("settings") or {}
            mode = settings.get("mode")
            if mode not in {"audio", "video"}:
                messagebox.showerror(
                    "Missing settings",
                    f"Queue item {idx} is missing audio/video mode.",
                )
                return
            if mode == "video" and not settings.get("codec_filter"):
                messagebox.showerror(
                    "Missing settings",
                    f"Queue item {idx} is missing a codec choice.",
                )
                return
            if not settings.get("format_filter"):
                messagebox.showerror(
                    "Missing settings",
                    f"Queue item {idx} is missing a container choice.",
                )
                return
            if not settings.get("format_label"):
                messagebox.showerror(
                    "Missing settings",
                    f"Queue item {idx} is missing a format choice.",
                )
                return

        self.queue_active = True
        self.queue_index = 0
        self.queue_settings = None
        self.is_downloading = True
        self._show_progress_item = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self.simple_state_var.set("Downloading queue")
        self.status_var.set("Downloading queue...")
        self.logs.clear()
        self._reset_progress_summary()
        self._update_controls_state()
        self._queue_refresh()
        self._start_next_queue_item()

    def _start_next_queue_item(self) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        if self.queue_index >= len(self.queue_items):
            self._finish_queue()
            return
        url = self.queue_items[self.queue_index].get("url", "")
        settings = self.queue_items[self.queue_index].get("settings") or {}
        if not url:
            self.queue_index += 1
            self._start_next_queue_item()
            return
        total = len(self.queue_items)
        self._log(f"[queue] item {self.queue_index + 1}/{total} {url}")
        self._queue_refresh()
        self.download_thread = threading.Thread(
            target=self._run_queue_download,
            kwargs={
                "url": url,
                "settings": settings,
                "index": self.queue_index + 1,
                "total": total,
            },
            daemon=True,
        )
        self.download_thread.start()

    def _run_queue_download(self, url: str, settings: dict, index: int, total: int) -> None:
        try:
            resolved = self._resolve_format_for_url(url, settings)
            title = resolved.get("title") or url
            item_text = f"{index}/{total} {title}"
            self.root.after(0, lambda: self.progress_item_var.set(item_text))
            output_dir = Path(settings.get("output_dir") or self.output_dir_var.get()).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            playlist_enabled = bool(resolved.get("is_playlist"))
            playlist_items = settings.get("playlist_items") or None
            if playlist_enabled:
                self._log(
                    f"[playlist] enabled=1 items={playlist_items or 'none'}"
                )
            download.run_download(
                url=url,
                output_dir=output_dir,
                fmt_info=resolved["fmt_info"],
                fmt_label=resolved["fmt_label"],
                format_filter=resolved["format_filter"],
                convert_to_mp4=bool(settings.get("convert_to_mp4")),
                playlist_enabled=playlist_enabled,
                playlist_items=playlist_items,
                cancel_event=self._cancel_event,
                log=self._log,
                update_progress=lambda u: self.root.after(
                    0, lambda: self._on_progress_update(u)
                ),
            )
        except Exception as exc:
            self._log(f"[queue] failed: {exc}")
        finally:
            self.root.after(0, self._on_queue_item_finish)

    def _on_queue_item_finish(self) -> None:
        if not self.queue_active or self.queue_index is None:
            self._finish_queue()
            return
        if self._cancel_requested:
            self._log("[queue] cancelled")
            self._finish_queue()
            return
        self.queue_index += 1
        if self.queue_index >= len(self.queue_items):
            self._finish_queue()
            return
        self._reset_progress_summary()
        self._start_next_queue_item()

    def _finish_queue(self) -> None:
        self.queue_active = False
        self.queue_index = None
        self.queue_settings = None
        self.is_downloading = False
        self._show_progress_item = False
        self._cancel_requested = False
        self._cancel_event = None
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self._reset_progress_summary()
        self._update_controls_state()
        self._queue_refresh()

    def _run_download(self, url: str, output_dir: Path, fmt_label: str) -> None:
        fmt_info = self.formats.filtered_lookup.get(fmt_label)
        format_filter = self.format_filter_var.get()
        playlist_enabled = bool(self.playlist_enabled_var.get())
        playlist_items_raw = (self.playlist_items_var.get() or "").strip()
        playlist_items = re.sub(r"\s+", "", playlist_items_raw)
        if playlist_items_raw and playlist_items != playlist_items_raw:
            self._log("[info] Playlist items normalized (spaces removed).")
        if playlist_enabled:
            self._log(f"[playlist] enabled=1 items={playlist_items or 'none'}")

        download.run_download(
            url=url,
            output_dir=output_dir,
            fmt_info=fmt_info,
            fmt_label=fmt_label,
            format_filter=format_filter,
            convert_to_mp4=self.convert_to_mp4_var.get(),
            playlist_enabled=playlist_enabled,
            playlist_items=playlist_items or None,
            cancel_event=self._cancel_event,
            log=self._log,
            update_progress=lambda u: self.root.after(
                0, lambda: self._on_progress_update(u)
            ),
        )
        self.root.after(0, self._on_finish)

    def _on_finish(self) -> None:
        self.is_downloading = False
        self._cancel_requested = False
        self._cancel_event = None
        self._show_progress_item = False
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self._reset_progress_summary()
        self._update_controls_state()

    def _on_close(self) -> None:
        if self.is_downloading:
            if not messagebox.askokcancel(
                "Download running", "A download is in progress. Quit anyway?"
            ):
                return
        self._cancel_after("fetch_after_id", self.formats)
        self._cancel_after("_progress_anim_after_id")
        self.logs.shutdown()
        self.queue_panel.shutdown()
        self.root.destroy()


def main() -> None:
    YtDlpGui().root.mainloop()


if __name__ == "__main__":
    main()
