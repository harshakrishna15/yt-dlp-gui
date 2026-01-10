import queue
import threading
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Support running as a script (python gui/app.py) or as a module (python -m gui.app).
try:
    from . import download, styles, yt_dlp_helpers as helpers
except ImportError:
    import importlib
    import sys

    sys.path.append(str(Path(__file__).resolve().parent))
    helpers = importlib.import_module("yt_dlp_helpers")
    download = importlib.import_module("download")
    styles = importlib.import_module("styles")


class YtDlpGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("yt-dlp GUI")
        self.root.minsize(520, 520)
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.download_thread: threading.Thread | None = None
        self.is_downloading = False
        self.is_fetching_formats = False
        self.last_fetched_url = ""
        self.format_fetch_after_id: str | None = None
        self.last_progress_update = 0.0
        self.last_progress_index: str | None = None
        self.download_start_time: float | None = None
        self.last_fetch_failed = False

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="video")  # "video" or "audio"
        # These are filled after probing a URL.
        self.format_labels: list[str] = []
        # Maps label to a format dict for the selected stream.
        self.format_lookup: dict[str, dict] = {}
        self.video_format_labels: list[str] = []
        self.video_format_lookup: dict[str, dict] = {}
        self.audio_format_labels: list[str] = []
        self.audio_format_lookup: dict[str, dict] = {}
        # Cache fetched formats per URL to avoid repeated probes.
        self.format_cache: dict[str, dict] = {}
        self.format_filter_var = tk.StringVar(value="")  # must choose mp4 or webm
        self.codec_filter_var = tk.StringVar(value="")  # must choose avc1 or av01
        self.convert_to_mp4_var = tk.BooleanVar(
            value=False
        )  # convert WebM to MP4 after download (re-encode)
        self.format_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = tk.StringVar(value="Idle")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_ui()
        self._init_visibility_helpers()
        self.url_var.trace_add("write", lambda *_: self._on_url_change())
        self._update_controls_state()
        self._poll_log_queue()

    class _Scrollable(ttk.Frame):
        def __init__(self, parent: tk.Widget, *, padding: int = 0) -> None:
            super().__init__(parent)
            self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.content = ttk.Frame(self.canvas, padding=padding)
            self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

            self.canvas.grid(column=0, row=0, sticky="nsew")
            self.scrollbar.grid(column=1, row=0, sticky="ns")
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)

            self.content.bind("<Configure>", self._on_content_configure)
            self.canvas.bind("<Configure>", self._on_canvas_configure)
            self._bind_mousewheel(self.canvas)

        def _on_content_configure(self, _event: tk.Event) -> None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(self, event: tk.Event) -> None:
            self.canvas.itemconfigure(self._window_id, width=event.width)

        def _bind_mousewheel(self, widget: tk.Widget) -> None:
            def on_mousewheel(event: tk.Event) -> str:
                if getattr(event, "delta", 0):
                    widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                return ""

            def on_button4(_event: tk.Event) -> str:
                widget.yview_scroll(-1, "units")
                return "break"

            def on_button5(_event: tk.Event) -> str:
                widget.yview_scroll(1, "units")
                return "break"

            widget.bind_all("<MouseWheel>", on_mousewheel)
            widget.bind_all("<Button-4>", on_button4)
            widget.bind_all("<Button-5>", on_button5)

    def _init_visibility_helpers(self) -> None:
        # Cache grid info for widgets we may hide/show.
        self._widget_grid_info = {}
        for w in [
            self.container_label,
            self.container_combo,
            self.codec_label,
            self.codec_combo,
            self.convert_mp4_check,
            self.format_label,
            self.format_combo,
        ]:
            self._widget_grid_info[w] = w.grid_info()

    def _set_widget_visible(self, widget: tk.Widget, show: bool) -> None:
        # Keep widgets laid out to avoid flicker; just ensure they are gridded once.
        if not widget.winfo_manager():
            info = self._widget_grid_info.get(widget) or {}
            widget.grid(**info)

    def _build_ui(self) -> None:
        require_plex = os.getenv("YTDLP_GUI_REQUIRE_PLEX_MONO") == "1"
        warn_missing_font = os.getenv("YTDLP_GUI_WARN_MISSING_FONT") == "1"
        try:
            palette = styles.apply_theme(self.root, require_plex_mono=require_plex)
        except RuntimeError as exc:
            messagebox.showerror("Font required", str(exc))
            raise SystemExit(1) from exc

        if warn_missing_font and not palette.get("using_plex_mono", False):
            messagebox.showwarning(
                "Font not installed",
                "IBM Plex Mono is not installed (or not visible to Tk). "
                "The UI will use a fallback monospace font.",
            )
        text_fg = palette["text_fg"]
        fonts = palette["fonts"]
        accent = palette["accent"]
        entry_border = palette["entry_border"]

        scroll = self._Scrollable(self.root, padding=6)
        scroll.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main = scroll.content
        main.columnconfigure(1, weight=1)

        header = ttk.Frame(main, padding=8, style="Card.TFrame")
        header.grid(column=0, row=0, columnspan=2, sticky="ew", pady=(0, 4))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="yt-dlp-gui", style="Title.TLabel", font=fonts["title"]).grid(
            column=0, row=0, sticky="w"
        )

        sep1 = ttk.Separator(main, orient="horizontal")
        sep1.grid(column=0, row=1, columnspan=2, sticky="ew", pady=(2, 2))

        options = ttk.Frame(main, padding=8, style="Card.TFrame")
        options.grid(column=0, row=2, columnspan=2, sticky="ew", pady=(0, 4))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Download Options", style="Subheader.TLabel", font=fonts["subheader"]).grid(
            column=0, row=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        ttk.Label(options, text="Video URL").grid(
            column=0, row=1, sticky="w", padx=(0, 8), pady=4
        )
        url_frame = ttk.Frame(options)
        url_frame.grid(column=1, row=1, sticky="ew", pady=4)
        url_frame.columnconfigure(0, weight=1)
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, style="Dark.TEntry")
        url_entry.grid(column=0, row=0, sticky="ew")
        ttk.Button(url_frame, text="Paste", command=self._paste_url).grid(
            column=1, row=0, padx=(8, 0)
        )
        url_entry.focus()

        type_row = ttk.Frame(options)
        type_row.grid(column=0, row=2, columnspan=2, sticky="w", pady=4)
        ttk.Label(type_row, text="Content Type").grid(column=0, row=0, sticky="w", padx=(0, 8))
        mode_frame = ttk.Frame(type_row)
        mode_frame.grid(column=1, row=0, sticky="w")
        ttk.Radiobutton(
            mode_frame,
            text="Video and Audio",
            variable=self.mode_var,
            value="video",
            command=self._on_mode_change,
        ).grid(column=0, row=0, padx=(0, 12))
        ttk.Radiobutton(
            mode_frame,
            text="Audio Only",
            variable=self.mode_var,
            value="audio",
            command=self._on_mode_change,
        ).grid(column=1, row=0)

        self.container_label = ttk.Label(options, text="Container")
        self.container_label.grid(column=0, row=3, sticky="w", padx=(0, 8), pady=4)
        self.container_combo = ttk.Combobox(
            options,
            textvariable=self.format_filter_var,
            values=["mp4", "webm"],
            state="readonly",
            width=10,
        )
        self.container_combo.grid(column=1, row=3, sticky="w", pady=4)
        self.format_filter_var.trace_add(
            "write",
            lambda *_: (self._apply_mode_formats(), self._update_controls_state()),
        )

        self.codec_label = ttk.Label(options, text="Codec")
        self.codec_label.grid(column=0, row=4, sticky="w", padx=(0, 8), pady=4)
        self.codec_combo = ttk.Combobox(
            options,
            textvariable=self.codec_filter_var,
            values=["avc1 (H.264)", "av01 (AV1)"],
            state="readonly",
            width=15,
        )
        self.codec_combo.grid(column=1, row=4, sticky="w", pady=4)
        self.codec_filter_var.trace_add(
            "write",
            lambda *_: (self._apply_mode_formats(), self._update_controls_state()),
        )

        self.convert_mp4_check = ttk.Checkbutton(
            options,
            text="Convert WebM to MP4 after download (re-encode; slower, lossy)",
            variable=self.convert_to_mp4_var,
        )
        self.convert_mp4_check.grid(column=1, row=5, sticky="w", pady=4)

        self.format_label = ttk.Label(options, text="Format")
        self.format_label.grid(column=0, row=6, sticky="w", padx=(0, 8), pady=4)
        self.format_combo = ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=self.format_labels,
            state="readonly",
        )
        self.format_combo.grid(column=1, row=6, sticky="ew", pady=4)

        ttk.Label(options, text="Output folder").grid(
            column=0, row=7, sticky="w", padx=(0, 8), pady=4
        )
        output_frame = ttk.Frame(options)
        output_frame.grid(column=1, row=7, sticky="ew", pady=(2, 0))
        output_frame.columnconfigure(0, weight=1)
        pill = ttk.Frame(output_frame, style="OutputPath.TFrame", padding=4)
        pill.grid(column=0, row=0, sticky="ew")
        pill.columnconfigure(0, weight=1)
        ttk.Label(
            pill,
            textvariable=self.output_dir_var,
            anchor="w",
            style="OutputPath.TLabel",
        ).grid(column=0, row=0, sticky="ew")
        ttk.Button(
            output_frame, text="Browse...", command=self._pick_folder
        ).grid(column=1, row=0, padx=(8, 0), sticky="e")

        sep2 = ttk.Separator(main, orient="horizontal")
        sep2.grid(column=0, row=3, columnspan=2, sticky="ew", pady=(2, 2))

        controls = ttk.Frame(main, padding=8, style="Card.TFrame")
        controls.grid(column=0, row=4, columnspan=2, sticky="ew", pady=4)
        controls.columnconfigure(0, weight=1)
        ttk.Label(controls, text="Controls", style="Subheader.TLabel", font=fonts["subheader"]).grid(
            column=0, row=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        ttk.Label(controls, textvariable=self.status_var).grid(
            column=0, row=1, sticky="w"
        )
        self.start_button = ttk.Button(
            controls, text="Start download", command=self._on_start, style="Accent.TButton"
        )
        self.start_button.grid(column=1, row=1, sticky="e")
        self.progress = ttk.Progressbar(
            controls, variable=self.progress_var, maximum=100, mode="determinate"
        )
        self.progress.grid(column=0, row=2, columnspan=2, sticky="ew", pady=(6, 0))

        progress_frame = ttk.Frame(controls, padding=4, style="Card.TFrame")
        progress_frame.grid(column=0, row=3, columnspan=2, sticky="ew", pady=(6, 0))
        progress_frame.columnconfigure(0, weight=1)
        ttk.Label(progress_frame, text="Progress Details", style="Subheader.TLabel", font=fonts["subheader"]).grid(
            column=0, row=0, sticky="w", pady=(0, 4)
        )
        self.progress_text = tk.Text(
            progress_frame,
            height=3,
            wrap="word",
            state="disabled",
            background=palette["panel_bg"],
            foreground=text_fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=entry_border,
            highlightcolor=entry_border,
        )
        self.progress_text.grid(column=0, row=1, sticky="ew")

        sep3 = ttk.Separator(main, orient="horizontal")
        sep3.grid(column=0, row=5, columnspan=2, sticky="ew", pady=(2, 2))

        log_frame = ttk.Frame(main, padding=8, style="Card.TFrame")
        log_frame.grid(column=0, row=6, columnspan=2, sticky="ew", pady=(4, 0))
        log_frame.columnconfigure(0, weight=1)
        ttk.Label(log_frame, text="Log", style="Subheader.TLabel", font=fonts["subheader"]).grid(
            column=0, row=0, sticky="w", pady=(0, 4)
        )

        self.log_text = tk.Text(
            log_frame,
            height=12,
            wrap="word",
            state="disabled",
            background=palette["panel_bg"],
            foreground=text_fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=entry_border,
            highlightcolor=entry_border,
        )
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(column=0, row=1, sticky="nsew")
        scrollbar.grid(column=1, row=1, sticky="ns")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            self.output_dir_var.set(chosen)

    def _paste_url(self) -> None:
        try:
            clip = self.root.clipboard_get().strip()
        except Exception:
            clip = ""
        if clip:
            self.url_var.set(clip)
            self.status_var.set("URL pasted")
            # Force format fetch even if URL hasn't changed.
            self._on_url_change(force=True)
        else:
            self.status_var.set("Clipboard is empty")

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _on_mode_change(self) -> None:
        self._apply_mode_formats()
        self._update_controls_state()

    def _on_url_change(self, force: bool = False) -> None:
        # Debounce format fetching when the URL changes.
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
        self._update_controls_state()
        if self.format_fetch_after_id:
            self.root.after_cancel(self.format_fetch_after_id)
        if force:
            self._start_fetch_formats(force=True)
        else:
            self.format_fetch_after_id = self.root.after(600, self._start_fetch_formats)

    def _start_fetch_formats(self, force: bool = False) -> None:
        url = self.url_var.get().strip()
        if (
            not url
            or self.is_downloading
            or self.is_fetching_formats
        ):
            return
        # Use cache if available.
        cached = self.format_cache.get(url)
        if cached:
            self._load_cached_formats(url, cached)
            return
        if url == self.last_fetched_url and not force and not self.last_fetch_failed:
            return
        self.is_fetching_formats = True
        self.last_fetched_url = url
        self.last_fetch_failed = False
        self.status_var.set("Fetching formats...")
        self.start_button.state(["disabled"])
        self.format_combo.state(["disabled"])
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

        entry = info
        if info.get("_type") == "playlist" and info.get("entries"):
            entry = info["entries"][0] or {}

        formats = entry.get("formats") or []
        self.root.after(0, lambda: self._set_formats(formats))

    def _set_formats(self, formats: list[dict], error: bool = False) -> None:
        self.is_fetching_formats = False
        if error or not formats:
            if error:
                self.last_fetched_url = ""
                self.last_fetch_failed = True
                self.status_var.set("Formats failed to load. Check URL or network.")
            self.video_format_labels = []
            self.video_format_lookup = {}
            self.audio_format_labels = []
            self.audio_format_lookup = {}
            self._apply_mode_formats()
            if not error:
                self.status_var.set("No formats found")
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

        self.video_format_labels = [label for label, _ in video_labeled]
        self.video_format_lookup = {label: fmt for label, fmt in video_labeled}
        self.audio_format_labels = [label for label, _ in audio_labeled]
        self.audio_format_lookup = {label: fmt for label, fmt in audio_labeled}
        # Cache processed formats for this URL.
        self.format_cache[self.last_fetched_url] = {
            "video_labels": self.video_format_labels,
            "video_lookup": self.video_format_lookup,
            "audio_labels": self.audio_format_labels,
            "audio_lookup": self.audio_format_lookup,
        }

        # Require user to pick a container after formats load.
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
        self._apply_mode_formats()
        self.last_fetch_failed = False
        self.status_var.set("Formats loaded")
        self._update_controls_state()

    def _load_cached_formats(self, url: str, cached: dict) -> None:
        self.last_fetched_url = url
        self.video_format_labels = cached.get("video_labels", [])
        self.video_format_lookup = cached.get("video_lookup", {})
        self.audio_format_labels = cached.get("audio_labels", [])
        self.audio_format_lookup = cached.get("audio_lookup", {})
        self.format_filter_var.set("")
        self.codec_filter_var.set("")
        self.format_var.set("")
        self._apply_mode_formats()
        self.status_var.set("Formats loaded (cached)")
        self._update_controls_state()

    def _apply_mode_formats(self) -> None:
        if self.mode_var.get() == "audio":
            labels = self.audio_format_labels
            lookup = self.audio_format_lookup
        else:
            labels = self.video_format_labels
            lookup = self.video_format_lookup

        filter_val = self.format_filter_var.get()
        codec_val = self.codec_filter_var.get().lower()
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
            self.status_var.set(
                "Chosen codec not available for this container; showing all formats in container"
            )
            apply_filters(allow_any_codec=True)

        self.format_labels = filtered_labels
        self.format_lookup = filtered_lookup
        self.format_combo.configure(values=self.format_labels)
        if self.format_labels:
            if self.format_var.get() not in self.format_labels:
                self.format_var.set(self.format_labels[0])
        else:
            self.format_var.set("")
        self._update_controls_state()

    def _update_controls_state(self) -> None:
        url_present = bool(self.url_var.get().strip())
        has_formats_data = bool(self.video_format_labels or self.audio_format_labels)
        filter_chosen = self.format_filter_var.get() in {"mp4", "webm"}
        codec_chosen = bool(self.codec_filter_var.get())
        format_available = bool(self.format_labels)
        format_selected = bool(self.format_var.get())

        # Container chooser
        show_container = url_present and has_formats_data and not self.is_fetching_formats
        self._set_widget_visible(self.container_label, show_container)
        self._set_widget_visible(self.container_combo, show_container)
        if show_container:
            self.container_combo.state(["!disabled", "readonly"])
        else:
            self.container_combo.state(["disabled"])

        # Codec chooser
        show_codec = (
            url_present and has_formats_data and filter_chosen and not self.is_fetching_formats
        )
        self._set_widget_visible(self.codec_label, show_codec)
        self._set_widget_visible(self.codec_combo, show_codec)
        if show_codec:
            self.codec_combo.state(["!disabled", "readonly"])
        else:
            self.codec_combo.state(["disabled"])

        # Convert checkbox only relevant when container is webm.
        show_convert = (
            url_present
            and has_formats_data
            and filter_chosen
            and self.format_filter_var.get() == "webm"
        )
        self._set_widget_visible(self.convert_mp4_check, show_convert)
        if show_convert:
            self.convert_mp4_check.state(["!disabled"])
        else:
            self.convert_to_mp4_var.set(False)
            self.convert_mp4_check.state(["disabled"])

        # Format dropdown
        if (
            url_present
            and has_formats_data
            and filter_chosen
            and codec_chosen
            and format_available
            and not self.is_fetching_formats
            and not self.is_downloading
        ):
            show_format = True
        else:
            show_format = False
        self._set_widget_visible(self.format_label, show_format)
        self._set_widget_visible(self.format_combo, show_format)
        if show_format:
            self.format_combo.state(["!disabled", "readonly"])
        else:
            self.format_combo.state(["disabled"])

        # Start button
        if (
            url_present
            and has_formats_data
            and filter_chosen
            and codec_chosen
            and format_selected
            and not self.is_fetching_formats
            and not self.is_downloading
        ):
            self.start_button.state(["!disabled"])
        else:
            self.start_button.state(["disabled"])

    def _poll_log_queue(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    def _append_log(self, message: str) -> None:
        # Route progress/start/done/time to the progress box; errors to log.
        progress_prefixes = ("[progress]", "[start]", "[done]", "[time]")
        if message.startswith(progress_prefixes):
            self._append_progress(message)
            return

        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.last_progress_index = None

    def _append_progress(self, message: str) -> None:
        # Replace last line for progress updates; append for start/done/time.
        replace_line = message.startswith("[progress]")
        self.progress_text.configure(state="normal")
        if replace_line:
            try:
                self.progress_text.delete("end-2l linestart", "end-1c")
            except tk.TclError:
                pass
        self.progress_text.insert("end", message + "\n")
        self.progress_text.see("end")
        self.progress_text.configure(state="disabled")

    def _clear_progress(self) -> None:
        self.progress_text.configure(state="normal")
        self.progress_text.delete("1.0", "end")
        self.progress_text.configure(state="disabled")

    def _update_progress(self, value: float) -> None:
        self.progress_var.set(max(0, min(100, value)))

    def _on_start(self) -> None:
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please paste a video URL to download.")
            return
        if not self.format_lookup:
            messagebox.showerror(
                "Formats unavailable", "Formats have not been loaded yet."
            )
            return
        output_dir = Path(self.output_dir_var.get()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        self.is_downloading = True
        self.status_var.set("Downloading...")
        self.start_button.state(["disabled"])
        self._clear_log()
        self._clear_progress()
        self._update_progress(0)
        self.download_start_time = time.time()
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
        fmt_info = self.format_lookup.get(fmt_label)
        format_filter = self.format_filter_var.get()

        download.run_download(
            url=url,
            output_dir=output_dir,
            fmt_info=fmt_info,
            fmt_label=fmt_label,
            format_filter=format_filter,
            convert_to_mp4=self.convert_to_mp4_var.get(),
            log=self._log,
            update_progress=lambda v: self.root.after(0, lambda: self._update_progress(v)),
        )
        self.root.after(0, self._on_finish)

    def _on_finish(self) -> None:
        self.is_downloading = False
        self.status_var.set("Idle")
        self.start_button.state(["!disabled"])
        self._update_progress(0)
        self.download_start_time = None

    def _on_close(self) -> None:
        if self.is_downloading:
            if not messagebox.askokcancel(
                "Download running", "A download is in progress. Quit anyway?"
            ):
                return
        self.root.destroy()


def main() -> None:
    YtDlpGui().root.mainloop()


if __name__ == "__main__":
    main()
