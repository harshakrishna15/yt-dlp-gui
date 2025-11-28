import tkinter as tk
from tkinter import ttk


def apply_theme(root: tk.Tk) -> dict[str, str]:
    """Configure ttk styles and return the palette used."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    base_bg = "#f6f1e8"
    panel_bg = "#fdfaf5"
    accent = "#2b4c7e"
    text_fg = "#2a2a2a"
    entry_bg = "#fefbf5"
    entry_border = "#cbbd9f"

    base_font = ("IBM Plex Mono", 12)
    header_font = ("IBM Plex Mono", 32, "bold")
    subheader_font = ("IBM Plex Mono", 22, "bold")
    title_font = ("IBM Plex Mono", 40, "bold")
    root.option_add("*Font", base_font)

    style.configure(".", background=base_bg, foreground=text_fg)
    style.configure("TFrame", background=base_bg)
    style.configure("Accent.TFrame", background=panel_bg, borderwidth=1, relief="solid")
    style.configure("TLabel", background=base_bg, foreground=text_fg, padding=(0, 0), font=base_font)
    style.configure("Title.TLabel", font=title_font, foreground=accent, background=base_bg)
    style.configure("Header.TLabel", font=header_font, foreground=accent, background=base_bg)
    style.configure("Subheader.TLabel", font=subheader_font, foreground=text_fg, background=base_bg)
    style.configure("Muted.TLabel", foreground="#94a3b8", background=base_bg)

    style.configure(
        "TButton",
        padding=(6, 4),
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
        "Accent.TButton",
        foreground="#fdfaf5",
        background=accent,
        padding=(10, 6),
        borderwidth=1,
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#243c63"), ("disabled", "#e5e7eb")],
        foreground=[("disabled", "#8b8b8b")],
    )
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#e5e2d8",
        background=accent,
        bordercolor="#e5e2d8",
        lightcolor=accent,
        darkcolor=accent,
    )
    style.configure(
        "Card.TFrame",
        background=panel_bg,
        borderwidth=1,
        relief="solid",
        padding=8,
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
        "accent": accent,
    }
