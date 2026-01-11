import queue
import re
import threading
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Timing/layout constants (keep UI behavior consistent and readable).
FETCH_DEBOUNCE_MS = 600
LAYOUT_ANIM_MS = 16
PROGRESS_ANIM_MS = 33
SIDEBAR_ANIM_MS = 16

# Support running as a script (python gui/app.py) or as a module (python -m gui.app).
try:
    from . import download, styles, yt_dlp_helpers as helpers, widgets
except ImportError:
    import importlib
    import sys

    sys.path.append(str(Path(__file__).resolve().parent))
    helpers = importlib.import_module("yt_dlp_helpers")
    download = importlib.import_module("download")
    styles = importlib.import_module("styles")
    widgets = importlib.import_module("widgets")


class YtDlpGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("yt-dlp GUI")
        self.root.minsize(720, 550)
        self._layout_anim_after_id: str | None = None
        self._layout_target: tuple[int, int] | None = None  # wraplength, log_lines
        self._layout_current: list[float] | None = (
            None  # wraplength, log_lines (floats for easing)
        )
        self._layout_last_applied: tuple[int, int] | None = None
        self._progress_anim_after_id: str | None = None
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self._log_sidebar_after_id: str | None = None
        self._log_sidebar_open = False
        self._log_sidebar_width_target = 0
        self._log_sidebar_width_current = 0.0
        self._log_sidebar_margin = 0
        self._logs_unread = False
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.download_thread: threading.Thread | None = None
        self.is_downloading = False
        self.is_fetching_formats = False
        self.last_fetched_url = ""
        self.format_fetch_after_id: str | None = None
        self._last_codec_fallback_notice: tuple[str, str, str] | None = None
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
        self.title_override_var = tk.StringVar(value="")
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = tk.StringVar(value="Idle")
        self._last_status_logged = self.status_var.get()
        self.simple_state_var = tk.StringVar(value="Idle")
        self.progress_pct_var = tk.StringVar(value="0.0%")
        self.progress_speed_var = tk.StringVar(value="—")
        self.progress_eta_var = tk.StringVar(value="—")

        self.status_var.trace_add("write", lambda *_: self._on_status_change())

        self._build_ui()
        self._init_visibility_helpers()
        self.url_var.trace_add("write", lambda *_: self._on_url_change())
        self._update_controls_state()
        self._poll_log_queue()

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

    def _set_grid_mapped(self, widget: tk.Widget, mapped: bool) -> None:
        if mapped:
            if not widget.winfo_ismapped():
                widget.grid()
        else:
            if widget.winfo_ismapped():
                widget.grid_remove()

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
        entry_border = palette["entry_border"]

        self.header_bar = ttk.Frame(self.root, padding=6, style="Card.TFrame")
        self.header_bar.grid(column=0, row=0, sticky="ew")
        self.header_bar.columnconfigure(0, weight=1)
        ttk.Label(
            self.header_bar,
            text="yt-dlp-gui",
            style="Title.TLabel",
            font=fonts["title"],
        ).grid(column=0, row=0, sticky="w")
        logs_wrap = ttk.Frame(self.header_bar, style="Card.TFrame", padding=0)
        logs_wrap.grid(column=1, row=0, sticky="e")
        self.logs_button = ttk.Button(
            logs_wrap, text="Logs", command=self._toggle_log_sidebar
        )
        self.logs_button.grid(column=0, row=0, sticky="e")
        # Unread indicator (keeps its space so the button doesn't shift).
        self._logs_dot = tk.Canvas(
            logs_wrap,
            width=10,
            height=10,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            background=palette["base_bg"],
        )
        self._logs_dot.grid(column=1, row=0, padx=(6, 0), sticky="e")
        self._logs_dot_item = self._logs_dot.create_oval(
            2, 2, 8, 8, fill="#dc2626", outline="#dc2626", state="hidden"
        )

        self.header_sep = ttk.Separator(self.root, orient="horizontal")
        self.header_sep.grid(column=0, row=1, sticky="ew")

        scroll = widgets.ScrollableFrame(self.root, padding=4, bg=palette["base_bg"])
        scroll.grid(column=0, row=2, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        main = scroll.content
        main.columnconfigure(1, weight=1)

        options = ttk.Frame(main, padding=6, style="Card.TFrame")
        options.grid(column=0, row=0, columnspan=2, sticky="ew", pady=(0, 3))
        options.columnconfigure(1, weight=1)
        ttk.Label(
            options,
            text="Download Options",
            style="Subheader.TLabel",
            font=fonts["subheader"],
        ).grid(column=0, row=0, columnspan=2, sticky="w", pady=(0, 3))

        ttk.Label(options, text="Video URL").grid(
            column=0, row=1, sticky="w", padx=(0, 8), pady=2
        )
        url_frame = ttk.Frame(options)
        url_frame.grid(column=1, row=1, sticky="ew", pady=2)
        url_frame.columnconfigure(0, weight=1)
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, style="Dark.TEntry")
        url_entry.grid(column=0, row=0, sticky="ew")
        ttk.Button(url_frame, text="Paste", command=self._paste_url).grid(
            column=1, row=0, padx=(8, 0)
        )
        url_entry.focus()

        ttk.Label(options, text="Output title").grid(
            column=0, row=2, sticky="w", padx=(0, 8), pady=2
        )
        self.title_entry = ttk.Entry(
            options, textvariable=self.title_override_var, style="Dark.TEntry"
        )
        self.title_entry.grid(column=1, row=2, sticky="ew", pady=2)
        self._init_title_placeholder()

        type_row = ttk.Frame(options)
        type_row.grid(column=0, row=3, columnspan=2, sticky="ew", pady=2)
        type_row.columnconfigure(1, weight=1)
        ttk.Label(type_row, text="Content Type").grid(
            column=0, row=0, sticky="w", padx=(0, 8)
        )
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
        self.container_label.grid(column=0, row=4, sticky="w", padx=(0, 8), pady=2)
        container_row = ttk.Frame(options)
        container_row.grid(column=1, row=4, sticky="ew", pady=2)
        container_row.columnconfigure(0, weight=1)
        self.container_combo = ttk.Combobox(
            container_row,
            textvariable=self.format_filter_var,
            values=["mp4", "webm"],
            state="readonly",
            width=10,
        )
        self.container_combo.grid(column=0, row=0, sticky="ew")
        self.convert_mp4_inline_label = ttk.Label(container_row, text="Convert to MP4")
        self.convert_mp4_inline_label.grid(column=1, row=0, padx=(12, 6), sticky="e")
        self.convert_mp4_check = ttk.Checkbutton(
            container_row,
            text="",
            variable=self.convert_to_mp4_var,
        )
        self.convert_mp4_check.grid(column=2, row=0, sticky="e")
        # Tooltip: old inline explanation text from the previous layout.
        widgets.Tooltip(
            self.root,
            self.convert_mp4_check,
            "Re-encodes WebM to MP4 after download (slower, lossy)",
        )
        self.format_filter_var.trace_add(
            "write",
            lambda *_: (self._apply_mode_formats(), self._update_controls_state()),
        )

        self.codec_label = ttk.Label(options, text="Codec")
        self.codec_label.grid(column=0, row=5, sticky="w", padx=(0, 8), pady=2)
        self.codec_combo = ttk.Combobox(
            options,
            textvariable=self.codec_filter_var,
            values=["avc1 (H.264)", "av01 (AV1)"],
            state="readonly",
            width=15,
        )
        self.codec_combo.grid(column=1, row=5, sticky="ew", pady=2)
        self.codec_filter_var.trace_add(
            "write",
            lambda *_: (self._apply_mode_formats(), self._update_controls_state()),
        )

        self.format_label = ttk.Label(options, text="Format")
        self.format_label.grid(column=0, row=6, sticky="w", padx=(0, 8), pady=2)
        self.format_combo = ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=self.format_labels,
            state="readonly",
        )
        self.format_combo.grid(column=1, row=6, sticky="ew", pady=2)

        ttk.Label(options, text="Output folder").grid(
            column=0, row=7, sticky="w", padx=(0, 8), pady=2
        )
        output_frame = ttk.Frame(options)
        output_frame.grid(column=1, row=7, sticky="ew", pady=(1, 0))
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
        ttk.Button(output_frame, text="Browse...", command=self._pick_folder).grid(
            column=1, row=0, padx=(8, 0), sticky="e"
        )

        sep2 = ttk.Separator(main, orient="horizontal")
        sep2.grid(column=0, row=1, columnspan=2, sticky="ew", pady=(1, 1))

        controls = ttk.Frame(main, padding=6, style="Card.TFrame")
        controls.grid(column=0, row=2, columnspan=2, sticky="ew", pady=3)
        controls.columnconfigure(0, weight=1)
        ttk.Label(
            controls, text="Controls", style="Subheader.TLabel", font=fonts["subheader"]
        ).grid(column=0, row=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Label(controls, textvariable=self.simple_state_var).grid(
            column=0, row=1, sticky="w"
        )
        self.start_button = ttk.Button(
            controls,
            text="Start download",
            command=self._on_start,
            style="Accent.TButton",
        )
        self.start_button.grid(column=1, row=1, sticky="e")

        progress_frame = ttk.Frame(controls, padding=3, style="Card.TFrame")
        progress_frame.grid(column=0, row=2, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Label(
            progress_frame,
            text="Progress",
            style="Subheader.TLabel",
            font=fonts["subheader"],
        ).grid(column=0, row=0, sticky="w", pady=(0, 3))
        summary = ttk.Frame(progress_frame, padding=0, style="Card.TFrame")
        summary.grid(column=0, row=1, sticky="ew")
        ttk.Label(summary, text="Progress").grid(
            column=0, row=0, sticky="w", padx=(0, 6)
        )
        ttk.Label(summary, textvariable=self.progress_pct_var).grid(
            column=1, row=0, sticky="w"
        )
        ttk.Label(summary, text="Speed").grid(column=2, row=0, sticky="w", padx=(10, 6))
        ttk.Label(summary, textvariable=self.progress_speed_var).grid(
            column=3, row=0, sticky="w"
        )
        ttk.Label(summary, text="ETA").grid(column=4, row=0, sticky="w", padx=(10, 6))
        ttk.Label(summary, textvariable=self.progress_eta_var).grid(
            column=5, row=0, sticky="w"
        )
        summary.columnconfigure(5, weight=1)

        self._build_log_sidebar(
            palette=palette, text_fg=text_fg, entry_border=entry_border, fonts=fonts
        )

        self.root.bind("<Configure>", self._on_root_configure, add=True)
        self._on_root_configure(tk.Event())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_log_sidebar(
        self,
        *,
        palette: dict[str, str],
        text_fg: str,
        entry_border: str,
        fonts: dict[str, tuple],
    ) -> None:
        # Use a bordered frame for separation (instead of a colored "shadow strip").
        self.log_sidebar = ttk.Frame(self.root, style="OutputPath.TFrame", padding=6)
        self.log_sidebar.place_forget()

        header = ttk.Frame(self.log_sidebar, style="Card.TFrame", padding=0)
        header.grid(column=0, row=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header, text="Logs", style="Subheader.TLabel", font=fonts["subheader"]
        ).grid(column=0, row=0, sticky="w")
        ttk.Button(header, text="Clear", command=self._clear_logs).grid(
            column=1, row=0, sticky="e"
        )

        body = ttk.Frame(self.log_sidebar, style="Card.TFrame", padding=0)
        body.grid(column=0, row=1, sticky="nsew")
        self.log_sidebar.columnconfigure(0, weight=1)
        self.log_sidebar.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            body,
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
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(
            yscrollcommand=lambda f, l: self._autohide_text_scrollbar(scrollbar, f, l)
        )
        self.log_text.grid(column=0, row=0, sticky="nsew")
        scrollbar.grid(column=1, row=0, sticky="ns")
        scrollbar.grid_remove()

    def _clear_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._set_logs_unread(False)

    def _set_logs_unread(self, unread: bool) -> None:
        self._logs_unread = unread
        if not hasattr(self, "_logs_dot"):
            return
        state = "normal" if unread else "hidden"
        try:
            self._logs_dot.itemconfigure(self._logs_dot_item, state=state)
        except Exception:
            pass

    def _autohide_text_scrollbar(
        self, scrollbar: ttk.Scrollbar, first: str, last: str
    ) -> None:
        """Proxy yscrollcommand that hides the scrollbar when not needed."""
        scrollbar.set(first, last)
        try:
            f = float(first)
            l = float(last)
        except Exception:
            return
        should_show = not (f <= 0.0 and l >= 1.0)
        if should_show:
            if not scrollbar.winfo_ismapped():
                scrollbar.grid()
        else:
            if scrollbar.winfo_ismapped():
                scrollbar.grid_remove()

    def _toggle_log_sidebar(self) -> None:
        if self._log_sidebar_open:
            self._close_log_sidebar()
        else:
            self._open_log_sidebar()

    def _open_log_sidebar(self) -> None:
        self._log_sidebar_open = True
        self._recompute_log_sidebar_target()
        if not self.log_sidebar.winfo_ismapped():
            y, h = self._log_sidebar_y_and_height()
            self.log_sidebar.place(
                relx=1.0,
                x=-self._log_sidebar_margin,
                y=y,
                anchor="ne",
                width=1,
                height=h,
            )
        # Keep the header (and Log button) above the overlay.
        self.header_bar.lift()
        self._set_logs_unread(False)
        self._start_log_sidebar_animation()

    def _close_log_sidebar(self) -> None:
        self._log_sidebar_open = False
        self._log_sidebar_width_target = 0
        self._start_log_sidebar_animation()

    def _recompute_log_sidebar_target(self) -> None:
        width = self.root.winfo_width()
        if width <= 1:
            return
        max_width = max(200, width - (self._log_sidebar_margin * 2))
        self._log_sidebar_width_target = min(
            420, max(260, min(max_width, int(width * 0.42)))
        )

    def _log_sidebar_y_and_height(self) -> tuple[int, int]:
        root_h = self.root.winfo_height()
        if root_h <= 1:
            return (0, 1)
        header_h = self.header_bar.winfo_height() if hasattr(self, "header_bar") else 0
        sep_h = self.header_sep.winfo_height() if hasattr(self, "header_sep") else 0
        y = int(header_h + sep_h + self._log_sidebar_margin)
        y = max(0, min(root_h - 1, y))
        h = max(1, root_h - y - self._log_sidebar_margin)
        return (y, h)

    def _start_log_sidebar_animation(self) -> None:
        if self._log_sidebar_after_id is None:
            self._log_sidebar_tick()

    def _log_sidebar_tick(self) -> None:
        target = float(self._log_sidebar_width_target)
        # Ease width; right edge stays fixed (anchor="ne"), so it opens right-to-left.
        ease = 0.28
        delta = target - self._log_sidebar_width_current
        if abs(delta) < 0.8:
            self._log_sidebar_width_current = target
        else:
            self._log_sidebar_width_current += delta * ease

        w = int(round(self._log_sidebar_width_current))
        if w <= 0:
            self.log_sidebar.place_forget()
            self._log_sidebar_after_id = None
            self._log_sidebar_width_current = 0.0
            return

        y, h = self._log_sidebar_y_and_height()
        self.log_sidebar.place_configure(
            relx=1.0,
            x=-self._log_sidebar_margin,
            y=y,
            anchor="ne",
            width=w,
            height=h,
        )
        self.log_sidebar.lift()
        self.header_bar.lift()

        if w == int(round(target)):
            self._log_sidebar_after_id = None
            return

        self._log_sidebar_after_id = self.root.after(
            SIDEBAR_ANIM_MS, self._log_sidebar_tick
        )

    def _on_root_configure(self, _event: tk.Event) -> None:
        if getattr(_event, "widget", self.root) is not self.root:
            return

        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        try:
            from tkinter import font as tkfont

            line_px = tkfont.nametofont("TkFixedFont").metrics("linespace") or 16
        except Exception:
            line_px = 16

        compact = height < 720
        wraplength = max(260, width - 120)
        log_target_px = int(height * (0.25 if compact else 0.33))
        log_min = 4 if compact else 6
        log_max = 12 if compact else 18
        log_lines = max(log_min, min(log_max, max(1, log_target_px // line_px)))
        self._layout_target = (wraplength, log_lines)
        if self._layout_anim_after_id is None:
            self._layout_tick()

        if self._log_sidebar_open:
            self._recompute_log_sidebar_target()
            if self._log_sidebar_after_id is None:
                # Update size immediately while dragging the window.
                y, h = self._log_sidebar_y_and_height()
                self.log_sidebar.place_configure(
                    relx=1.0,
                    x=-self._log_sidebar_margin,
                    y=y,
                    anchor="ne",
                    width=self._log_sidebar_width_target,
                    height=h,
                )
                self.header_bar.lift()

    def _layout_tick(self) -> None:
        if not self._layout_target:
            self._layout_anim_after_id = None
            return

        if self._layout_current is None:
            self._layout_current = [float(v) for v in self._layout_target]

        # Easing factor: higher = snappier, lower = smoother.
        ease = 0.35
        done = True
        for idx, target in enumerate(self._layout_target):
            current = self._layout_current[idx]
            delta = float(target) - current
            if abs(delta) > 0.01:
                self._layout_current[idx] = current + (delta * ease)
                done = False

        wraplength = int(round(self._layout_current[0]))
        log_lines = int(round(self._layout_current[1]))

        applied = (wraplength, log_lines)
        if applied != self._layout_last_applied:
            self._layout_last_applied = applied
            try:
                self.log_text.configure(height=log_lines)
            except tk.TclError:
                pass

        if done:
            self._layout_current = None
            self._layout_anim_after_id = None
            return

        # ~60fps.
        self._layout_anim_after_id = self.root.after(LAYOUT_ANIM_MS, self._layout_tick)

    def _pick_folder(self) -> None:
        chosen = filedialog.askdirectory()
        if chosen:
            self.output_dir_var.set(chosen)

    def _init_title_placeholder(self) -> None:
        self._title_placeholder_text = "Optional — leave blank for default title"
        self._title_placeholder_active = False

        def on_focus_in(_event: tk.Event) -> None:
            if not self._title_placeholder_active:
                return
            self._title_placeholder_active = False
            self.title_entry.configure(style="Dark.TEntry")
            self.title_override_var.set("")

        def on_focus_out(_event: tk.Event) -> None:
            if (self.title_override_var.get() or "").strip():
                return
            self._title_placeholder_active = True
            self.title_entry.configure(style="Placeholder.Dark.TEntry")
            self.title_override_var.set(self._title_placeholder_text)

        self.title_entry.bind("<FocusIn>", on_focus_in, add=True)
        self.title_entry.bind("<FocusOut>", on_focus_out, add=True)

        # Initialize placeholder if empty.
        if not (self.title_override_var.get() or "").strip():
            on_focus_out(tk.Event())

    def _on_status_change(self) -> None:
        value = (self.status_var.get() or "").strip()
        if not value or value == self._last_status_logged:
            return
        self._last_status_logged = value
        self._log(f"[status] {value}")

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
            self.format_fetch_after_id = self.root.after(
                FETCH_DEBOUNCE_MS, self._start_fetch_formats
            )

    def _start_fetch_formats(self, force: bool = False) -> None:
        url = self.url_var.get().strip()
        if not url or self.is_downloading or self.is_fetching_formats:
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
                # self.status_var.set("Formats failed to load. Check URL or network.")
            self.video_format_labels = []
            self.video_format_lookup = {}
            self.audio_format_labels = []
            self.audio_format_lookup = {}
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
            if notice_key != self._last_codec_fallback_notice:
                self._last_codec_fallback_notice = notice_key
                self._log(f"[info] {msg}")
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
        show_container = (
            url_present and has_formats_data and not self.is_fetching_formats
        )
        self._set_widget_visible(self.container_label, show_container)
        self._set_widget_visible(self.container_combo, show_container)
        self._set_combobox_enabled(self.container_combo, show_container)

        # Codec chooser
        show_codec = (
            url_present
            and has_formats_data
            and filter_chosen
            and not self.is_fetching_formats
        )
        self._set_widget_visible(self.codec_label, show_codec)
        self._set_widget_visible(self.codec_combo, show_codec)
        self._set_combobox_enabled(self.codec_combo, show_codec)

        # Convert checkbox only relevant when container is webm.
        show_convert = (
            url_present
            and has_formats_data
            and filter_chosen
            and self.format_filter_var.get() == "webm"
        )
        if show_convert:
            self._set_grid_mapped(self.convert_mp4_inline_label, True)
            self._set_grid_mapped(self.convert_mp4_check, True)
            self.convert_mp4_check.state(["!disabled"])
        else:
            self.convert_to_mp4_var.set(False)
            self.convert_mp4_check.state(["disabled"])
            self._set_grid_mapped(self.convert_mp4_inline_label, False)
            self._set_grid_mapped(self.convert_mp4_check, False)

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
        self._set_combobox_enabled(self.format_combo, show_format)

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

    _ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

    def _strip_ansi(self, text: str) -> str:
        return self._ANSI_RE.sub("", text)

    def _append_log(self, message: str) -> None:
        message = self._strip_ansi(message)
        if not self._log_sidebar_open:
            self._set_logs_unread(True)
        # All output goes to the Log sidebar; progress numbers are shown above.
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _reset_progress_summary(self) -> None:
        self.progress_pct_var.set("0.0%")
        self.progress_speed_var.set("—")
        self.progress_eta_var.set("—")
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        if self._progress_anim_after_id:
            try:
                self.root.after_cancel(self._progress_anim_after_id)
            except Exception:
                pass
            self._progress_anim_after_id = None

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
        if not self.format_lookup:
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
        self._clear_log()
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
        fmt_info = self.format_lookup.get(fmt_label)
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
        if self._layout_anim_after_id:
            try:
                self.root.after_cancel(self._layout_anim_after_id)
            except Exception:
                pass
        if self._progress_anim_after_id:
            try:
                self.root.after_cancel(self._progress_anim_after_id)
            except Exception:
                pass
        if self._log_sidebar_after_id:
            try:
                self.root.after_cancel(self._log_sidebar_after_id)
            except Exception:
                pass
        self.root.destroy()


def main() -> None:
    YtDlpGui().root.mainloop()


if __name__ == "__main__":
    main()
