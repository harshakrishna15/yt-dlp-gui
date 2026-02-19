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
    """Create a solid rectangle with a 1px border (connected corners)."""
    size = max(1, int(size))
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put(fill, to=(0, 0, size, size))
    img.put(border, to=(0, 0, size, 1))  # top
    img.put(border, to=(0, size - 1, size, size))  # bottom
    img.put(border, to=(0, 0, 1, size))  # left
    img.put(border, to=(size - 1, 0, size, size))  # right
    # Force the 4 corner pixels to the border color.
    img.put(border, to=(0, 0, 1, 1))
    img.put(border, to=(size - 1, 0, size, 1))
    img.put(border, to=(0, size - 1, 1, size))
    img.put(border, to=(size - 1, size - 1, size, size))
    return img


def _make_solid_image(root: tk.Tk, *, fill: str, size: int = 7) -> tk.PhotoImage:
    """Create a simple solid rectangle (no border)."""
    size = max(3, int(size))
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put(fill, to=(0, 0, size, size))
    return img


def _make_rounded_rect_image(
    root: tk.Tk,
    *,
    fill: str,
    size: int = 11,
    radius: int = 4,
) -> tk.PhotoImage:
    """Create a rounded rectangle with transparent corners for softer buttons."""
    radius = max(1, int(radius))
    size = max((radius * 2) + 1, int(size))
    img = tk.PhotoImage(master=root, width=size, height=size)

    # Fill center bars first.
    img.put(fill, to=(radius, 0, size - radius, size))
    img.put(fill, to=(0, radius, size, size - radius))

    # Fill quarter-circle corners.
    r2 = float(radius) * float(radius)
    for y in range(radius):
        for x in range(radius):
            dx = float((radius - 1) - x)
            dy = float((radius - 1) - y)
            if (dx * dx) + (dy * dy) > r2:
                continue
            # top-left
            img.put(fill, to=(x, y, x + 1, y + 1))
            # top-right
            rx = (size - radius) + x
            img.put(fill, to=(rx, y, rx + 1, y + 1))
            # bottom-left
            by = (size - radius) + y
            img.put(fill, to=(x, by, x + 1, by + 1))
            # bottom-right
            img.put(fill, to=(rx, by, rx + 1, by + 1))
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
    if combo_padding == "Combobox.border":
        combo_padding = None

    if not all((entry_textarea, combo_textarea, combo_arrow)):
        return

    cache = _theme_image_cache(root)
    entry_normal = _make_solid_image(root, fill=fill)
    entry_focus = _make_solid_image(root, fill=fill)
    entry_disabled = _make_solid_image(root, fill=disabled_fill)
    combo_normal = _make_rect_border_image(root, fill=fill, border=border)
    combo_focus = _make_rect_border_image(root, fill=fill, border=focus_border)
    combo_disabled = _make_rect_border_image(
        root, fill=disabled_fill, border=disabled_border
    )
    cache.extend(
        [
            entry_normal,
            entry_focus,
            entry_disabled,
            combo_normal,
            combo_focus,
            combo_disabled,
        ]
    )

    try:
        style.element_create(
            "Ytdlp.Entry.field",
            "image",
            entry_normal,
            ("focus", entry_focus),
            ("disabled", entry_disabled),
            border=0,
            sticky="nsew",
        )
        style.element_create(
            "Ytdlp.Combobox.field",
            "image",
            combo_normal,
            ("focus", combo_focus),
            ("disabled", combo_disabled),
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
    text_element = combo_textarea
    if combo_textarea in ("Combobox.textfield", "Combobox.field"):
        text_element = entry_textarea or combo_textarea

    combo_layout = [
        (
            "Ytdlp.Combobox.field",
            {
                "sticky": "nsew",
                "children": [
                    (combo_arrow, {"side": "right", "sticky": "ns"}),
                    (
                        (combo_padding or text_element),
                        {
                            "sticky": "nsew",
                            "children": (
                                [(text_element, {"sticky": "nsew"})]
                                if combo_padding
                                else []
                            ),
                        },
                    ),
                ],
            },
        )
    ]
    style.layout("TCombobox", combo_layout)
    style.layout("Clean.TCombobox", combo_layout)


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

    for frame_style in ("Accent.TFrame", "Card.TFrame"):
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
    radius: int = 4,
) -> None:
    """Make buttons render as rounded, friendly surfaces without theme bevels."""
    available = set(style.element_names())
    button_padding = _pick_first_existing(("Button.padding",), available)
    button_label = _pick_first_existing(("Button.label",), available)
    if button_padding is None or button_label is None:
        return

    cache = _theme_image_cache(root)
    normal_img = _make_rounded_rect_image(root, fill=normal_fill, radius=radius)
    active_img = _make_rounded_rect_image(root, fill=active_fill, radius=radius)
    pressed_img = _make_rounded_rect_image(root, fill=pressed_fill, radius=radius)
    disabled_img = _make_rounded_rect_image(root, fill=disabled_fill, radius=radius)
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

    # Remove theme bevels and rely on our image for rounded corners.
    style.configure("TButton", relief="flat", borderwidth=0)

    for button_style in ("TButton", "TMenubutton"):
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

    # Friendly unified palette.
    base_bg = "#e3edf8"
    panel_bg = "#ffffff"
    accent = "#5a8eea"
    accent_hover = "#4d7ed5"
    accent_pressed = "#426db8"
    accent_soft = "#e9f0fb"
    text_fg = "#23364b"
    muted_fg = "#6f839e"
    # Slightly tint fields so they stand apart from white cards.
    entry_bg = "#f4f8ff"
    entry_border = "#c7d7ea"
    danger_fg = "#c2410c"

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
    style.configure("TFrame", background=panel_bg)
    style.configure("HeaderBar.TFrame", background=panel_bg, borderwidth=0, relief="flat")
    style.configure("Accent.TFrame", background=panel_bg, borderwidth=1, relief="solid")
    style.configure(
        "TLabel", background=panel_bg, foreground=text_fg, padding=(0, 0), font=base_font
    )
    style.configure(
        "Title.TLabel", font=title_font, foreground=accent, background=panel_bg
    )
    style.configure(
        "Header.TLabel", font=header_font, foreground=accent, background=panel_bg
    )
    style.configure(
        "Subheader.TLabel", font=subheader_font, foreground=text_fg, background=panel_bg
    )
    style.configure(
        "Alert.TLabel", foreground=danger_fg, background=panel_bg, font=base_font
    )
    style.configure("Muted.TLabel", foreground=muted_fg, background=panel_bg)
    style.configure(
        "TRadiobutton", background=panel_bg, foreground=text_fg, font=base_font
    )
    style.configure(
        "TCheckbutton", background=panel_bg, foreground=text_fg, font=base_font
    )

    style.configure(
        "TButton",
        padding=(12, 6),
        background=accent,
        foreground="#ffffff",
        borderwidth=0,
        font=base_font,
    )
    style.map(
        "TButton",
        background=[("active", accent_hover), ("disabled", "#e9eff6")],
        foreground=[("active", "#ffffff"), ("disabled", "#97a5b6")],
    )
    style.configure(
        "TMenubutton",
        padding=(12, 6),
        background=accent,
        foreground="#ffffff",
        borderwidth=0,
        font=base_font,
    )
    style.map(
        "TMenubutton",
        background=[("active", accent_hover), ("disabled", "#e9eff6")],
        foreground=[("active", "#ffffff"), ("disabled", "#97a5b6")],
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
    style.configure(
        "Clean.TCombobox",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=text_fg,
        padding=(2, 2),
        arrowcolor=text_fg,
        relief="flat",
        borderwidth=0,
    )
    for combo_style in ("TCombobox", "Clean.TCombobox"):
        _safe_style_configure(
            style,
            combo_style,
            bordercolor=panel_bg,
            lightcolor=panel_bg,
            darkcolor=panel_bg,
            focuscolor=panel_bg,
        )
        _safe_style_map(
            style,
            combo_style,
            bordercolor=[
                ("focus", panel_bg),
                ("!focus", panel_bg),
                ("readonly", panel_bg),
            ],
            lightcolor=[
                ("focus", panel_bg),
                ("!focus", panel_bg),
                ("readonly", panel_bg),
            ],
            darkcolor=[
                ("focus", panel_bg),
                ("!focus", panel_bg),
                ("readonly", panel_bg),
            ],
            focuscolor=[
                ("focus", panel_bg),
                ("!focus", panel_bg),
                ("readonly", panel_bg),
            ],
        )
    # Ensure readonly comboboxes don't look "disabled"/greyed out.
    for combo_style in ("TCombobox", "Clean.TCombobox"):
        style.map(
            combo_style,
            fieldbackground=[("readonly", entry_bg), ("disabled", "#eef2f7")],
            background=[("readonly", entry_bg), ("disabled", "#eef2f7")],
            foreground=[("disabled", muted_fg)],
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
        foreground=muted_fg,
        insertcolor=muted_fg,
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
        borderwidth=1,
        relief="flat",
        padding=10,
    )
    style.configure(
        "Link.TButton",
        foreground=accent,
        background=panel_bg,
        padding=(4, 2),
        borderwidth=0,
        relief="flat",
        font=base_font,
    )
    style.map(
        "Link.TButton",
        foreground=[("active", accent_hover), ("disabled", muted_fg)],
        background=[("active", panel_bg)],
    )
    style.configure(
        "OutputPath.TFrame",
        background=accent_soft,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "OutputPath.TLabel",
        background=accent_soft,
        foreground=accent,
        padding=(0, 0),
        font=base_font,
    )

    # Keep default theme combobox rendering; custom layout overrides were causing
    # persistent outlines on some platforms.
    _apply_connected_corner_frames(root, style, fill=panel_bg, border=entry_border)
    _apply_connected_corner_buttons(
        root,
        style,
        normal_fill=accent,
        active_fill=accent_hover,
        pressed_fill=accent_pressed,
        disabled_fill="#e5e7eb",
        radius=8,
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
