from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import styles, widgets
from .history_sidebar import HistorySidebar
from .log_sidebar import LogSidebar
from .queue_sidebar import QueueSidebar
from .sidebar_host import SidebarHost, SidebarSizeSpec


class _HeaderPanelSwitcher:
    def __init__(
        self,
        *,
        panels: dict[str, object],
        buttons: dict[str, ttk.Button],
    ) -> None:
        self._panels = panels
        self._buttons = buttons
        self._active: str | None = None
        self._last_selected: str | None = None

    def bind(self) -> None:
        for name, button in self._buttons.items():
            button.configure(command=lambda n=name: self.toggle(n))
        self._set_active(None)

    def toggle(self, name: str) -> None:
        panel = self._panels[name]
        if bool(getattr(panel, "is_open")()):
            getattr(panel, "close")()
            self._set_active(None)
            return
        self._open_only(name)

    def open(self, name: str) -> None:
        self._open_only(name)

    def close_active(self) -> None:
        if self._active is None:
            return
        panel = self._panels[self._active]
        if bool(getattr(panel, "is_open")()):
            getattr(panel, "close")()
        self._set_active(None)

    def _open_only(self, name: str) -> None:
        for other_name, panel in self._panels.items():
            if other_name == name:
                continue
            getattr(panel, "close")()
        getattr(self._panels[name], "open")()
        self._set_active(name)

    def _set_active(self, name: str | None) -> None:
        self._active = name
        if name is not None:
            self._last_selected = name
        for key, button in self._buttons.items():
            if key == name:
                button.state(["pressed"])
            else:
                button.state(["!pressed"])


class _SettingsSidebar:
    def __init__(
        self,
        app: object,
        *,
        root: tk.Tk,
        header_bar: ttk.Frame,
        header_sep: ttk.Separator,
        header_button: ttk.Button,
        palette: dict[str, str],
        entry_border: str,
        fonts: dict[str, tuple],
    ) -> None:
        self.root = root
        self.button = header_button
        self._app = app
        self._fonts = fonts
        self._host = SidebarHost(
            self.root,
            header_bar=header_bar,
            header_sep=header_sep,
            palette=palette,
            entry_border=entry_border,
            size_spec=SidebarSizeSpec(width_ratio=1.0, min_width=720),
            border_width=0,
        )
        self.button.configure(command=self.toggle)
        self._build_content()

    def _build_content(self) -> None:
        content = self._host.content
        content.columnconfigure(1, weight=1)

        ttk.Label(
            content,
            text="Settings",
            style="Subheader.TLabel",
            font=self._fonts["subheader"],
        ).grid(column=0, row=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))

        subtitle_languages_label = ttk.Label(content, text="Subtitle langs")
        subtitle_languages_label.grid(column=0, row=1, sticky="w", padx=(6, 8), pady=2)
        setattr(self._app, "subtitle_languages_label", subtitle_languages_label)
        subtitle_languages_entry = ttk.Entry(
            content,
            textvariable=getattr(self._app, "subtitle_languages_var"),
            style="Dark.TEntry",
        )
        subtitle_languages_entry.grid(column=1, row=1, sticky="ew", padx=(6, 0), pady=2)
        setattr(self._app, "subtitle_languages_entry", subtitle_languages_entry)
        widgets.Tooltip(
            self.root,
            subtitle_languages_entry,
            "Comma separated subtitle languages (e.g. en,es). Leave blank for default behavior.",
        )

        subtitle_options_label = ttk.Label(content, text="Subtitle options")
        subtitle_options_label.grid(column=0, row=2, sticky="w", padx=(6, 8), pady=2)
        setattr(self._app, "subtitle_options_label", subtitle_options_label)
        subtitle_options_frame = ttk.Frame(content)
        subtitle_options_frame.grid(column=1, row=2, sticky="w", padx=(6, 0), pady=2)
        write_subtitles_check = ttk.Checkbutton(
            subtitle_options_frame,
            text="Write subtitles",
            variable=getattr(self._app, "write_subtitles_var"),
        )
        write_subtitles_check.grid(column=0, row=0, sticky="w", padx=(0, 12))
        setattr(self._app, "write_subtitles_check", write_subtitles_check)
        embed_subtitles_check = ttk.Checkbutton(
            subtitle_options_frame,
            text="Embed subtitles",
            variable=getattr(self._app, "embed_subtitles_var"),
        )
        embed_subtitles_check.grid(column=1, row=0, sticky="w")
        setattr(self._app, "embed_subtitles_check", embed_subtitles_check)

        audio_language_label = ttk.Label(content, text="Audio language")
        audio_language_label.grid(column=0, row=3, sticky="w", padx=(6, 8), pady=2)
        setattr(self._app, "audio_language_label", audio_language_label)
        audio_language_combo = ttk.Combobox(
            content,
            textvariable=getattr(self._app, "audio_language_var"),
            values=["Any"],
            state="readonly",
            style="Clean.TCombobox",
        )
        audio_language_combo.grid(column=1, row=3, sticky="ew", padx=(6, 0), pady=2)
        setattr(self._app, "audio_language_combo", audio_language_combo)
        widgets.Tooltip(
            self.root,
            audio_language_combo,
            "Pick a preferred audio language from detected tracks for this URL.",
        )

        network_label = ttk.Label(content, text="Network policy")
        network_label.grid(column=0, row=4, sticky="w", padx=(6, 8), pady=2)
        setattr(self._app, "network_label", network_label)
        network_frame = ttk.Frame(content)
        network_frame.grid(column=1, row=4, sticky="ew", padx=(6, 0), pady=2)
        network_frame.columnconfigure(0, minsize=56)
        network_frame.columnconfigure(2, minsize=56)
        network_frame.columnconfigure(4, minsize=56)
        ttk.Label(network_frame, text="Timeout").grid(column=0, row=0, sticky="w")
        timeout_entry = ttk.Entry(
            network_frame,
            textvariable=getattr(self._app, "network_timeout_var"),
            width=6,
            style="Dark.TEntry",
        )
        timeout_entry.grid(column=1, row=0, sticky="w", padx=(6, 10))
        setattr(self._app, "network_timeout_entry", timeout_entry)
        ttk.Label(network_frame, text="Retries").grid(column=2, row=0, sticky="w")
        retries_entry = ttk.Entry(
            network_frame,
            textvariable=getattr(self._app, "network_retries_var"),
            width=6,
            style="Dark.TEntry",
        )
        retries_entry.grid(column=3, row=0, sticky="w", padx=(6, 10))
        setattr(self._app, "network_retries_entry", retries_entry)
        ttk.Label(network_frame, text="Backoff").grid(column=4, row=0, sticky="w")
        backoff_entry = ttk.Entry(
            network_frame,
            textvariable=getattr(self._app, "retry_backoff_var"),
            width=6,
            style="Dark.TEntry",
        )
        backoff_entry.grid(column=5, row=0, sticky="w", padx=(6, 0))
        setattr(self._app, "retry_backoff_entry", backoff_entry)
        widgets.Tooltip(
            self.root,
            network_frame,
            "Timeout in seconds, retries count, and retry backoff in seconds.",
        )

        ui_layout_label = ttk.Label(content, text="UI layout")
        ui_layout_label.grid(column=0, row=5, sticky="w", padx=(6, 8), pady=2)
        ui_layout_combo = ttk.Combobox(
            content,
            textvariable=getattr(self._app, "ui_layout_var"),
            values=["Simple", "Classic"],
            state="readonly",
            style="Clean.TCombobox",
        )
        ui_layout_combo.grid(column=1, row=5, sticky="ew", padx=(6, 0), pady=2)
        widgets.Tooltip(
            self.root,
            ui_layout_combo,
            "Simple uses one Panel button in the header. Classic shows separate top buttons.",
        )

        actions = ttk.Frame(content, style="Card.TFrame", padding=0)
        actions.grid(column=1, row=6, sticky="e", padx=(6, 0), pady=(8, 0))
        diagnostics_button = ttk.Button(
            actions,
            text="Export diagnostics",
            command=getattr(self._app, "_export_diagnostics"),
        )
        diagnostics_button.grid(column=0, row=0, sticky="e")
        setattr(self._app, "diagnostics_button", diagnostics_button)

    def toggle(self) -> None:
        self._host.toggle()

    def open(self) -> None:
        self._host.open()

    def close(self) -> None:
        self._host.close()

    def is_open(self) -> bool:
        return self._host.is_open()

    def set_on_open(self, callback: callable | None) -> None:
        self._host.set_on_open(callback)

    def on_root_configure(self, event: tk.Event) -> None:
        self._host.on_root_configure(event)

    def shutdown(self) -> None:
        self._host.shutdown()


def build_ui(app: object) -> LogSidebar:
    root: tk.Tk = getattr(app, "root")
    if not hasattr(app, "ui_layout_var"):
        setattr(app, "ui_layout_var", tk.StringVar(value="Simple"))

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
    root.configure(background=palette["panel_bg"])

    SP_2 = 2
    SP_4 = 4
    SP_6 = 6
    SP_8 = 8
    SP_12 = 12

    header_bar = ttk.Frame(root, padding=SP_6, style="HeaderBar.TFrame")
    header_bar.grid(column=0, row=0, sticky="ew")
    header_bar.columnconfigure(0, weight=1)
    setattr(app, "header_bar", header_bar)

    brand = ttk.Frame(header_bar, style="HeaderBar.TFrame", padding=0)
    brand.grid(column=0, row=0, sticky="w")
    ttk.Label(
        brand,
        text="yt-dlp-gui",
        style="Title.TLabel",
        font=fonts["title"],
    ).grid(column=0, row=0, sticky="w")
    ttk.Label(
        brand,
        text="Simple downloads for videos, playlists, and audio.",
        style="Muted.TLabel",
    ).grid(column=0, row=1, sticky="w", pady=(SP_2, 0))

    top_actions = ttk.Frame(header_bar, style="HeaderBar.TFrame", padding=0)
    top_actions.grid(column=1, row=0, sticky="e")
    classic_switcher = ttk.Frame(top_actions, style="HeaderBar.TFrame", padding=0)
    classic_switcher.grid(column=0, row=0, sticky="e")
    simple_switcher = ttk.Frame(top_actions, style="HeaderBar.TFrame", padding=0)
    simple_switcher.grid(column=0, row=0, sticky="e")
    panel_menu_button = ttk.Menubutton(simple_switcher, text="Panel")
    panel_menu_button.grid(column=0, row=0, sticky="e")
    panel_menu = tk.Menu(panel_menu_button, tearoff=False)
    panel_menu_button.configure(menu=panel_menu)
    setattr(app, "panel_menu_button", panel_menu_button)

    header_sep = ttk.Separator(root, orient="horizontal")
    header_sep.grid(column=0, row=1, sticky="ew")
    setattr(app, "header_sep", header_sep)

    scroll = widgets.ScrollableFrame(root, padding=SP_4, bg=palette["panel_bg"])
    scroll.grid(column=0, row=2, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)
    main = scroll.content
    main.columnconfigure(0, weight=1)

    header_padx = SP_6
    label_padx = SP_6
    input_padx = SP_6
    section_gap = SP_8

    source = ttk.Frame(main, padding=SP_6, style="Card.TFrame")
    source.grid(column=0, row=0, sticky="ew", pady=(0, section_gap))
    source.columnconfigure(1, weight=1)
    ttk.Label(
        source,
        text="1. Source",
        style="Subheader.TLabel",
        font=fonts["subheader"],
    ).grid(column=0, row=0, columnspan=2, sticky="w", padx=header_padx, pady=(0, SP_4))

    url_label = ttk.Label(source, text="Video URL")
    url_label.grid(column=0, row=1, sticky="w", padx=(label_padx, SP_8), pady=SP_2)
    setattr(app, "url_label", url_label)
    url_frame = ttk.Frame(source)
    url_frame.grid(column=1, row=1, sticky="ew", padx=(input_padx, 0), pady=SP_2)
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
    paste_button.grid(column=1, row=0, padx=(SP_8, 0))
    setattr(app, "paste_button", paste_button)
    url_entry.focus()

    mixed_prompt_label = ttk.Label(source, text="Playlist")
    mixed_prompt_label.grid(
        column=0, row=2, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    setattr(app, "mixed_prompt_label", mixed_prompt_label)
    mixed_prompt_frame = ttk.Frame(source)
    mixed_prompt_frame.grid(
        column=1, row=2, sticky="ew", padx=(input_padx, 0), pady=SP_2
    )
    mixed_prompt_frame.columnconfigure(0, weight=1)
    setattr(app, "mixed_prompt_frame", mixed_prompt_frame)
    mixed_prompt_text = ttk.Label(
        mixed_prompt_frame,
        text="Download playlist or video?",
        style="Alert.TLabel",
    )
    mixed_prompt_text.grid(column=0, row=0, sticky="w")
    mixed_prompt_buttons = ttk.Frame(mixed_prompt_frame)
    mixed_prompt_buttons.grid(column=1, row=0, sticky="e", padx=(SP_8, 0))
    ttk.Button(
        mixed_prompt_buttons,
        text="Playlist",
        command=getattr(app, "_on_mixed_choose_playlist"),
    ).grid(column=0, row=0, padx=(0, SP_6))
    ttk.Button(
        mixed_prompt_buttons,
        text="Video",
        command=getattr(app, "_on_mixed_choose_video"),
    ).grid(column=1, row=0)

    playlist_label = ttk.Label(source, text="Playlist items")
    playlist_label.grid(
        column=0, row=3, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    setattr(app, "playlist_label", playlist_label)
    playlist_frame = ttk.Frame(source)
    playlist_frame.grid(
        column=1, row=3, sticky="ew", padx=(input_padx, 0), pady=SP_2
    )
    playlist_frame.columnconfigure(1, weight=1)
    setattr(app, "playlist_frame", playlist_frame)
    playlist_check = ttk.Label(playlist_frame, text="Items")
    playlist_check.grid(column=0, row=0, sticky="w", padx=(0, SP_8))
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

    preview_title_label = ttk.Label(source, text="Preview title")
    preview_title_label.grid(
        column=0, row=4, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    setattr(app, "preview_title_label", preview_title_label)
    preview_title_pill = ttk.Frame(
        source, style="OutputPath.TFrame", padding=(SP_8, SP_4)
    )
    preview_title_pill.grid(column=1, row=4, sticky="ew", padx=(input_padx, 0), pady=SP_2)
    preview_title_value = ttk.Label(
        preview_title_pill,
        textvariable=getattr(app, "preview_title_var"),
        anchor="w",
        style="OutputPath.TLabel",
    )
    preview_title_value.grid(column=0, row=0, sticky="ew")
    setattr(app, "preview_title_value", preview_title_value)

    output = ttk.Frame(main, padding=SP_6, style="Card.TFrame")
    output.grid(column=0, row=1, sticky="ew", pady=(0, section_gap))
    output.columnconfigure(0, weight=3)
    output.columnconfigure(1, weight=2)
    ttk.Label(
        output,
        text="2. Output",
        style="Subheader.TLabel",
        font=fonts["subheader"],
    ).grid(column=0, row=0, columnspan=2, sticky="w", padx=header_padx, pady=(0, SP_4))

    format_card = ttk.Frame(output, style="Card.TFrame", padding=SP_4)
    format_card.grid(column=0, row=1, sticky="nsew", padx=(0, SP_6))
    format_card.columnconfigure(1, weight=1)
    ttk.Label(format_card, text="Format setup", style="Muted.TLabel").grid(
        column=0, row=0, columnspan=2, sticky="w", padx=(SP_2, 0), pady=(0, SP_2)
    )

    save_card = ttk.Frame(output, style="Card.TFrame", padding=SP_4)
    save_card.grid(column=1, row=1, sticky="nsew")
    save_card.columnconfigure(1, weight=1)
    ttk.Label(save_card, text="Save options", style="Muted.TLabel").grid(
        column=0, row=0, columnspan=2, sticky="w", padx=(SP_2, 0), pady=(0, SP_2)
    )

    ttk.Label(format_card, text="Content Type").grid(
        column=0, row=1, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    container_label = ttk.Label(format_card, text="Container")
    container_label.grid(
        column=0, row=2, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    setattr(app, "container_label", container_label)

    mode_frame = ttk.Frame(format_card)
    mode_frame.grid(column=1, row=1, sticky="w", padx=(input_padx, 0), pady=SP_2)
    video_mode_radio = ttk.Radiobutton(
        mode_frame,
        text="Video and Audio",
        variable=getattr(app, "mode_var"),
        value="video",
        command=getattr(app, "_on_mode_change"),
    )
    video_mode_radio.grid(column=0, row=0, padx=(0, SP_12))
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

    container_row = ttk.Frame(format_card)
    container_row.grid(column=1, row=2, sticky="ew", padx=(input_padx, 0), pady=SP_2)
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
    convert_mp4_inline_label.grid(column=1, row=0, padx=(SP_12, SP_6), sticky="e")
    setattr(app, "convert_mp4_inline_label", convert_mp4_inline_label)

    convert_mp4_check = ttk.Checkbutton(
        container_row,
        text="",
        variable=getattr(app, "convert_to_mp4_var"),
    )
    convert_mp4_check.grid(column=2, row=0, sticky="e")
    setattr(app, "convert_mp4_check", convert_mp4_check)

    ttk.Label(
        format_card,
        text="Choose mode first to enable compatible format controls.",
        style="Muted.TLabel",
    ).grid(column=1, row=3, sticky="w", padx=(input_padx, 0), pady=(0, SP_2))

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

    codec_label = ttk.Label(format_card, text="Codec")
    codec_label.grid(column=0, row=4, sticky="w", padx=(label_padx, SP_8), pady=SP_2)
    setattr(app, "codec_label", codec_label)

    codec_combo = ttk.Combobox(
        format_card,
        textvariable=getattr(app, "codec_filter_var"),
        values=["avc1 (H.264)", "av01 (AV1)"],
        state="readonly",
        width=15,
    )
    codec_combo.grid(column=1, row=4, sticky="ew", padx=(input_padx, 0), pady=SP_2)
    setattr(app, "codec_combo", codec_combo)
    getattr(app, "codec_filter_var").trace_add(
        "write",
        lambda *_: (
            getattr(app, "_apply_mode_formats")(),
            getattr(app, "_update_controls_state")(),
        ),
    )

    format_label = ttk.Label(format_card, text="Format")
    format_label.grid(column=0, row=5, sticky="w", padx=(label_padx, SP_8), pady=SP_2)
    setattr(app, "format_label", format_label)

    format_combo = ttk.Combobox(
        format_card,
        textvariable=getattr(app, "format_var"),
        values=getattr(app, "formats").filtered_labels,
        state="readonly",
    )
    format_combo.grid(column=1, row=5, sticky="ew", padx=(input_padx, 0), pady=SP_2)
    setattr(app, "format_combo", format_combo)
    getattr(app, "format_var").trace_add(
        "write", lambda *_: getattr(app, "_update_controls_state")()
    )

    custom_filename_label = ttk.Label(save_card, text="File name")
    custom_filename_label.grid(
        column=0, row=1, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    setattr(app, "custom_filename_label", custom_filename_label)
    custom_filename_entry = ttk.Entry(
        save_card,
        textvariable=getattr(app, "custom_filename_var"),
        style="Dark.TEntry",
    )
    custom_filename_entry.grid(
        column=1, row=1, sticky="ew", padx=(input_padx, 0), pady=SP_2
    )
    setattr(app, "custom_filename_entry", custom_filename_entry)
    widgets.Tooltip(
        root,
        custom_filename_entry,
        "Optional single-video filename. Leave blank to use the source title.",
    )

    ttk.Label(save_card, text="Output folder").grid(
        column=0, row=2, sticky="w", padx=(label_padx, SP_8), pady=SP_2
    )
    output_frame = ttk.Frame(save_card)
    output_frame.grid(column=1, row=2, sticky="ew", padx=(input_padx, 0), pady=(SP_2, 0))
    # Keep path pill and browse button visually grouped instead of stretching apart.
    output_frame.columnconfigure(0, weight=0)
    pill = ttk.Frame(output_frame, style="OutputPath.TFrame", padding=4)
    pill.grid(column=0, row=0, sticky="w")
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
    browse_button.grid(column=1, row=0, padx=(SP_8, 0), sticky="e")
    setattr(app, "browse_button", browse_button)

    footer_sep = ttk.Separator(root, orient="horizontal")
    footer_sep.grid(column=0, row=3, sticky="ew")

    run = ttk.Frame(root, padding=SP_6, style="Card.TFrame")
    run.grid(column=0, row=4, sticky="ew")
    run.columnconfigure(0, weight=1)
    ttk.Label(
        run,
        text="3. Run",
        style="Subheader.TLabel",
        font=fonts["subheader"],
    ).grid(column=0, row=0, sticky="w", padx=header_padx, pady=(0, SP_4))
    ttk.Label(
        run,
        text="Everything is ready when you are.",
        style="Muted.TLabel",
    ).grid(column=0, row=1, sticky="w", padx=header_padx, pady=(0, SP_4))

    run_row = ttk.Frame(run, style="Card.TFrame", padding=SP_4)
    run_row.grid(column=0, row=2, sticky="ew")
    run_row.columnconfigure(0, weight=1)
    status_chip = ttk.Frame(run_row, style="OutputPath.TFrame", padding=(SP_8, SP_4))
    status_chip.grid(column=0, row=0, sticky="w", padx=(label_padx, 0))
    ttk.Label(status_chip, text="Status", style="Muted.TLabel").grid(
        column=0, row=0, sticky="w"
    )
    ttk.Label(
        status_chip,
        textvariable=getattr(app, "simple_state_var"),
        style="OutputPath.TLabel",
    ).grid(column=1, row=0, sticky="w", padx=(SP_8, 0))
    buttons = ttk.Frame(run_row, style="Card.TFrame", padding=0)
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
    add_queue_button.grid(column=1, row=0, sticky="e", padx=(SP_8, 0))
    setattr(app, "add_queue_button", add_queue_button)

    start_queue_button = ttk.Button(
        buttons,
        text="Download queue",
        command=getattr(app, "_on_start_queue"),
    )
    start_queue_button.grid(column=2, row=0, sticky="e", padx=(SP_8, 0))
    setattr(app, "start_queue_button", start_queue_button)

    cancel_button = ttk.Button(
        buttons,
        text="Cancel",
        command=getattr(app, "_on_cancel"),
    )
    cancel_button.grid(column=3, row=0, sticky="e", padx=(SP_8, 0))
    setattr(app, "cancel_button", cancel_button)

    progress_frame = ttk.Frame(run, padding=(0, SP_2), style="Card.TFrame")
    progress_frame.grid(column=0, row=3, sticky="ew", pady=(SP_4, 0))
    progress_frame.columnconfigure(0, weight=1)
    setattr(app, "progress_frame", progress_frame)
    item_row = ttk.Frame(progress_frame, style="Card.TFrame", padding=0)
    item_row.grid(column=0, row=0, sticky="ew")
    item_row.columnconfigure(1, weight=1)
    progress_item_label = ttk.Label(item_row, text="Current item", style="Muted.TLabel")
    progress_item_label.grid(column=0, row=0, sticky="w", padx=(label_padx, SP_6))
    setattr(app, "progress_item_label", progress_item_label)
    progress_item_value = ttk.Label(
        item_row, textvariable=getattr(app, "progress_item_var")
    )
    progress_item_value.grid(column=1, row=0, sticky="w")
    setattr(app, "progress_item_value", progress_item_value)
    metric_row = ttk.Frame(
        progress_frame,
        style="Card.TFrame",
        padding=(0, SP_2),
    )
    metric_row.grid(column=0, row=1, sticky="ew", pady=(SP_2, 0))
    metric_row.columnconfigure(0, weight=1)
    metric_row.columnconfigure(1, weight=1)
    metric_row.columnconfigure(2, weight=1)

    progress_line = ttk.Frame(metric_row, style="Card.TFrame", padding=0)
    progress_line.grid(column=0, row=0, sticky="w")
    ttk.Label(progress_line, text="Progress", style="Muted.TLabel").grid(
        column=0, row=0, sticky="w"
    )
    ttk.Label(
        progress_line,
        textvariable=getattr(app, "progress_pct_var"),
        style="Muted.TLabel",
    ).grid(column=1, row=0, sticky="w", padx=(SP_6, 0))

    speed_line = ttk.Frame(metric_row, style="Card.TFrame", padding=0)
    speed_line.grid(column=1, row=0, sticky="w")
    ttk.Label(speed_line, text="Speed", style="Muted.TLabel").grid(
        column=0, row=0, sticky="w"
    )
    ttk.Label(
        speed_line,
        textvariable=getattr(app, "progress_speed_var"),
        style="Muted.TLabel",
    ).grid(column=1, row=0, sticky="w", padx=(SP_6, 0))

    eta_line = ttk.Frame(metric_row, style="Card.TFrame", padding=0)
    eta_line.grid(column=2, row=0, sticky="w")
    ttk.Label(eta_line, text="ETA", style="Muted.TLabel").grid(column=0, row=0, sticky="w")
    ttk.Label(
        eta_line,
        textvariable=getattr(app, "progress_eta_var"),
        style="Muted.TLabel",
    ).grid(column=1, row=0, sticky="w", padx=(SP_6, 0))

    settings_button = ttk.Button(classic_switcher, text="Settings")
    settings_button.grid(column=0, row=0, sticky="e", padx=(0, SP_6))
    setattr(app, "settings_button", settings_button)

    queue_button = ttk.Button(classic_switcher, text="Queue")
    queue_button.grid(column=1, row=0, sticky="e", padx=(0, SP_6))

    history_button = ttk.Button(classic_switcher, text="History")
    history_button.grid(column=2, row=0, sticky="e", padx=(0, SP_6))

    logs_button_wrap = ttk.Frame(classic_switcher, style="Card.TFrame", padding=0)
    logs_button_wrap.grid(column=3, row=0, sticky="e")
    logs_button = ttk.Button(logs_button_wrap, text="Logs")
    logs_button.grid(column=0, row=0, sticky="e")

    settings_panel = _SettingsSidebar(
        app,
        root=root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_button=settings_button,
        palette=palette,
        entry_border=entry_border,
        fonts=fonts,
    )
    setattr(app, "settings_panel", settings_panel)

    queue_panel = QueueSidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_button=queue_button,
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

    history_panel = HistorySidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_button=history_button,
        palette=palette,
        text_fg=text_fg,
        entry_border=entry_border,
        fonts=fonts,
        on_open_file=getattr(app, "_open_selected_history_file"),
        on_open_folder=getattr(app, "_open_selected_history_folder"),
        on_clear=getattr(app, "_clear_download_history"),
    )
    setattr(app, "history_panel", history_panel)

    logs_panel = LogSidebar(
        root,
        header_bar=header_bar,
        header_sep=header_sep,
        header_button=logs_button,
        header_wrap=logs_button_wrap,
        palette=palette,
        text_fg=text_fg,
        entry_border=entry_border,
        fonts=fonts,
    )

    header_panel_switcher = _HeaderPanelSwitcher(
        panels={
            "settings": settings_panel,
            "queue": queue_panel,
            "history": history_panel,
            "logs": logs_panel,
        },
        buttons={
            "settings": settings_button,
            "queue": queue_button,
            "history": history_button,
            "logs": logs_button,
        },
    )
    header_panel_switcher.bind()
    setattr(app, "header_panel_switcher", header_panel_switcher)
    panel_menu.add_command(
        label="Queue",
        command=lambda: header_panel_switcher.open("queue"),
    )
    panel_menu.add_command(
        label="History",
        command=lambda: header_panel_switcher.open("history"),
    )
    panel_menu.add_command(
        label="Logs",
        command=lambda: header_panel_switcher.open("logs"),
    )
    panel_menu.add_command(
        label="Settings",
        command=lambda: header_panel_switcher.open("settings"),
    )
    panel_menu.add_separator()
    panel_menu.add_command(
        label="Hide panel",
        command=header_panel_switcher.close_active,
    )

    def _apply_header_layout(*_args: object) -> None:
        mode_raw = str(getattr(app, "ui_layout_var").get() or "").strip().lower()
        use_classic = mode_raw == "classic"
        if use_classic:
            if simple_switcher.winfo_manager():
                simple_switcher.grid_remove()
            if not classic_switcher.winfo_manager():
                classic_switcher.grid()
            return
        if classic_switcher.winfo_manager():
            classic_switcher.grid_remove()
        if not simple_switcher.winfo_manager():
            simple_switcher.grid()

    getattr(app, "ui_layout_var").trace_add("write", _apply_header_layout)
    _apply_header_layout()
    return logs_panel
