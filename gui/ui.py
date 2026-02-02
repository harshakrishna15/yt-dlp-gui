from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import styles, widgets
from .log_sidebar import LogSidebar
from .queue_sidebar import QueueSidebar


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
    logs_wrap.columnconfigure(0, weight=1)
    logs_wrap.columnconfigure(1, weight=1)

    header_sep = ttk.Separator(root, orient="horizontal")
    header_sep.grid(column=0, row=1, sticky="ew")
    setattr(app, "header_sep", header_sep)

    scroll = widgets.ScrollableFrame(root, padding=4, bg=palette["base_bg"])
    scroll.grid(column=0, row=2, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)
    main = scroll.content
    main.columnconfigure(1, weight=1)

    header_padx = 6
    label_padx = 6
    input_padx = 6
    options = ttk.Frame(main, padding=6, style="Card.TFrame")
    options.grid(column=0, row=0, columnspan=2, sticky="ew", pady=(0, 3))
    options.columnconfigure(1, weight=1)
    ttk.Label(
        options,
        text="Download Options",
        style="Subheader.TLabel",
        font=fonts["subheader"],
    ).grid(column=0, row=0, columnspan=2, sticky="w", padx=header_padx, pady=(0, 3))

    url_label = ttk.Label(options, text="Video URL")
    url_label.grid(column=0, row=1, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "url_label", url_label)
    url_frame = ttk.Frame(options)
    url_frame.grid(column=1, row=1, sticky="ew", padx=(input_padx, 0), pady=2)
    url_frame.columnconfigure(0, weight=1)
    url_entry = ttk.Entry(
        url_frame, textvariable=getattr(app, "url_var"), style="Dark.TEntry"
    )
    url_entry.grid(column=0, row=0, sticky="ew")

    def _select_all(_event: tk.Event) -> str:
        url_entry.selection_range(0, "end")
        url_entry.icursor("end")
        return "break"

    url_entry.bind("<Control-a>", _select_all, add=True)
    url_entry.bind("<Command-a>", _select_all, add=True)
    paste_button = ttk.Button(
        url_frame, text="Paste", command=getattr(app, "_paste_url")
    )
    paste_button.grid(column=1, row=0, padx=(8, 0))
    setattr(app, "paste_button", paste_button)
    url_entry.focus()

    mixed_prompt_label = ttk.Label(options, text="Playlist")
    mixed_prompt_label.grid(column=0, row=2, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "mixed_prompt_label", mixed_prompt_label)
    mixed_prompt_frame = ttk.Frame(options)
    mixed_prompt_frame.grid(column=1, row=2, sticky="ew", padx=(input_padx, 0), pady=2)
    mixed_prompt_frame.columnconfigure(0, weight=1)
    setattr(app, "mixed_prompt_frame", mixed_prompt_frame)
    mixed_prompt_text = ttk.Label(
        mixed_prompt_frame,
        text="Download playlist or video?",
        style="Alert.TLabel",
    )
    mixed_prompt_text.grid(column=0, row=0, sticky="w")
    mixed_prompt_buttons = ttk.Frame(mixed_prompt_frame)
    mixed_prompt_buttons.grid(column=1, row=0, sticky="e", padx=(8, 0))
    ttk.Button(
        mixed_prompt_buttons,
        text="Playlist",
        command=getattr(app, "_on_mixed_choose_playlist"),
    ).grid(column=0, row=0, padx=(0, 6))
    ttk.Button(
        mixed_prompt_buttons,
        text="Video",
        command=getattr(app, "_on_mixed_choose_video"),
    ).grid(column=1, row=0)

    playlist_label = ttk.Label(options, text="Playlist items")
    playlist_label.grid(column=0, row=3, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "playlist_label", playlist_label)
    playlist_frame = ttk.Frame(options)
    playlist_frame.grid(column=1, row=3, sticky="ew", padx=(input_padx, 0), pady=2)
    playlist_frame.columnconfigure(1, weight=1)
    setattr(app, "playlist_frame", playlist_frame)
    playlist_check = ttk.Label(playlist_frame, text="Items")
    playlist_check.grid(column=0, row=0, sticky="w", padx=(0, 10))
    playlist_items_entry = ttk.Entry(
        playlist_frame,
        textvariable=getattr(app, "playlist_items_var"),
        style="Dark.TEntry",
    )
    playlist_items_entry.grid(column=1, row=0, sticky="ew")
    setattr(app, "playlist_items_entry", playlist_items_entry)
    widgets.Tooltip(
        root,
        playlist_items_entry,
        "Optional items/ranges (e.g., 1-5,7,10-). Leave blank for full playlist.",
    )
    getattr(app, "playlist_enabled_var").trace_add(
        "write", lambda *_: getattr(app, "_update_controls_state")()
    )

    ttk.Label(options, text="Content Type").grid(
        column=0, row=4, sticky="w", padx=(label_padx, 8), pady=2
    )
    mode_frame = ttk.Frame(options)
    mode_frame.grid(column=1, row=4, sticky="w", padx=(input_padx, 0), pady=2)
    video_mode_radio = ttk.Radiobutton(
        mode_frame,
        text="Video and Audio",
        variable=getattr(app, "mode_var"),
        value="video",
        command=getattr(app, "_on_mode_change"),
    )
    video_mode_radio.grid(column=0, row=0, padx=(0, 12))
    setattr(app, "video_mode_radio", video_mode_radio)
    audio_mode_radio = ttk.Radiobutton(
        mode_frame,
        text="Audio Only",
        variable=getattr(app, "mode_var"),
        value="audio",
        command=getattr(app, "_on_mode_change"),
    )
    audio_mode_radio.grid(column=1, row=0)
    setattr(app, "audio_mode_radio", audio_mode_radio)

    container_label = ttk.Label(options, text="Container")
    container_label.grid(column=0, row=5, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "container_label", container_label)

    container_row = ttk.Frame(options)
    container_row.grid(column=1, row=5, sticky="ew", padx=(input_padx, 0), pady=2)
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
        lambda *_: (
            getattr(app, "_apply_mode_formats")(),
            getattr(app, "_update_controls_state")(),
        ),
    )

    codec_label = ttk.Label(options, text="Codec")
    codec_label.grid(column=0, row=6, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "codec_label", codec_label)

    codec_combo = ttk.Combobox(
        options,
        textvariable=getattr(app, "codec_filter_var"),
        values=["avc1 (H.264)", "av01 (AV1)"],
        state="readonly",
        width=15,
    )
    codec_combo.grid(column=1, row=6, sticky="ew", padx=(input_padx, 0), pady=2)
    setattr(app, "codec_combo", codec_combo)
    getattr(app, "codec_filter_var").trace_add(
        "write",
        lambda *_: (
            getattr(app, "_apply_mode_formats")(),
            getattr(app, "_update_controls_state")(),
        ),
    )

    format_label = ttk.Label(options, text="Format")
    format_label.grid(column=0, row=7, sticky="w", padx=(label_padx, 8), pady=2)
    setattr(app, "format_label", format_label)

    format_combo = ttk.Combobox(
        options,
        textvariable=getattr(app, "format_var"),
        values=getattr(app, "formats").filtered_labels,
        state="readonly",
    )
    format_combo.grid(column=1, row=7, sticky="ew", padx=(input_padx, 0), pady=2)
    setattr(app, "format_combo", format_combo)
    getattr(app, "format_var").trace_add(
        "write", lambda *_: getattr(app, "_update_controls_state")()
    )

    ttk.Label(options, text="Output folder").grid(
        column=0, row=8, sticky="w", padx=(label_padx, 8), pady=2
    )
    output_frame = ttk.Frame(options)
    output_frame.grid(column=1, row=8, sticky="ew", padx=(input_padx, 0), pady=(1, 0))
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
    browse_button = ttk.Button(
        output_frame, text="Browse...", command=getattr(app, "_pick_folder")
    )
    browse_button.grid(column=1, row=0, padx=(8, 0), sticky="e")
    setattr(app, "browse_button", browse_button)

    sep2 = ttk.Separator(main, orient="horizontal")
    sep2.grid(column=0, row=1, columnspan=2, sticky="ew", pady=(1, 1))

    controls = ttk.Frame(main, padding=6, style="Card.TFrame")
    controls.grid(column=0, row=2, columnspan=2, sticky="ew", pady=3)
    controls.columnconfigure(0, weight=1)
    ttk.Label(
        controls, text="Controls", style="Subheader.TLabel", font=fonts["subheader"]
    ).grid(column=0, row=0, columnspan=2, sticky="w", padx=header_padx, pady=(0, 3))
    controls_row = ttk.Frame(controls, style="Card.TFrame", padding=3)
    controls_row.grid(column=0, row=1, columnspan=2, sticky="ew")
    controls_row.columnconfigure(0, weight=1)
    ttk.Label(controls_row, textvariable=getattr(app, "simple_state_var")).grid(
        column=0, row=0, sticky="w", padx=(label_padx, 0)
    )
    buttons = ttk.Frame(controls_row, style="Card.TFrame", padding=0)
    buttons.grid(column=1, row=0, sticky="e")

    start_button = ttk.Button(
        buttons,
        text="Download",
        command=getattr(app, "_on_start"),
    )
    start_button.grid(column=0, row=0, sticky="e")
    setattr(app, "start_button", start_button)

    add_queue_button = ttk.Button(
        buttons,
        text="Add to queue",
        command=getattr(app, "_on_add_to_queue"),
    )
    add_queue_button.grid(column=1, row=0, sticky="e", padx=(8, 0))
    setattr(app, "add_queue_button", add_queue_button)

    start_queue_button = ttk.Button(
        buttons,
        text="Download queue",
        command=getattr(app, "_on_start_queue"),
    )
    start_queue_button.grid(column=2, row=0, sticky="e", padx=(8, 0))
    setattr(app, "start_queue_button", start_queue_button)

    cancel_button = ttk.Button(
        buttons,
        text="Cancel",
        command=getattr(app, "_on_cancel"),
    )
    cancel_button.grid(column=3, row=0, sticky="e", padx=(8, 0))
    setattr(app, "cancel_button", cancel_button)

    progress_frame = ttk.Frame(controls, padding=(0, 3), style="Card.TFrame")
    progress_frame.grid(column=0, row=2, columnspan=2, sticky="ew", pady=(4, 0))
    ttk.Label(
        progress_frame,
        text="Progress",
        style="Subheader.TLabel",
        font=fonts["subheader"],
    ).grid(column=0, row=0, sticky="w", padx=header_padx, pady=(0, 3))
    summary = ttk.Frame(progress_frame, padding=0, style="Card.TFrame")
    summary.grid(column=0, row=1, sticky="ew")
    summary.columnconfigure(0, minsize=90)
    summary.columnconfigure(1, weight=1)

    progress_item_label = ttk.Label(summary, text="Item")
    progress_item_label.grid(column=0, row=0, sticky="w", padx=(label_padx, 6))
    setattr(app, "progress_item_label", progress_item_label)
    progress_item_value = ttk.Label(
        summary, textvariable=getattr(app, "progress_item_var")
    )
    progress_item_value.grid(column=1, row=0, sticky="w")
    setattr(app, "progress_item_value", progress_item_value)
    ttk.Label(summary, text="Progress").grid(column=0, row=1, sticky="w", padx=(label_padx, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_pct_var")).grid(
        column=1, row=1, sticky="w"
    )
    ttk.Label(summary, text="Speed").grid(column=0, row=2, sticky="w", padx=(label_padx, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_speed_var")).grid(
        column=1, row=2, sticky="w"
    )
    ttk.Label(summary, text="ETA").grid(column=0, row=3, sticky="w", padx=(label_padx, 6))
    ttk.Label(summary, textvariable=getattr(app, "progress_eta_var")).grid(
        column=1, row=3, sticky="w"
    )

    queue_wrap = ttk.Frame(logs_wrap, style="Card.TFrame", padding=0)
    queue_wrap.grid(column=0, row=0, sticky="e", padx=(0, 6))
    logs_button_wrap = ttk.Frame(logs_wrap, style="Card.TFrame", padding=0)
    logs_button_wrap.grid(column=1, row=0, sticky="e")

    queue_panel = QueueSidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_wrap=queue_wrap,
        palette=palette,
        text_fg=text_fg,
        entry_border=entry_border,
        fonts=fonts,
        on_remove=getattr(app, "_queue_remove_selected"),
        on_move_up=getattr(app, "_queue_move_up"),
        on_move_down=getattr(app, "_queue_move_down"),
        on_clear=getattr(app, "_queue_clear"),
    )
    setattr(app, "queue_panel", queue_panel)

    logs_panel = LogSidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_wrap=logs_button_wrap,
        palette=palette,
        text_fg=text_fg,
        entry_border=entry_border,
        fonts=fonts,
    )
    queue_panel.set_on_open(logs_panel.close)
    logs_panel.set_on_open(queue_panel.close)
    return logs_panel
