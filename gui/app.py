import re
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Timing/layout constants (keep UI behavior consistent and readable).
FETCH_DEBOUNCE_MS = 600
PROGRESS_ANIM_MS = 33

# Support running as a script (python gui/app.py) or as a module (python -m gui.app).
try:
    from . import (
        download,
        formats as formats_mod,
        ui,
        yt_dlp_helpers as helpers,
    )
    from .state import FormatState
except ImportError:
    import importlib
    import sys

    sys.path.append(str(Path(__file__).resolve().parent))
    helpers = importlib.import_module("yt_dlp_helpers")
    download = importlib.import_module("download")
    formats_mod = importlib.import_module("formats")
    ui = importlib.import_module("ui")
    FormatState = importlib.import_module("state").FormatState


class YtDlpGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("yt-dlp GUI")
        self.root.minsize(720, 550)
        self._progress_anim_after_id: str | None = None
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self.download_thread: threading.Thread | None = None
        self.is_downloading = False
        self.formats = FormatState()
        self._normalizing_url = False

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="video")  # "video" or "audio"
        # These are filled after probing a URL.
        self.format_filter_var = tk.StringVar(value="")  # must choose mp4 or webm
        self.codec_filter_var = tk.StringVar(value="")  # must choose avc1 or av01
        self.convert_to_mp4_var = tk.BooleanVar(
            value=False
        )  # convert WebM to MP4 after download (re-encode)
        self.format_var = tk.StringVar()
        self.title_override_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = tk.StringVar(value="Idle")
        self._last_status_logged = self.status_var.get()
        self.simple_state_var = tk.StringVar(value="Idle")
        self.progress_pct_var = tk.StringVar(value="0.0%")
        self.progress_speed_var = tk.StringVar(value="—")
        self.progress_eta_var = tk.StringVar(value="—")

        self.logs = ui.build_ui(self)
        self._init_visibility_helpers()
        self.status_var.trace_add("write", lambda *_: self._on_status_change())
        self.url_var.trace_add("write", lambda *_: self._on_url_change())
        self._update_controls_state()
        self.root.bind("<Configure>", self.logs.on_root_configure, add=True)
        self.logs.on_root_configure(tk.Event())
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
            self.container_label,
            self.container_combo,
            self.codec_label,
            self.codec_combo,
            self.convert_mp4_inline_label,
            self.convert_mp4_check,
            self.format_label,
            self.format_combo,
        ]:
            self._widget_grid_info[w] = w.grid_info()

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
            if widget.winfo_manager():
                widget.grid_remove()

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

    def _log(self, message: str) -> None:
        self.logs.queue(message)

    def _on_mode_change(self) -> None:
        self._apply_mode_formats()
        self._update_controls_state()

    def _on_url_change(self, force: bool = False) -> None:
        self._normalize_url_var()
        # Debounce format fetching when the URL changes.
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
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
        formats = formats_mod.formats_from_info(info)
        self.root.after(0, lambda: self._set_formats(formats))

    def _set_formats(self, formats: list[dict], error: bool = False) -> None:
        self.formats.is_fetching = False
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
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
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
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
        self._apply_mode_formats()
        self.status_var.set("Formats loaded (cached)")
        self._update_controls_state()

    def _apply_mode_formats(self) -> None:
        if self.mode_var.get() == "audio":
            labels = self.formats.audio_labels
            lookup = self.formats.audio_lookup
        else:
            labels = self.formats.video_labels
            lookup = self.formats.video_lookup

        filter_val = self.format_filter_var.get()
        codec_raw = self.codec_filter_var.get()
        codec_val = codec_raw.lower()
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

        self.formats.filtered_labels = filtered_labels
        self.formats.filtered_lookup = filtered_lookup
        self.format_combo.configure(values=self.formats.filtered_labels)
        if self.formats.filtered_labels:
            if self.format_var.get() not in self.formats.filtered_labels:
                self.format_var.set(self.formats.filtered_labels[0])
        else:
            self.format_var.set("")
        self._update_controls_state()

    def _update_controls_state(self) -> None:
        url_present = bool(self.url_var.get().strip())
        has_formats_data = bool(self.formats.video_labels or self.formats.audio_labels)
        container_value = self.format_filter_var.get()
        filter_chosen = container_value in {"mp4", "webm"}
        codec_chosen = bool(self.codec_filter_var.get())
        format_available = bool(self.formats.filtered_labels)
        format_selected = bool(self.format_var.get())
        base_ready = (
            url_present
            and has_formats_data
            and not self.formats.is_fetching
            and not self.is_downloading
        )

        # Keep all options visible; disable when not usable.
        self._configure_combobox(
            self.container_label,
            self.container_combo,
            show=True,
            enabled=base_ready,
        )

        self._configure_combobox(
            self.codec_label,
            self.codec_combo,
            show=True,
            enabled=base_ready and filter_chosen,
        )

        # Convert checkbox only relevant when container is webm.
        is_webm = container_value == "webm"
        show_convert = is_webm
        self._set_widget_visible(self.convert_mp4_inline_label, show_convert)
        self._set_widget_visible(self.convert_mp4_check, show_convert)
        convert_enabled = base_ready and filter_chosen and is_webm
        if convert_enabled:
            self.convert_mp4_check.state(["!disabled"])
        else:
            self.convert_to_mp4_var.set(False)
            self.convert_mp4_check.state(["disabled"])

        self._configure_combobox(
            self.format_label,
            self.format_combo,
            show=True,
            enabled=base_ready and filter_chosen and codec_chosen and format_available,
        )

        # Start button
        if base_ready and filter_chosen and codec_chosen and format_selected:
            self.start_button.state(["!disabled"])
        else:
            self.start_button.state(["disabled"])

    def _reset_progress_summary(self) -> None:
        self.progress_pct_var.set("0.0%")
        self.progress_speed_var.set("—")
        self.progress_eta_var.set("—")
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
            if isinstance(eta, str):
                self.progress_eta_var.set(eta or "—")
        elif status == "finished":
            self._progress_pct_target = 100.0
            if self._progress_anim_after_id is None:
                self._progress_anim_tick()

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
        self.simple_state_var.set("Downloading")
        self.status_var.set("Downloading...")
        self.start_button.state(["disabled"])
        self.logs.clear()
        self._reset_progress_summary()
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

    def _run_download(self, url: str, output_dir: Path, fmt_label: str) -> None:
        fmt_info = self.formats.filtered_lookup.get(fmt_label)
        format_filter = self.format_filter_var.get()
        title_override_raw = self.title_override_var.get().strip()
        if getattr(self, "_title_placeholder_active", False):
            title_override_raw = ""
        title_override = title_override_raw or None

        download.run_download(
            url=url,
            output_dir=output_dir,
            fmt_info=fmt_info,
            fmt_label=fmt_label,
            format_filter=format_filter,
            convert_to_mp4=self.convert_to_mp4_var.get(),
            title_override=title_override,
            log=self._log,
            update_progress=lambda u: self.root.after(
                0, lambda: self._on_progress_update(u)
            ),
        )
        self.root.after(0, self._on_finish)

    def _on_finish(self) -> None:
        self.is_downloading = False
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self.start_button.state(["!disabled"])
        self._reset_progress_summary()

    def _on_close(self) -> None:
        if self.is_downloading:
            if not messagebox.askokcancel(
                "Download running", "A download is in progress. Quit anyway?"
            ):
                return
        self._cancel_after("fetch_after_id", self.formats)
        self._cancel_after("_progress_anim_after_id")
        self.logs.shutdown()
        self.root.destroy()


def main() -> None:
    YtDlpGui().root.mainloop()


if __name__ == "__main__":
    main()
