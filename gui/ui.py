from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import styles, widgets
from .log_sidebar import LogSidebar


def init_title_placeholder(app: object) -> None:
    title_entry = getattr(app, "title_entry")
    title_override_var = getattr(app, "title_override_var")

    placeholder_text = "Optional — leave blank for default title"
    setattr(app, "_title_placeholder_active", False)

    def on_focus_in(_event: tk.Event) -> None:
        if not getattr(app, "_title_placeholder_active", False):
            return
        setattr(app, "_title_placeholder_active", False)
        title_entry.configure(style="Dark.TEntry")
        title_override_var.set("")

    def on_focus_out(_event: tk.Event) -> None:
        if (title_override_var.get() or "").strip():
            return
        setattr(app, "_title_placeholder_active", True)
        title_entry.configure(style="Placeholder.Dark.TEntry")
        title_override_var.set(placeholder_text)

    title_entry.bind("<FocusIn>", on_focus_in, add=True)
    title_entry.bind("<FocusOut>", on_focus_out, add=True)

    if not (title_override_var.get() or "").strip():
        on_focus_out(tk.Event())


def build_ui(app: object) -> LogSidebar:
    root: tk.Tk = getattr(app, "root")

    require_plex = os.getenv("YTDLP_GUI_REQUIRE_PLEX_MONO") == "1"
    warn_missing_font = os.getenv("YTDLP_GUI_WARN_MISSING_FONT") == "1"
    try:
        palette = styles.apply_theme(root, require_plex_mono=require_plex)
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

    header_bar = ttk.Frame(root, padding=6, style="Card.TFrame")
    header_bar.grid(column=0, row=0, sticky="ew")
    header_bar.columnconfigure(0, weight=1)
    setattr(app, "header_bar", header_bar)

    ttk.Label(
        header_bar,
        text="yt-dlp-gui",
        style="Title.TLabel",
        font=fonts["title"],
    ).grid(column=0, row=0, sticky="w")

    logs_wrap = ttk.Frame(header_bar, style="Card.TFrame", padding=0)
    logs_wrap.grid(column=1, row=0, sticky="e")

    header_sep = ttk.Separator(root, orient="horizontal")
    header_sep.grid(column=0, row=1, sticky="ew")
    setattr(app, "header_sep", header_sep)

    scroll = widgets.ScrollableFrame(root, padding=4, bg=palette["base_bg"])
    scroll.grid(column=0, row=2, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)
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
    url_entry = ttk.Entry(url_frame, textvariable=getattr(app, "url_var"), style="Dark.TEntry")
    url_entry.grid(column=0, row=0, sticky="ew")
    ttk.Button(url_frame, text="Paste", command=getattr(app, "_paste_url")).grid(
        column=1, row=0, padx=(8, 0)
    )
    url_entry.focus()

    ttk.Label(options, text="Output title").grid(
        column=0, row=2, sticky="w", padx=(0, 8), pady=2
    )
    title_entry = ttk.Entry(
        options, textvariable=getattr(app, "title_override_var"), style="Dark.TEntry"
    )
    title_entry.grid(column=1, row=2, sticky="ew", pady=2)
    setattr(app, "title_entry", title_entry)
    init_title_placeholder(app)

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
        variable=getattr(app, "mode_var"),
        value="video",
        command=getattr(app, "_on_mode_change"),
    ).grid(column=0, row=0, padx=(0, 12))
    ttk.Radiobutton(
        mode_frame,
        text="Audio Only",
        variable=getattr(app, "mode_var"),
        value="audio",
        command=getattr(app, "_on_mode_change"),
    ).grid(column=1, row=0)

    container_label = ttk.Label(options, text="Container")
    container_label.grid(column=0, row=4, sticky="w", padx=(0, 8), pady=2)
    setattr(app, "container_label", container_label)

    container_row = ttk.Frame(options)
    container_row.grid(column=1, row=4, sticky="ew", pady=2)
    container_row.columnconfigure(0, weight=1)
    container_combo = ttk.Combobox(
        container_row,
        textvariable=getattr(app, "format_filter_var"),
        values=[],
        state="readonly",
        width=10,
    )
    container_combo.grid(column=0, row=0, sticky="ew")
    setattr(app, "container_combo", container_combo)

    convert_mp4_inline_label = ttk.Label(container_row, text="Convert to MP4")
    convert_mp4_inline_label.grid(column=1, row=0, padx=(12, 6), sticky="e")
    setattr(app, "convert_mp4_inline_label", convert_mp4_inline_label)

    convert_mp4_check = ttk.Checkbutton(
        container_row,
        text="",
        variable=getattr(app, "convert_to_mp4_var"),
    )
    convert_mp4_check.grid(column=2, row=0, sticky="e")
    setattr(app, "convert_mp4_check", convert_mp4_check)

    widgets.Tooltip(
        root,
        convert_mp4_check,
        "Re-encodes WebM to MP4 after download (slower, lossy)",
    )
    getattr(app, "format_filter_var").trace_add(
        "write",
        lambda *_: (getattr(app, "_apply_mode_formats")(), getattr(app, "_update_controls_state")()),
    )

    codec_label = ttk.Label(options, text="Codec")
    codec_label.grid(column=0, row=5, sticky="w", padx=(0, 8), pady=2)
    setattr(app, "codec_label", codec_label)

    codec_combo = ttk.Combobox(
        options,
        textvariable=getattr(app, "codec_filter_var"),
        values=["avc1 (H.264)", "av01 (AV1)"],
        state="readonly",
        width=15,
    )
    codec_combo.grid(column=1, row=5, sticky="ew", pady=2)
    setattr(app, "codec_combo", codec_combo)
    getattr(app, "codec_filter_var").trace_add(
        "write",
        lambda *_: (getattr(app, "_apply_mode_formats")(), getattr(app, "_update_controls_state")()),
    )

    format_label = ttk.Label(options, text="Format")
    format_label.grid(column=0, row=6, sticky="w", padx=(0, 8), pady=2)
    setattr(app, "format_label", format_label)

    format_combo = ttk.Combobox(
        options,
        textvariable=getattr(app, "format_var"),
        values=getattr(app, "formats").filtered_labels,
        state="readonly",
    )
    format_combo.grid(column=1, row=6, sticky="ew", pady=2)
    setattr(app, "format_combo", format_combo)

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
        textvariable=getattr(app, "output_dir_var"),
        anchor="w",
        style="OutputPath.TLabel",
    ).grid(column=0, row=0, sticky="ew")
    ttk.Button(output_frame, text="Browse...", command=getattr(app, "_pick_folder")).grid(
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
    ttk.Label(controls, textvariable=getattr(app, "simple_state_var")).grid(
        column=0, row=1, sticky="w"
    )
    buttons = ttk.Frame(controls, style="Card.TFrame", padding=0)
    buttons.grid(column=1, row=1, sticky="e")

    start_button = ttk.Button(
        buttons,
        text="Start download",
        command=getattr(app, "_on_start"),
        style="Accent.TButton",
    )
    start_button.grid(column=0, row=0, sticky="e")
    setattr(app, "start_button", start_button)

    cancel_button = ttk.Button(
        buttons,
        text="Cancel",
        command=getattr(app, "_on_cancel"),
    )
    cancel_button.grid(column=1, row=0, sticky="e", padx=(8, 0))
    setattr(app, "cancel_button", cancel_button)

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
    ttk.Label(summary, text="Progress").grid(column=0, row=0, sticky="w", padx=(0, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_pct_var")).grid(
        column=1, row=0, sticky="w"
    )
    ttk.Label(summary, text="Speed").grid(column=2, row=0, sticky="w", padx=(10, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_speed_var")).grid(
        column=3, row=0, sticky="w"
    )
    ttk.Label(summary, text="ETA").grid(column=4, row=0, sticky="w", padx=(10, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_eta_var")).grid(
        column=5, row=0, sticky="w"
    )
    summary.columnconfigure(5, weight=1)

    return LogSidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_wrap=logs_wrap,
        palette=palette,
        text_fg=text_fg,
        entry_border=entry_border,
        fonts=fonts,
    )
