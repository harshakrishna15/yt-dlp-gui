import tkinter as tk
import os
from tkinter import ttk
from tkinter import font as tkfont


def _safe_style_configure(style: ttk.Style, style_name: str, **kwargs: object) -> None:
    """Configure only options supported by the active ttk theme."""
    for key, value in kwargs.items():
        try:
            style.configure(style_name, **{key: value})
        except tk.TclError:
            continue


def _safe_style_map(style: ttk.Style, style_name: str, **kwargs: object) -> None:
    """Map only options supported by the active ttk theme."""
    for key, value in kwargs.items():
        try:
            style.map(style_name, **{key: value})
        except tk.TclError:
            continue


def _theme_image_cache(root: tk.Tk) -> list[tk.PhotoImage]:
    cache = getattr(root, "_ytdlp_gui_theme_images", None)
    if cache is None:
        cache = []
        setattr(root, "_ytdlp_gui_theme_images", cache)
    return cache


def _make_rect_border_image(
    root: tk.Tk,
    *,
    fill: str,
    border: str,
    size: int = 7,
) -> tk.PhotoImage:
    """Create a simple solid rectangle with a 1px border (connected corners)."""
    size = max(3, int(size))
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put(fill, to=(0, 0, size, size))
    img.put(border, to=(0, 0, size, 1))  # top
    img.put(border, to=(0, size - 1, size, size))  # bottom
    img.put(border, to=(0, 0, 1, size))  # left
    img.put(border, to=(size - 1, 0, size, size))  # right
    return img


def _make_solid_image(root: tk.Tk, *, fill: str, size: int = 7) -> tk.PhotoImage:
    """Create a simple solid rectangle (no border)."""
    size = max(3, int(size))
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put(fill, to=(0, 0, size, size))
    return img


def _pick_first_existing(
    candidates: tuple[str, ...], available: set[str]
) -> str | None:
    for name in candidates:
        if name in available:
            return name
    return None


def _apply_connected_corner_fields(
    root: tk.Tk,
    style: ttk.Style,
    *,
    fill: str,
    border: str,
    focus_border: str,
    disabled_fill: str,
    disabled_border: str,
) -> None:
    """Override Entry/Combobox field elements for clean, borderless fields."""
    available = set(style.element_names())

    entry_textarea = _pick_first_existing(("Entry.textarea", "Entry.field"), available)
    combo_textarea = _pick_first_existing(
        ("Combobox.textarea", "Combobox.textfield", "Combobox.field"), available
    )
    combo_arrow = _pick_first_existing(
        ("Combobox.downarrow", "Combobox.arrow"), available
    )

    # Padding elements vary by theme; keep optional and fall back to the textarea directly.
    entry_padding = _pick_first_existing(("Entry.padding", "Entry.border"), available)
    combo_padding = _pick_first_existing(
        ("Combobox.padding", "Combobox.border"), available
    )

    if not all((entry_textarea, combo_textarea, combo_arrow)):
        return

    cache = _theme_image_cache(root)
    normal_img = _make_solid_image(root, fill=fill)
    focus_img = _make_solid_image(root, fill=fill)
    disabled_img = _make_solid_image(root, fill=disabled_fill)
    cache.extend([normal_img, focus_img, disabled_img])

    try:
        style.element_create(
            "Ytdlp.Entry.field",
            "image",
            normal_img,
            ("focus", focus_img),
            ("disabled", disabled_img),
            border=0,
            sticky="nsew",
        )
        style.element_create(
            "Ytdlp.Combobox.field",
            "image",
            normal_img,
            ("focus", focus_img),
            ("disabled", disabled_img),
            border=0,
            sticky="nsew",
        )
    except tk.TclError:
        # Element names can only be created once per interpreter; ignore duplicates.
        pass

    # Remove theme bevels and rely on the image element for borderless fields.
    style.configure("TCombobox", relief="flat", borderwidth=0)
    style.configure("Dark.TEntry", relief="flat", borderwidth=0)
    style.configure("Placeholder.Dark.TEntry", relief="flat", borderwidth=0)

    style.layout(
        "Dark.TEntry",
        [
            (
                "Ytdlp.Entry.field",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            (entry_padding or entry_textarea),
                            {
                                "sticky": "nsew",
                                "children": (
                                    [(entry_textarea, {"sticky": "nsew"})]
                                    if entry_padding
                                    else []
                                ),
                            },
                        ),
                    ],
                },
            )
        ],
    )
    style.layout(
        "Placeholder.Dark.TEntry",
        [
            (
                "Ytdlp.Entry.field",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            (entry_padding or entry_textarea),
                            {
                                "sticky": "nsew",
                                "children": (
                                    [(entry_textarea, {"sticky": "nsew"})]
                                    if entry_padding
                                    else []
                                ),
                            },
                        ),
                    ],
                },
            )
        ],
    )
    style.layout(
        "TCombobox",
        [
            (
                "Ytdlp.Combobox.field",
                {
                    "sticky": "nsew",
                    "children": [
                        (combo_arrow, {"side": "right", "sticky": "ns"}),
                        (
                            (combo_padding or combo_textarea),
                            {
                                "sticky": "nsew",
                                "children": (
                                    [(combo_textarea, {"sticky": "nsew"})]
                                    if combo_padding
                                    else []
                                ),
                            },
                        ),
                    ],
                },
            )
        ],
    )


def _apply_connected_corner_frames(
    root: tk.Tk,
    style: ttk.Style,
    *,
    fill: str,
    border: str,
) -> None:
    """Make bordered frames draw as clean rectangles with 1px connected corners."""
    available = set(style.element_names())
    frame_padding = _pick_first_existing(("Frame.padding",), available)
    if frame_padding is None:
        return

    cache = _theme_image_cache(root)
    normal_img = _make_rect_border_image(root, fill=fill, border=border)
    cache.append(normal_img)

    try:
        style.element_create(
            "Ytdlp.Frame.border",
            "image",
            normal_img,
            border=1,
            sticky="nsew",
        )
    except tk.TclError:
        pass

    for frame_style in ("Accent.TFrame",):
        style.configure(frame_style, relief="flat", borderwidth=0)
        style.layout(
            frame_style,
            [
                (
                    "Ytdlp.Frame.border",
                    {
                        "sticky": "nsew",
                        "children": [(frame_padding, {"sticky": "nsew"})],
                    },
                )
            ],
        )


def _apply_connected_corner_buttons(
    root: tk.Tk,
    style: ttk.Style,
    *,
    normal_fill: str,
    active_fill: str,
    pressed_fill: str,
    disabled_fill: str,
) -> None:
    """Make buttons render as clean rectangles (no theme bevels)."""
    available = set(style.element_names())
    button_padding = _pick_first_existing(("Button.padding",), available)
    button_label = _pick_first_existing(("Button.label",), available)
    if button_padding is None or button_label is None:
        return

    cache = _theme_image_cache(root)
    normal_img = _make_solid_image(root, fill=normal_fill)
    active_img = _make_solid_image(root, fill=active_fill)
    pressed_img = _make_solid_image(root, fill=pressed_fill)
    disabled_img = _make_solid_image(root, fill=disabled_fill)
    cache.extend(
        [
            normal_img,
            active_img,
            pressed_img,
            disabled_img,
        ]
    )

    try:
        style.element_create(
            "Ytdlp.Button.bg",
            "image",
            normal_img,
            ("disabled", disabled_img),
            ("pressed", pressed_img),
            ("active", active_img),
            border=0,
            sticky="nsew",
        )
    except tk.TclError:
        pass

    # Remove theme bevels and rely on our image for borders/corners.
    style.configure("TButton", relief="flat", borderwidth=0)

    for button_style in ("TButton",):
        style.layout(
            button_style,
            [
                (
                    "Ytdlp.Button.bg",
                    {
                        "sticky": "nsew",
                        "children": [
                            (
                                button_padding,
                                {
                                    "sticky": "nsew",
                                    "children": [(button_label, {"sticky": "nsew"})],
                                },
                            )
                        ],
                    },
                )
            ],
        )


def _set_named_fonts(root: tk.Tk, family: str, size: int) -> None:
    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
    ):
        try:
            tkfont.nametofont(name).configure(family=family, size=size)
        except tk.TclError:
            continue


def _pick_font_family(root: tk.Tk) -> tuple[str, bool]:
    override = os.getenv("YTDLP_GUI_FONT_FAMILY")
    preferred = override or "IBM Plex Mono"
    try:
        from . import font_loader
    except Exception:
        font_loader = None

    if font_loader is not None:
        try:
            font_loader.ensure_bundled_fonts(root)
        except Exception:
            pass
        if not override and preferred == "IBM Plex Mono":
            try:
                font_loader.ensure_ibm_plex_mono(root)
            except Exception:
                pass
    families = set(tkfont.families(root))
    if preferred in families:
        return preferred, preferred == "IBM Plex Mono"
    fallback = tkfont.nametofont("TkFixedFont").actual().get("family", "monospace")
    return fallback, False


def apply_theme(root: tk.Tk, *, require_plex_mono: bool = False) -> dict[str, str]:
    """Configure ttk styles and return the palette used."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    base_bg = "#f6f1e8"
    panel_bg = base_bg
    accent = "#2b4c7e"
    text_fg = "#2a2a2a"
    entry_bg = "#fefbf5"
    entry_border = "#cbbd9f"

    font_family, using_plex_mono = _pick_font_family(root)
    if require_plex_mono and not using_plex_mono:
        raise RuntimeError(
            "IBM Plex Mono is not installed (or not visible to Tk). "
            "Install it, or set YTDLP_GUI_FONT_FAMILY to a different family."
        )

    # Keep the UI compact enough to fit on smaller laptop screens (e.g. 13" MacBooks)
    # without requiring fullscreen.
    base_size = 11
    title_size = 26
    header_size = 22
    subheader_size = 16

    _set_named_fonts(root, font_family, base_size)
    base_font = (font_family, base_size)
    header_font = (font_family, header_size, "bold")
    subheader_font = (font_family, subheader_size, "bold")
    title_font = (font_family, title_size, "bold")
    root.option_add("*Font", base_font)

    style.configure(".", background=base_bg, foreground=text_fg)
    style.configure("TFrame", background=base_bg)
    style.configure("Accent.TFrame", background=panel_bg, borderwidth=1, relief="solid")
    style.configure(
        "TLabel", background=base_bg, foreground=text_fg, padding=(0, 0), font=base_font
    )
    style.configure(
        "Title.TLabel", font=title_font, foreground=accent, background=base_bg
    )
    style.configure(
        "Header.TLabel", font=header_font, foreground=accent, background=base_bg
    )
    style.configure(
        "Subheader.TLabel", font=subheader_font, foreground=text_fg, background=base_bg
    )
    style.configure(
        "Alert.TLabel", foreground="#b42318", background=base_bg, font=base_font
    )
    style.configure("Muted.TLabel", foreground="#94a3b8", background=base_bg)
    style.configure(
        "TRadiobutton", background=base_bg, foreground=text_fg, font=base_font
    )
    style.configure(
        "TCheckbutton", background=base_bg, foreground=text_fg, font=base_font
    )

    style.configure(
        "TButton",
        padding=(8, 4),
        background=accent,
        foreground="#fdfaf5",
        borderwidth=0,
        font=base_font,
    )
    style.map(
        "TButton",
        background=[("active", "#243c63"), ("disabled", "#e5e7eb")],
        foreground=[("disabled", "#8b8b8b")],
    )
    style.configure(
        "TEntry",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=text_fg,
        insertcolor=text_fg,
        relief="flat",
        borderwidth=0,
    )
    # On some platforms/themes (notably "clam"), the entry still draws a 1px
    # outline via border colors even when borderwidth is 0.
    _safe_style_configure(
        style,
        "TEntry",
        bordercolor=entry_bg,
        lightcolor=entry_bg,
        darkcolor=entry_bg,
        focuscolor=entry_bg,
    )
    _safe_style_map(
        style,
        "TEntry",
        bordercolor=[("focus", entry_bg), ("!focus", entry_bg)],
        lightcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        darkcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        focuscolor=[("focus", entry_bg), ("!focus", entry_bg)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=text_fg,
        padding=(2, 2),
        arrowcolor=text_fg,
        relief="flat",
        borderwidth=0,
    )
    _safe_style_configure(
        style,
        "TCombobox",
        bordercolor=entry_bg,
        lightcolor=entry_bg,
        darkcolor=entry_bg,
        focuscolor=entry_bg,
    )
    _safe_style_map(
        style,
        "TCombobox",
        bordercolor=[
            ("focus", entry_bg),
            ("!focus", entry_bg),
            ("readonly", entry_bg),
        ],
        lightcolor=[
            ("focus", entry_bg),
            ("!focus", entry_bg),
            ("readonly", entry_bg),
        ],
        darkcolor=[
            ("focus", entry_bg),
            ("!focus", entry_bg),
            ("readonly", entry_bg),
        ],
        focuscolor=[
            ("focus", entry_bg),
            ("!focus", entry_bg),
            ("readonly", entry_bg),
        ],
    )
    # Ensure readonly comboboxes don't look "disabled"/greyed out.
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", entry_bg), ("disabled", "#e5e7eb")],
        background=[("readonly", entry_bg), ("disabled", "#e5e7eb")],
        foreground=[("disabled", "#8b8b8b")],
    )
    style.configure(
        "Dark.TEntry",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=text_fg,
        insertcolor=text_fg,
        relief="flat",
        borderwidth=0,
    )
    _safe_style_configure(
        style,
        "Dark.TEntry",
        bordercolor=entry_bg,
        lightcolor=entry_bg,
        darkcolor=entry_bg,
        focuscolor=entry_bg,
    )
    _safe_style_map(
        style,
        "Dark.TEntry",
        bordercolor=[("focus", entry_bg), ("!focus", entry_bg)],
        lightcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        darkcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        focuscolor=[("focus", entry_bg), ("!focus", entry_bg)],
    )
    style.configure(
        "Placeholder.Dark.TEntry",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground="#94a3b8",
        insertcolor="#94a3b8",
        relief="flat",
        borderwidth=0,
    )
    _safe_style_configure(
        style,
        "Placeholder.Dark.TEntry",
        bordercolor=entry_bg,
        lightcolor=entry_bg,
        darkcolor=entry_bg,
        focuscolor=entry_bg,
    )
    _safe_style_map(
        style,
        "Placeholder.Dark.TEntry",
        bordercolor=[("focus", entry_bg), ("!focus", entry_bg)],
        lightcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        darkcolor=[("focus", entry_bg), ("!focus", entry_bg)],
        focuscolor=[("focus", entry_bg), ("!focus", entry_bg)],
    )
    style.configure(
        "Card.TFrame",
        background=panel_bg,
        borderwidth=0,
        relief="flat",
        padding=4,
    )
    style.configure(
        "Link.TButton",
        foreground=accent,
        background=panel_bg,
        padding=(2, 2),
        borderwidth=0,
        relief="flat",
        font=base_font,
    )
    style.map(
        "Link.TButton",
        foreground=[("active", "#1f3558"), ("disabled", "#8b8b8b")],
        background=[("active", panel_bg)],
    )
    style.configure(
        "OutputPath.TFrame",
        background=panel_bg,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "OutputPath.TLabel",
        background=panel_bg,
        foreground=accent,
        padding=(0, 0),
        font=base_font,
    )

    _apply_connected_corner_fields(
        root,
        style,
        fill=entry_bg,
        border=entry_border,
        focus_border=entry_border,
        disabled_fill="#e5e7eb",
        disabled_border="#d1d5db",
    )
    _apply_connected_corner_frames(root, style, fill=panel_bg, border=entry_border)
    _apply_connected_corner_buttons(
        root,
        style,
        normal_fill=accent,
        active_fill="#243c63",
        pressed_fill="#243c63",
        disabled_fill="#e5e7eb",
    )

    return {
        "text_fg": text_fg,
        "base_bg": base_bg,
        "panel_bg": panel_bg,
        "entry_bg": entry_bg,
        "entry_border": entry_border,
        "fonts": {
            "base": base_font,
            "header": header_font,
            "subheader": subheader_font,
            "title": title_font,
        },
        "font_family": font_family,
        "using_plex_mono": using_plex_mono,
        "accent": accent,
    }
