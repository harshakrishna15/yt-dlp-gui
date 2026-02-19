import os
import queue
import subprocess
import sys
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Keep module-level imports for compatibility with existing tests that patch
# gui.tkinter.app.<module> symbols directly.
from ..common import (
    diagnostics,
    download,
    format_pipeline,
    formats as formats_mod,
    tooling,
    yt_dlp_helpers as helpers,
)
from ..common.types import HistoryItem, QueueItem, QueueSettings
from ..core import urls as core_urls
from ..services import app_service
from . import ui
from .constants import (
    AUDIO_CONTAINERS,
    FETCH_DEBOUNCE_MS,
    FORMAT_CACHE_MAX_ENTRIES,
    HISTORY_MAX_ENTRIES,
    PROGRESS_ANIM_MS,
    UI_EVENT_MAX_PER_TICK,
    UI_EVENT_POLL_MS,
    VIDEO_CONTAINERS,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_SCREEN_MARGIN,
)
from .controls import ControlsMixin
from .download_flow import DownloadFlowMixin
from .queue_flow import QueueFlowMixin
from .state import FormatState


class YtDlpGui(ControlsMixin, QueueFlowMixin, DownloadFlowMixin):
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
        self._bind_sidebar_layout_handlers()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ui_event_after_id = self._safe_after(UI_EVENT_POLL_MS, self._drain_ui_events)
        self._safe_after(50, self._warn_missing_dependencies)

    def _sidebar_panels(self) -> list[object]:
        return [
            panel
            for panel in [
                getattr(self, "logs", None),
                getattr(self, "settings_panel", None),
                getattr(self, "queue_panel", None),
                getattr(self, "history_panel", None),
            ]
            if panel is not None
        ]

    def _bind_sidebar_layout_handlers(self) -> None:
        panels = self._sidebar_panels()
        for panel in panels:
            on_root_configure = getattr(panel, "on_root_configure", None)
            if on_root_configure is None:
                continue
            self.root.bind("<Configure>", on_root_configure, add=True)

        for panel in panels:
            on_root_configure = getattr(panel, "on_root_configure", None)
            if on_root_configure is None:
                continue
            on_root_configure(tk.Event())

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
            self.url_var.set(core_urls.strip_url_whitespace(clip))
            self.status_var.set("URL pasted")
            # Force format fetch even if URL hasn't changed.
            self._on_url_change(force=True)
        else:
            self.status_var.set("Clipboard is empty")

    def _normalize_url_var(self) -> None:
        if self._normalizing_url:
            return
        current = self.url_var.get()
        normalized = core_urls.strip_url_whitespace(current)
        if normalized == current:
            return
        self._normalizing_url = True
        try:
            self.url_var.set(normalized)
        finally:
            self._normalizing_url = False

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
        recorded = app_service.record_history_output(
            history=self.download_history,
            seen_paths=self._history_seen_paths,
            output_path=output_path,
            source_url=source_url,
            max_entries=HISTORY_MAX_ENTRIES,
        )
        if not recorded:
            return
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

        for component_name in ["logs", "settings_panel", "queue_panel", "history_panel"]:
            component = getattr(self, component_name, None)
            if component is None:
                continue
            shutdown = getattr(component, "shutdown", None)
            if shutdown is None:
                continue
            try:
                shutdown()
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
