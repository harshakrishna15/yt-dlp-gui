from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .sidebar_host import SidebarHost, SidebarSizeSpec

SIDEBAR_ANIM_MS = 16


class QueueSidebar:
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
        on_remove: callable,
        on_move_up: callable,
        on_move_down: callable,
        on_clear: callable,
    ) -> None:
        self.root = root
        self.header_bar = header_bar
        self.header_sep = header_sep
        self._palette = palette
        self._text_fg = text_fg
        self._entry_border = entry_border
        self._fonts = fonts

        self._on_remove_cb = on_remove
        self._on_move_up_cb = on_move_up
        self._on_move_down_cb = on_move_down
        self._on_clear_cb = on_clear

        self._selected_index: int | None = None
        self._row_widgets: list[dict] = []
        self._editable = True

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
            text="Queue",
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

    def _update_row_wrap(self, width: int | None = None) -> None:
        if width is None:
            try:
                width = int(self.list_canvas.winfo_width())
            except (tk.TclError, RuntimeError, TypeError, ValueError):
                width = 0
        if width <= 0:
            return
        wrap = max(100, width - 120)
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

    def refresh(
        self,
        items: list[dict],
        active_index: int | None = None,
        editable: bool = True,
    ) -> None:
        self._editable = editable
        if self._editable:
            self.clear_button.state(["!disabled"])
        else:
            self.clear_button.state(["disabled"])
        for child in self.list_inner.winfo_children():
            child.destroy()
        self._row_widgets.clear()
        for idx, item in enumerate(items):
            url = item.get("url", "")
            prefix = ">> " if active_index is not None and idx == active_index else ""
            settings = item.get("settings") or {}
            mode = str(settings.get("mode") or "").strip()
            container = str(settings.get("format_filter") or "").strip()
            size_text = str(settings.get("estimated_size") or "").strip()
            format_label = str(settings.get("format_label") or "").strip()

            details: list[str] = []
            if mode:
                details.append(mode)
            if container:
                details.append(container)
            if size_text:
                details.append(f"~{size_text}")

            label_text = f"{prefix}{idx + 1}. {url}"
            if details:
                label_text = f"{label_text}\n   {' | '.join(details)}"
            if format_label:
                label_text = f"{label_text}\n   {format_label}"

            row = tk.Frame(self.list_inner, background=self._palette["panel_bg"])
            row.grid(column=0, row=idx, sticky="ew", pady=2)
            row.columnconfigure(1, weight=1)
            button_wrap = ttk.Frame(row, style="Card.TFrame", padding=0)
            button_wrap.grid(column=0, row=0, sticky="w", padx=(0, 8))
            delete_button = ttk.Button(
                button_wrap,
                text="Delete",
                command=lambda i=idx: self._on_remove_cb([i]),
            )
            delete_button.grid(column=0, row=0, sticky="w")
            move_up_button = ttk.Button(
                button_wrap,
                text="↑",
                command=lambda i=idx: self._on_move_up_cb([i]),
                width=2,
            )
            move_up_button.grid(column=1, row=0, sticky="w", padx=(4, 0))
            move_down_button = ttk.Button(
                button_wrap,
                text="↓",
                command=lambda i=idx: self._on_move_down_cb([i]),
                width=2,
            )
            move_down_button.grid(column=2, row=0, sticky="w", padx=(2, 0))
            if not self._editable:
                delete_button.state(["disabled"])
                move_up_button.state(["disabled"])
                move_down_button.state(["disabled"])
            label = tk.Label(
                row,
                text=label_text,
                anchor="w",
                background=self._palette["panel_bg"],
                foreground=self._text_fg,
                justify="left",
            )
            label.grid(column=1, row=0, sticky="ew")

            row.bind("<Button-1>", lambda _event, i=idx: self._set_selected_index(i))
            label.bind("<Button-1>", lambda _event, i=idx: self._set_selected_index(i))

            self._row_widgets.append({"frame": row, "label": label})

        self._update_row_wrap()
        if self._selected_index is not None and self._selected_index < len(items):
            self._set_selected_index(self._selected_index)
        else:
            self._set_selected_index(None)


    def shutdown(self) -> None:
        self._host.shutdown()
