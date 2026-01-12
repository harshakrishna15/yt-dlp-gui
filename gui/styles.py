import tkinter as tk
import os
from tkinter import ttk
from tkinter import font as tkfont


def _set_named_fonts(root: tk.Tk, family: str, size: int) -> None:
    for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont"):
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
    style.configure("TLabel", background=base_bg, foreground=text_fg, padding=(0, 0), font=base_font)
    style.configure("Title.TLabel", font=title_font, foreground=accent, background=base_bg)
    style.configure("Header.TLabel", font=header_font, foreground=accent, background=base_bg)
    style.configure("Subheader.TLabel", font=subheader_font, foreground=text_fg, background=base_bg)
    style.configure("Muted.TLabel", foreground="#94a3b8", background=base_bg)
    style.configure("TRadiobutton", background=base_bg, foreground=text_fg, font=base_font)
    style.configure("TCheckbutton", background=base_bg, foreground=text_fg, font=base_font)

    style.configure(
        "TButton",
        padding=(6, 3),
        background=accent,
        foreground="#fdfaf5",
        borderwidth=1,
        font=base_font,
    )
    style.map(
        "TButton",
        background=[("active", "#243c63"), ("disabled", "#e5e7eb")],
        foreground=[("disabled", "#8b8b8b")],
    )
    style.configure(
        "TCombobox",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=text_fg,
        padding=(2, 2),
        bordercolor=entry_border,
        lightcolor=entry_border,
        darkcolor=entry_border,
        arrowcolor=text_fg,
        relief="solid",
        borderwidth=1,
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
        bordercolor=entry_border,
        lightcolor=entry_border,
        darkcolor=entry_border,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Placeholder.Dark.TEntry",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground="#94a3b8",
        insertcolor="#94a3b8",
        bordercolor=entry_border,
        lightcolor=entry_border,
        darkcolor=entry_border,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Accent.TButton",
        foreground="#fdfaf5",
        background=accent,
        padding=(8, 4),
        borderwidth=1,
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#243c63"), ("disabled", "#e5e7eb")],
        foreground=[("disabled", "#8b8b8b")],
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
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "OutputPath.TLabel",
        background=panel_bg,
        foreground=accent,
        padding=(0, 0),
        font=base_font,
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
