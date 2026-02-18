import threading
import queue
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections.abc import Callable

# Timing/layout constants (keep UI behavior consistent and readable).
FETCH_DEBOUNCE_MS = 600
PROGRESS_ANIM_MS = 33
UI_EVENT_POLL_MS = 25
UI_EVENT_MAX_PER_TICK = 200
FORMAT_CACHE_MAX_ENTRIES = 100
HISTORY_MAX_ENTRIES = 250
WINDOW_MIN_WIDTH = 720
WINDOW_MIN_HEIGHT = 550
WINDOW_SCREEN_MARGIN = 8

VIDEO_CONTAINERS = ("mp4", "webm")
AUDIO_CONTAINERS = ("m4a", "mp3", "opus", "wav", "flac")

from . import (
    diagnostics,
    download,
    format_pipeline,
    formats as formats_mod,
    history_store,
    ui,
    yt_dlp_helpers as helpers,
    tooling,
)
from .core import format_selection as core_format_selection
from .core import download_plan as core_download_plan
from .core import options as core_options
from .core import queue_logic as core_queue_logic
from .core import urls as core_urls
from .shared_types import DownloadOptions, HistoryItem, QueueItem, QueueSettings
from .state import FormatState


class YtDlpGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("yt-dlp-gui")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._progress_anim_after_id: str | None = None
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self.download_thread: threading.Thread | None = None
        self.is_downloading = False
        self._cancel_event: threading.Event | None = None
        self._cancel_requested = False
        self._closing = False
        self.formats = FormatState()
        self._normalizing_url = False
        self.is_playlist = False
        self._mixed_prompt_active = False
        self._pending_mixed_url = ""
        self.queue_items: list[QueueItem] = []
        self.queue_active = False
        self.queue_index: int | None = None
        self.queue_settings: QueueSettings | None = None
        self._queue_failed_items = 0
        self.download_history: list[HistoryItem] = []
        self._history_seen_paths: set[str] = set()

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
        self.custom_filename_var = tk.StringVar(value="")
        self.preview_title_var = tk.StringVar(value="")
        self.subtitle_languages_var = tk.StringVar(value="")
        self.write_subtitles_var = tk.BooleanVar(value=False)
        self.embed_subtitles_var = tk.BooleanVar(value=False)
        self.audio_language_var = tk.StringVar(value="")
        self.network_timeout_var = tk.StringVar(
            value=str(download.YDL_SOCKET_TIMEOUT_SECONDS)
        )
        self.network_retries_var = tk.StringVar(value=str(download.YDL_ATTEMPT_RETRIES))
        self.retry_backoff_var = tk.StringVar(
            value=str(download.YDL_RETRY_BACKOFF_SECONDS)
        )
        self.status_var = tk.StringVar(value="Idle")
        self._last_status_logged = self.status_var.get()
        self.simple_state_var = tk.StringVar(value="Idle")
        self.ui_layout_var = tk.StringVar(value="Simple")
        self.progress_pct_var = tk.StringVar(value="—")
        self.progress_speed_var = tk.StringVar(value="—")
        self.progress_eta_var = tk.StringVar(value="—")
        self.progress_item_var = tk.StringVar(value="—")
        self._show_progress_item = False
        self._ui_event_queue: "queue.Queue[tuple[Callable, tuple, dict]]" = queue.Queue()
        self._ui_event_after_id: str | None = None
        self._fetch_request_seq = 0
        self._active_fetch_request_id: int | None = None

        self.logs = ui.build_ui(self)
        self._set_audio_language_values([])
        # Ensure logs are empty when the app launches.
        self.logs.clear()
        self.queue_panel.refresh(self.queue_items)
        self._init_visibility_helpers()
        self._refresh_container_choices()
        self.status_var.trace_add("write", lambda *_: self._on_status_change())
        self.url_var.trace_add("write", lambda *_: self._on_url_change())
        self.write_subtitles_var.trace_add(
            "write", lambda *_: self._update_controls_state()
        )
        self.mode_var.trace_add("write", lambda *_: self._update_controls_state())
        self._refresh_history_panel()
        self._update_controls_state()
        self._fit_window_to_content()
        self.root.bind("<Configure>", self.logs.on_root_configure, add=True)
        self.root.bind("<Configure>", self.settings_panel.on_root_configure, add=True)
        self.root.bind("<Configure>", self.queue_panel.on_root_configure, add=True)
        self.root.bind("<Configure>", self.history_panel.on_root_configure, add=True)
        self.logs.on_root_configure(tk.Event())
        self.settings_panel.on_root_configure(tk.Event())
        self.queue_panel.on_root_configure(tk.Event())
        self.history_panel.on_root_configure(tk.Event())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ui_event_after_id = self._safe_after(UI_EVENT_POLL_MS, self._drain_ui_events)
        self._safe_after(50, self._warn_missing_dependencies)

    def _fit_window_to_content(self) -> None:
        try:
            self.root.update_idletasks()
            req_w = int(self.root.winfo_reqwidth())
            req_h = int(self.root.winfo_reqheight())
            screen_w = int(self.root.winfo_screenwidth())
            screen_h = int(self.root.winfo_screenheight())
        except (tk.TclError, RuntimeError, ValueError):
            return
        max_w = max(WINDOW_MIN_WIDTH, screen_w - WINDOW_SCREEN_MARGIN)
        max_h = max(WINDOW_MIN_HEIGHT, screen_h - WINDOW_SCREEN_MARGIN)
        target_w = max(WINDOW_MIN_WIDTH, min(req_w, max_w))
        target_h = max(WINDOW_MIN_HEIGHT, min(req_h, max_h))
        try:
            self.root.geometry(f"{target_w}x{target_h}")
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _cancel_after(self, attr_name: str, obj: object | None = None) -> None:
        target = obj if obj is not None else self
        after_id = getattr(target, attr_name, None)
        if not after_id:
            setattr(target, attr_name, None)
            return
        try:
            self.root.after_cancel(after_id)
        except (tk.TclError, ValueError, RuntimeError):
            pass
        setattr(target, attr_name, None)

    def _safe_after(self, delay_ms: int, callback: callable) -> str | None:
        if self._closing:
            return None
        try:
            if not self.root.winfo_exists():
                return None
        except (tk.TclError, RuntimeError):
            return None
        try:
            return self.root.after(delay_ms, callback)
        except (tk.TclError, RuntimeError):
            return None

    def _post_ui(self, callback: Callable, *args: object, **kwargs: object) -> None:
        if self._closing:
            return
        self._ui_event_queue.put((callback, args, kwargs))

    def _drain_ui_events(self) -> None:
        self._ui_event_after_id = None
        if self._closing:
            return
        processed = 0
        try:
            while processed < UI_EVENT_MAX_PER_TICK:
                callback, args, kwargs = self._ui_event_queue.get_nowait()
                try:
                    callback(*args, **kwargs)
                except Exception as exc:
                    self._log(f"[ui] callback failed: {exc}")
                processed += 1
        except queue.Empty:
            pass
        next_delay = 0 if not self._ui_event_queue.empty() else UI_EVENT_POLL_MS
        self._ui_event_after_id = self._safe_after(next_delay, self._drain_ui_events)

    def _cache_formats_entry(self, url: str, entry: dict) -> None:
        if not url:
            return
        snapshot = {
            "video_labels": list(entry.get("video_labels", [])),
            "video_lookup": dict(entry.get("video_lookup", {})),
            "audio_labels": list(entry.get("audio_labels", [])),
            "audio_lookup": dict(entry.get("audio_lookup", {})),
            "audio_languages": list(entry.get("audio_languages", [])),
            "preview_title": str(entry.get("preview_title", "")),
        }
        cache = self.formats.cache
        if url in cache:
            cache.pop(url, None)
        cache[url] = snapshot
        while len(cache) > FORMAT_CACHE_MAX_ENTRIES:
            oldest = next(iter(cache))
            cache.pop(oldest, None)

    def _touch_cached_url(self, url: str) -> None:
        if not url:
            return
        cache = self.formats.cache
        entry = cache.pop(url, None)
        if entry is None:
            return
        cache[url] = entry

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
            self.subtitle_languages_label,
            self.subtitle_languages_entry,
            self.subtitle_options_label,
            self.write_subtitles_check,
            self.embed_subtitles_check,
            self.progress_frame,
            self.progress_item_label,
            self.progress_item_value,
        ]:
            self._widget_grid_info[w] = w.grid_info()

        self._set_playlist_ui(False)
        self._set_mixed_prompt_ui(False)

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

    def _ensure_output_dir(self, output_dir_raw: str) -> Path | None:
        output_dir = Path(output_dir_raw).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._log(f"[error] output folder unavailable: {output_dir} ({exc})")
            self.status_var.set("Output folder unavailable")
            messagebox.showerror(
                "Output folder unavailable",
                "Could not create or access the output folder:\n"
                f"{output_dir}\n\n"
                f"{exc}",
            )
            return None
        return output_dir

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
        return core_urls.strip_url_whitespace(url)

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
        return core_urls.is_mixed_url(url)

    def _is_playlist_url(self, url: str) -> bool:
        return core_urls.is_playlist_url(url)

    def _strip_list_param(self, url: str) -> str:
        return core_urls.strip_list_param(url)

    def _to_playlist_url(self, url: str) -> str:
        return core_urls.to_playlist_url(url)

    def _open_path(self, path: Path) -> bool:
        target = path.expanduser()
        try:
            if os.name == "nt" and hasattr(os, "startfile"):
                os.startfile(str(target))  # type: ignore[attr-defined]
                return True
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
                return True
            subprocess.Popen(["xdg-open", str(target)])
            return True
        except (OSError, ValueError, RuntimeError) as exc:
            self._log(f"[history] Failed to open path: {target} ({exc})")
            return False

    def _selected_history_item(self) -> dict[str, str] | None:
        panel = getattr(self, "history_panel", None)
        if panel is None:
            return None
        try:
            idx = panel.get_selected_index()
        except (tk.TclError, AttributeError, TypeError, ValueError):
            return None
        history = getattr(self, "download_history", [])
        if idx is None:
            return None
        if idx < 0 or idx >= len(history):
            return None
        return history[idx]

    def _update_history_buttons_state(self) -> None:
        # HistorySidebar owns the action-button state.
        return

    def _refresh_history_panel(self) -> None:
        panel = getattr(self, "history_panel", None)
        if panel is None:
            return
        panel.refresh(self.download_history)

    def _record_download_output(self, output_path: Path, source_url: str = "") -> None:
        if not output_path:
            return
        normalized = history_store.normalize_output_path(output_path)
        if not normalized:
            return
        history_store.upsert_history_entry(
            self.download_history,
            self._history_seen_paths,
            normalized_path=normalized,
            source_url=source_url,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            max_entries=HISTORY_MAX_ENTRIES,
        )
        self._refresh_history_panel()

    def _open_selected_history_file(self, _event: tk.Event | None = None) -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        if self._open_path(path):
            self.status_var.set("Opened downloaded file")

    def _open_selected_history_folder(self, _event: tk.Event | None = None) -> None:
        item = self._selected_history_item()
        if item is None:
            return
        path_raw = str(item.get("path", "")).strip()
        if not path_raw:
            return
        path = Path(path_raw)
        if self._open_path(path.parent):
            self.status_var.set("Opened download folder")

    def _clear_download_history(self) -> None:
        if not self.download_history:
            return
        self.download_history.clear()
        self._history_seen_paths.clear()
        self._refresh_history_panel()
        self.status_var.set("Download history cleared")

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

    def _warn_missing_dependencies(self) -> None:
        missing = tooling.missing_required_binaries()
        if not missing:
            return

        missing_txt = ", ".join(missing)
        self._log(f"[deps] missing binaries: {missing_txt}")
        messagebox.showwarning(
            "Missing dependencies",
            "Some required binaries are missing:\n"
            f"{missing_txt}\n\n"
            "Please install required dependencies before using this app.\n"
            "See README.md for setup instructions.",
        )

    def _on_mode_change(self) -> None:
        self._refresh_container_choices()
        self._apply_mode_formats()
        self._update_controls_state()

    def _queue_refresh(self) -> None:
        active_index = self.queue_index if self.queue_active else None
        self.queue_panel.refresh(
            self.queue_items,
            active_index=active_index,
            editable=not self.queue_active,
        )

    def _queue_remove_selected(self, indices: list[int]) -> None:
        if self.queue_active:
            return
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

    def _queue_move_up(self, indices: list[int]) -> None:
        if self.queue_active:
            return
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
        if self.queue_active:
            return
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
        if self.queue_active:
            return
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
        self.formats.preview_title = ""
        self.formats.audio_languages = []
        self.preview_title_var.set("")
        self._set_audio_language_values([])
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
                # self.status_var.set("Formats failed to load. Check URL or network.")
            self.formats.video_labels = []
            self.formats.video_lookup = {}
            self.formats.audio_labels = []
            self.formats.audio_lookup = {}
            self.formats.audio_languages = []
            self._set_audio_language_values([])
            if not self.formats.preview_title:
                self.preview_title_var.set("")
            self._apply_mode_formats()
            # if not error:
            # self.status_var.set("No formats found")
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
        self._cache_formats_entry(cache_key, {
            "video_labels": self.formats.video_labels,
            "video_lookup": self.formats.video_lookup,
            "audio_labels": self.formats.audio_labels,
            "audio_lookup": self.formats.audio_lookup,
            "audio_languages": self.formats.audio_languages,
            "preview_title": self.formats.preview_title,
        })

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

    @staticmethod
    def _codec_matches_preference(vcodec_raw: str, codec_pref: str) -> bool:
        return core_format_selection.codec_matches_preference(vcodec_raw, codec_pref)

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
        self._set_widget_visible(self.progress_frame, True)

        subtitle_controls_enabled = is_video_mode and not self.is_downloading
        self._set_widget_visible(self.subtitle_languages_label, is_video_mode)
        self._set_widget_visible(self.subtitle_languages_entry, is_video_mode)
        self._set_widget_visible(self.subtitle_options_label, is_video_mode)
        self._set_widget_visible(self.write_subtitles_check, is_video_mode)
        self._set_widget_visible(self.embed_subtitles_check, is_video_mode)
        if subtitle_controls_enabled:
            self.subtitle_languages_entry.configure(state="normal")
            self.write_subtitles_check.state(["!disabled"])
        else:
            self.subtitle_languages_entry.configure(state="disabled")
            self.write_subtitles_check.state(["disabled"])
            self.embed_subtitles_var.set(False)
        embed_allowed = subtitle_controls_enabled and bool(self.write_subtitles_var.get())
        if embed_allowed:
            self.embed_subtitles_check.state(["!disabled"])
        else:
            self.embed_subtitles_var.set(False)
            self.embed_subtitles_check.state(["disabled"])

        audio_language_combo = getattr(self, "audio_language_combo", None)

        if self.is_downloading:
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
        else:
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
        custom_filename_entry = getattr(self, "custom_filename_entry", None)
        if custom_filename_entry is not None:
            if self.is_downloading or is_playlist_url:
                custom_filename_entry.configure(state="disabled")
            else:
                custom_filename_entry.configure(state="normal")
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
        self._progress_anim_after_id = self._safe_after(
            PROGRESS_ANIM_MS, self._progress_anim_tick
        )

    def _snapshot_download_options(self) -> DownloadOptions:
        custom_filename_var = getattr(self, "custom_filename_var", None)
        custom_filename = ""
        if custom_filename_var is not None:
            try:
                custom_filename = str(custom_filename_var.get())
            except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
                custom_filename = ""
        return core_options.build_download_options(
            network_timeout_raw=self.network_timeout_var.get(),
            network_retries_raw=self.network_retries_var.get(),
            retry_backoff_raw=self.retry_backoff_var.get(),
            subtitle_languages_raw=self.subtitle_languages_var.get(),
            write_subtitles_requested=bool(self.write_subtitles_var.get()),
            embed_subtitles_requested=bool(self.embed_subtitles_var.get()),
            is_video_mode=self.mode_var.get() == "video",
            audio_language_raw=self.audio_language_var.get(),
            custom_filename_raw=custom_filename,
            timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
            retries_default=download.YDL_ATTEMPT_RETRIES,
            backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
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
        output_dir = self._ensure_output_dir(self.output_dir_var.get())
        if output_dir is None:
            return
        fmt_label = self.format_var.get()
        fmt_info = self.formats.filtered_lookup.get(fmt_label)
        format_filter = self.format_filter_var.get()
        playlist_enabled = bool(self.playlist_enabled_var.get())
        playlist_items_raw = (self.playlist_items_var.get() or "").strip()
        convert_to_mp4 = bool(self.convert_to_mp4_var.get())
        options = self._snapshot_download_options()

        self.is_downloading = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self._show_progress_item = bool(playlist_enabled and self.is_playlist)
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
                "fmt_label": fmt_label,
                "fmt_info": fmt_info,
                "format_filter": format_filter,
                "playlist_enabled": playlist_enabled,
                "playlist_items_raw": playlist_items_raw,
                "convert_to_mp4": convert_to_mp4,
                "network_timeout_s": options["network_timeout_s"],
                "network_retries": options["network_retries"],
                "retry_backoff_s": options["retry_backoff_s"],
                "subtitle_languages": options["subtitle_languages"],
                "write_subtitles": options["write_subtitles"],
                "embed_subtitles": options["embed_subtitles"],
                "audio_language": options["audio_language"],
                "custom_filename": options["custom_filename"],
            },
            daemon=True,
        )
        self.download_thread.start()

    def _on_add_to_queue(self) -> None:
        if self.is_downloading:
            return
        url = self._strip_url_whitespace(self.url_var.get())
        settings = self._capture_queue_settings()
        issue = core_queue_logic.queue_add_issue(
            url=url,
            playlist_mode=bool(self.is_playlist or self._is_playlist_url(url)),
            formats_loaded=bool(self.formats.filtered_lookup),
            settings=settings,
        )
        if issue:
            status_text, log_text = core_queue_logic.queue_add_feedback(issue)
            self.status_var.set(status_text)
            self._log(log_text)
            return

        self.queue_items.append(core_queue_logic.queue_item(url, settings))
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

    def _export_diagnostics(self) -> None:
        timestamp = datetime.now()
        base_dir = Path(self.output_dir_var.get() or Path.home() / "Downloads").expanduser()
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            base_dir = Path.home() / "Downloads"
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._log(f"[diag] export failed: {exc}")
                self.status_var.set("Diagnostics export failed")
                messagebox.showerror("Diagnostics export failed", str(exc))
                return
        output_path = base_dir / f"yt-dlp-gui-diagnostics-{timestamp:%Y%m%d-%H%M%S}.txt"

        options = self._snapshot_download_options()
        payload = diagnostics.build_report_payload(
            generated_at=timestamp,
            status=self.status_var.get(),
            simple_state=self.simple_state_var.get(),
            url=self.url_var.get(),
            mode=self.mode_var.get(),
            container=self.format_filter_var.get(),
            codec=self.codec_filter_var.get(),
            format_label=self.format_var.get(),
            queue_items=self.queue_items,
            queue_active=self.queue_active,
            is_downloading=self.is_downloading,
            preview_title=self.formats.preview_title,
            options=options,
            history_items=self.download_history,
            logs_text=self.logs.get_text(),
        )

        try:
            output_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            self._log(f"[diag] export failed: {exc}")
            self.status_var.set("Diagnostics export failed")
            messagebox.showerror("Diagnostics export failed", str(exc))
            return
        self._log(f"[diag] exported {output_path}")
        self.status_var.set("Diagnostics exported")
        messagebox.showinfo("Diagnostics exported", f"Saved to:\n{output_path}")

    def _capture_queue_settings(self) -> QueueSettings:
        fmt_label = self.format_var.get()
        fmt_info = self.formats.filtered_lookup.get(fmt_label) or {}
        estimated_size = helpers.humanize_bytes(helpers.estimate_filesize_bytes(fmt_info))
        options = self._snapshot_download_options()
        return core_options.build_queue_settings(
            mode=self.mode_var.get(),
            format_filter=self.format_filter_var.get(),
            codec_filter=self.codec_filter_var.get(),
            convert_to_mp4=bool(self.convert_to_mp4_var.get()),
            format_label=fmt_label,
            estimated_size=estimated_size,
            output_dir=self.output_dir_var.get(),
            playlist_items=self.playlist_items_var.get(),
            options=options,
        )

    def _resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        info = helpers.fetch_info(url)
        formats = formats_mod.formats_from_info(info)
        return core_format_selection.resolve_format_for_info(
            info=info,
            formats=formats,
            settings=settings,
            log=self._log,
        )

    def _start_queue_download(self) -> None:
        if self.is_downloading or not self.queue_items:
            return
        invalid = core_queue_logic.first_invalid_queue_item(self.queue_items)
        if invalid is not None:
            idx, issue = invalid
            messagebox.showerror(
                "Missing settings",
                (
                    "Queue item "
                    f"{idx} is missing {core_queue_logic.queue_start_missing_detail(issue)}."
                ),
            )
            return

        self.queue_active = True
        self.queue_index = 0
        self.queue_settings = None
        self._queue_failed_items = 0
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
        next_index = core_queue_logic.next_non_empty_queue_index(
            self.queue_items, self.queue_index
        )
        if next_index is None:
            self._finish_queue()
            return
        self.queue_index = next_index
        url = str(self.queue_items[self.queue_index].get("url", "")).strip()
        settings = self.queue_items[self.queue_index].get("settings") or {}
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
                "default_output_dir": self.output_dir_var.get(),
            },
            daemon=True,
        )
        self.download_thread.start()

    def _run_queue_download(
        self,
        url: str,
        settings: QueueSettings,
        index: int,
        total: int,
        default_output_dir: str,
    ) -> None:
        had_error = False
        cancelled = False
        try:
            resolved = self._resolve_format_for_url(url, settings)
            title = resolved.get("title") or url
            item_text = f"{index}/{total} {title}"
            self._post_ui(self.progress_item_var.set, item_text)
            request = core_download_plan.build_queue_download_request(
                url=url,
                settings=settings,
                resolved=resolved,
                default_output_dir=default_output_dir,
                timeout_default=download.YDL_SOCKET_TIMEOUT_SECONDS,
                retries_default=download.YDL_ATTEMPT_RETRIES,
                backoff_default=download.YDL_RETRY_BACKOFF_SECONDS,
            )
            output_dir = request["output_dir"]
            output_dir.mkdir(parents=True, exist_ok=True)
            if request["playlist_enabled"]:
                self._log(
                    f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}"
                )
            result = download.run_download(
                url=request["url"],
                output_dir=output_dir,
                fmt_info=request["fmt_info"],
                fmt_label=request["fmt_label"],
                format_filter=request["format_filter"],
                convert_to_mp4=bool(request["convert_to_mp4"]),
                playlist_enabled=bool(request["playlist_enabled"]),
                playlist_items=request["playlist_items"],
                cancel_event=self._cancel_event,
                log=self._log,
                update_progress=lambda u: self._post_ui(self._on_progress_update, u),
                network_retries=int(request["network_retries"]),
                network_timeout_s=int(request["network_timeout_s"]),
                retry_backoff_s=float(request["retry_backoff_s"]),
                subtitle_languages=list(request["subtitle_languages"]),
                write_subtitles=bool(request["write_subtitles"]),
                embed_subtitles=bool(request["embed_subtitles"]),
                audio_language=str(request["audio_language"]),
                custom_filename=str(request["custom_filename"]),
                record_output=lambda p: self._post_ui(self._record_download_output, p, url),
            )
            had_error = result == download.DOWNLOAD_ERROR
            cancelled = result == download.DOWNLOAD_CANCELLED
        except Exception as exc:
            had_error = True
            self._log(f"[queue] failed: {exc}")
        finally:
            self._post_ui(self._on_queue_item_finish, had_error, cancelled)

    def _on_queue_item_finish(
        self,
        had_error: bool = False,
        cancelled: bool = False,
    ) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        if had_error:
            self._queue_failed_items += 1
        if cancelled:
            self._cancel_requested = True
        if self._cancel_requested:
            self._log("[queue] cancelled")
            self._finish_queue(cancelled=True)
            return
        self.queue_index += 1
        if self.queue_index >= len(self.queue_items):
            self._finish_queue()
            return
        self._reset_progress_summary()
        self._start_next_queue_item()

    def _finish_queue(self, *, cancelled: bool = False) -> None:
        failed_items = self._queue_failed_items
        self.queue_active = False
        self.queue_index = None
        self.queue_settings = None
        self._queue_failed_items = 0
        self.is_downloading = False
        self._show_progress_item = False
        self._cancel_requested = False
        self._cancel_event = None
        if cancelled:
            self._log("[queue] stopped by cancellation")
        elif failed_items:
            self._log(f"[queue] finished with {failed_items} failed item(s)")
        else:
            self._log("[queue] finished successfully")
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self._reset_progress_summary()
        self._update_controls_state()
        self._queue_refresh()

    def _run_download(
        self,
        url: str,
        output_dir: Path,
        fmt_label: str,
        fmt_info: dict | None,
        format_filter: str,
        playlist_enabled: bool,
        playlist_items_raw: str,
        convert_to_mp4: bool,
        network_timeout_s: int = download.YDL_SOCKET_TIMEOUT_SECONDS,
        network_retries: int = download.YDL_ATTEMPT_RETRIES,
        retry_backoff_s: float = download.YDL_RETRY_BACKOFF_SECONDS,
        subtitle_languages: list[str] | None = None,
        write_subtitles: bool = False,
        embed_subtitles: bool = False,
        audio_language: str = "",
        custom_filename: str = "",
    ) -> None:
        playlist_items, was_normalized = core_download_plan.normalize_playlist_items(
            playlist_items_raw
        )
        if was_normalized:
            self._log("[info] Playlist items normalized (spaces removed).")
        if playlist_enabled:
            self._log(f"[playlist] enabled=1 items={playlist_items or 'none'}")

        options: DownloadOptions = {
            "network_timeout_s": network_timeout_s,
            "network_retries": network_retries,
            "retry_backoff_s": retry_backoff_s,
            "subtitle_languages": list(subtitle_languages or []),
            "write_subtitles": bool(write_subtitles),
            "embed_subtitles": bool(embed_subtitles),
            "audio_language": audio_language,
            "custom_filename": custom_filename,
        }
        request = core_download_plan.build_single_download_request(
            url=url,
            output_dir=output_dir,
            fmt_info=fmt_info,
            fmt_label=fmt_label,
            format_filter=format_filter,
            convert_to_mp4=convert_to_mp4,
            playlist_enabled=playlist_enabled,
            playlist_items_raw=playlist_items or "",
            options=options,
        )

        result = download.run_download(
            url=request["url"],
            output_dir=request["output_dir"],
            fmt_info=request["fmt_info"],
            fmt_label=request["fmt_label"],
            format_filter=request["format_filter"],
            convert_to_mp4=request["convert_to_mp4"],
            playlist_enabled=request["playlist_enabled"],
            playlist_items=request["playlist_items"],
            cancel_event=self._cancel_event,
            log=self._log,
            update_progress=lambda u: self._post_ui(self._on_progress_update, u),
            network_retries=request["network_retries"],
            network_timeout_s=request["network_timeout_s"],
            retry_backoff_s=request["retry_backoff_s"],
            subtitle_languages=list(request["subtitle_languages"]),
            write_subtitles=bool(request["write_subtitles"]),
            embed_subtitles=bool(request["embed_subtitles"]),
            audio_language=(request["audio_language"] or "").strip(),
            custom_filename=(request["custom_filename"] or "").strip(),
            record_output=lambda p: self._post_ui(self._record_download_output, p, url),
        )
        if result == download.DOWNLOAD_ERROR:
            self._log("[status] Download finished with errors.")
        self._post_ui(self._on_finish)

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
        self._closing = True
        self._active_fetch_request_id = None
        self._cancel_requested = True
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._cancel_after("fetch_after_id", self.formats)
        self._cancel_after("_progress_anim_after_id")
        self._cancel_after("_ui_event_after_id")
        try:
            while True:
                self._ui_event_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self.logs.shutdown()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            self.settings_panel.shutdown()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            self.queue_panel.shutdown()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            self.history_panel.shutdown()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            self.root.destroy()
        except (tk.TclError, RuntimeError):
            pass


def main() -> None:
    YtDlpGui().root.mainloop()


if __name__ == "__main__":
    main()
