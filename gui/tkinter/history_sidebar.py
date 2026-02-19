from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from .sidebar_host import SidebarHost, SidebarSizeSpec

SIDEBAR_ANIM_MS = 16


class HistorySidebar:
    def __init__(
        self,
        root: tk.Tk,
        *,
        header_bar: ttk.Frame,
        header_sep: ttk.Separator,
        header_button: ttk.Button,
        palette: dict[str, str],
        text_fg: str,
        entry_border: str,
        fonts: dict[str, tuple],
        on_open_file: callable,
        on_open_folder: callable,
        on_clear: callable,
    ) -> None:
        self.root = root
        self.header_bar = header_bar
        self.header_sep = header_sep
        self._palette = palette
        self._text_fg = text_fg
        self._entry_border = entry_border
        self._fonts = fonts

        self._on_open_file_cb = on_open_file
        self._on_open_folder_cb = on_open_folder
        self._on_clear_cb = on_clear

        self._selected_index: int | None = None
        self._row_widgets: list[dict] = []
        self._items: list[dict] = []

        self._build_header_controls(header_button)
        self._host = SidebarHost(
            self.root,
            header_bar=self.header_bar,
            header_sep=self.header_sep,
            palette=self._palette,
            entry_border=self._entry_border,
            size_spec=SidebarSizeSpec(width_ratio=1.0, min_width=720),
            border_width=0,
            anim_ms=SIDEBAR_ANIM_MS,
        )
        self.sidebar = self._host.canvas
        self._sidebar_content = self._host.content
        self._build_sidebar()

    def _build_header_controls(self, header_button: ttk.Button) -> None:
        self.button = header_button
        self.button.configure(command=self.toggle)

    def _build_sidebar(self) -> None:
        header = ttk.Frame(self._sidebar_content, style="Card.TFrame", padding=0)
        header.grid(column=0, row=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Download History",
            style="Subheader.TLabel",
            font=self._fonts["subheader"],
        ).grid(column=0, row=0, sticky="w")
        self.clear_button = ttk.Button(header, text="Clear", command=self._on_clear_cb)
        self.clear_button.grid(column=1, row=0, sticky="e")

        list_wrap = ttk.Frame(self._sidebar_content, style="Card.TFrame", padding=0)
        list_wrap.grid(column=0, row=1, sticky="nsew")
        self._sidebar_content.columnconfigure(0, weight=1)
        self._sidebar_content.rowconfigure(1, weight=1)
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(0, weight=1)

        self.list_canvas = tk.Canvas(
            list_wrap,
            background=self._palette["panel_bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        self._scrollbar = ttk.Scrollbar(
            list_wrap, orient="vertical", command=self.list_canvas.yview
        )
        self.list_canvas.configure(
            yscrollcommand=lambda f, l: self._autohide_list_scrollbar(f, l)
        )
        self.list_canvas.grid(column=0, row=0, sticky="nsew")
        self._scrollbar.grid(column=1, row=0, sticky="ns")
        self._scrollbar.grid_remove()

        self.list_inner = ttk.Frame(self.list_canvas, style="Card.TFrame", padding=0)
        self._list_window = self.list_canvas.create_window(
            0, 0, window=self.list_inner, anchor="nw"
        )
        self.list_inner.bind("<Configure>", self._on_list_inner_configure, add=True)
        self.list_canvas.bind("<Configure>", self._on_list_canvas_configure, add=True)
        self._bind_scroll_events(self.list_canvas)
        self._bind_scroll_events(self.list_inner)

        actions = ttk.Frame(self._sidebar_content, style="Card.TFrame", padding=0)
        actions.grid(column=0, row=2, sticky="e", pady=(6, 0))
        self.open_file_button = ttk.Button(
            actions, text="Open file", command=self._open_file_selected
        )
        self.open_file_button.grid(column=0, row=0, padx=(0, 8))
        self.open_folder_button = ttk.Button(
            actions, text="Open folder", command=self._open_folder_selected
        )
        self.open_folder_button.grid(column=1, row=0)

    def _open_file_selected(self) -> None:
        if self._selected_index is None:
            return
        self._on_open_file_cb()

    def _open_folder_selected(self) -> None:
        if self._selected_index is None:
            return
        self._on_open_folder_cb()

    def _on_list_inner_configure(self, _event: tk.Event) -> None:
        try:
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        except (tk.TclError, RuntimeError):
            pass

    def _on_list_canvas_configure(self, event: tk.Event) -> None:
        try:
            self.list_canvas.itemconfigure(self._list_window, width=event.width)
            self._update_row_wrap(event.width)
        except (tk.TclError, RuntimeError):
            pass

    def _autohide_list_scrollbar(self, first: str, last: str) -> None:
        try:
            self._scrollbar.set(first, last)
        except (tk.TclError, RuntimeError):
            return
        try:
            f = float(first)
            l = float(last)
        except (TypeError, ValueError):
            return
        should_show = not (f <= 0.0 and l >= 1.0)
        if should_show:
            if not self._scrollbar.winfo_ismapped():
                self._scrollbar.grid()
        else:
            if self._scrollbar.winfo_ismapped():
                self._scrollbar.grid_remove()

    def _bind_scroll_events(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add=True)
        widget.bind("<Button-4>", self._on_mousewheel, add=True)
        widget.bind("<Button-5>", self._on_mousewheel, add=True)

    def _on_mousewheel(self, event: tk.Event) -> str:
        units = 0
        num = getattr(event, "num", None)
        if num == 4:
            units = -1
        elif num == 5:
            units = 1
        else:
            delta = int(getattr(event, "delta", 0) or 0)
            if delta == 0:
                return "break"
            if sys.platform == "darwin":
                units = -1 if delta > 0 else 1
            else:
                units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        if units != 0:
            try:
                self.list_canvas.yview_scroll(units, "units")
            except (tk.TclError, RuntimeError):
                return "break"
        return "break"

    def _update_row_wrap(self, width: int | None = None) -> None:
        if width is None:
            try:
                width = int(self.list_canvas.winfo_width())
            except (tk.TclError, RuntimeError, TypeError, ValueError):
                width = 0
        if width <= 0:
            return
        wrap = max(120, width - 24)
        for row in self._row_widgets:
            row["label"].configure(wraplength=wrap)

    def _set_selected_index(self, index: int | None) -> None:
        if self._selected_index is not None and self._selected_index < len(
            self._row_widgets
        ):
            row = self._row_widgets[self._selected_index]
            row["frame"].configure(background=self._palette["panel_bg"])
            row["label"].configure(background=self._palette["panel_bg"])
        self._selected_index = index
        if index is not None and index < len(self._row_widgets):
            row = self._row_widgets[index]
            row["frame"].configure(background=self._palette["base_bg"])
            row["label"].configure(background=self._palette["base_bg"])
        self._update_action_buttons()

    def get_selected_index(self) -> int | None:
        return self._selected_index

    def _update_action_buttons(self) -> None:
        has_items = bool(self._items)
        selected = self._selected_index is not None and self._selected_index < len(
            self._items
        )
        if has_items:
            self.clear_button.state(["!disabled"])
        else:
            self.clear_button.state(["disabled"])
        if selected:
            self.open_file_button.state(["!disabled"])
            self.open_folder_button.state(["!disabled"])
        else:
            self.open_file_button.state(["disabled"])
            self.open_folder_button.state(["disabled"])

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

    def refresh(self, items: list[dict]) -> None:
        self._items = list(items)
        for child in self.list_inner.winfo_children():
            child.destroy()
        self._row_widgets.clear()

        for idx, item in enumerate(self._items):
            ts = str(item.get("timestamp") or "").strip()
            name = str(item.get("name") or item.get("path") or "").strip()
            source = str(item.get("source_url") or "").strip()
            source_short = source[:56] + "..." if len(source) > 59 else source

            label_text = name
            if ts:
                label_text = f"{ts} | {name}"
            if source_short:
                label_text = f"{label_text}\n{source_short}"

            row = tk.Frame(self.list_inner, background=self._palette["panel_bg"])
            row.grid(column=0, row=idx, sticky="ew", pady=2)
            row.columnconfigure(0, weight=1)
            label = tk.Label(
                row,
                text=label_text,
                anchor="w",
                background=self._palette["panel_bg"],
                foreground=self._text_fg,
                justify="left",
            )
            label.grid(column=0, row=0, sticky="ew")

            row.bind("<Button-1>", lambda _event, i=idx: self._set_selected_index(i))
            label.bind("<Button-1>", lambda _event, i=idx: self._set_selected_index(i))
            row.bind(
                "<Double-Button-1>",
                lambda _event, i=idx: (self._set_selected_index(i), self._on_open_file_cb()),
            )
            label.bind(
                "<Double-Button-1>",
                lambda _event, i=idx: (self._set_selected_index(i), self._on_open_file_cb()),
            )
            self._bind_scroll_events(row)
            self._bind_scroll_events(label)

            self._row_widgets.append({"frame": row, "label": label})

        self._update_row_wrap()
        if self._selected_index is not None and self._selected_index < len(self._items):
            self._set_selected_index(self._selected_index)
        else:
            self._set_selected_index(None)
        self._update_action_buttons()

    def shutdown(self) -> None:
        self._host.shutdown()
