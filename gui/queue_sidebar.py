from __future__ import annotations

import tkinter as tk
from tkinter import ttk

SIDEBAR_ANIM_MS = 16


class QueueSidebar:
    _SIDEBAR_BORDER_WIDTH = 2

    def __init__(
        self,
        root: tk.Tk,
        *,
        header_bar: ttk.Frame,
        header_sep: ttk.Separator,
        header_wrap: ttk.Frame,
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

        self._sidebar_after_id: str | None = None
        self._sidebar_open = False
        self._sidebar_width_target = 0
        self._sidebar_width_current = 0.0
        self._sidebar_margin = 0
        self._sidebar_manual_width: int | None = None
        self._on_open_cb: callable | None = None
        self._shutdown = False

        self._selected_index: int | None = None
        self._row_widgets: list[dict] = []
        self._editable = True

        self._build_header_controls(header_wrap)
        self._build_sidebar()

    def _build_header_controls(self, header_wrap: ttk.Frame) -> None:
        self.button = ttk.Button(header_wrap, text="Queue", command=self.toggle)
        self.button.grid(column=0, row=0, sticky="e")

    def _build_sidebar(self) -> None:
        self.sidebar = tk.Canvas(
            self.root,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            background=self._palette["base_bg"],
        )
        self.sidebar.place_forget()

        self._sidebar_fill_item: int | None = None
        self._sidebar_outline_items: list[int] = []
        self._sidebar_window_item: int | None = None

        self._sidebar_content = ttk.Frame(self.sidebar, style="Card.TFrame", padding=6)
        self._sidebar_window_item = self.sidebar.create_window(
            0, 0, window=self._sidebar_content, anchor="nw"
        )
        self.sidebar.bind("<Configure>", self._on_sidebar_canvas_configure, add=True)

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
        scrollbar = ttk.Scrollbar(
            list_wrap, orient="vertical", command=self.list_canvas.yview
        )
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        self.list_canvas.grid(column=0, row=0, sticky="nsew")
        scrollbar.grid(column=1, row=0, sticky="ns")

        self.list_inner = ttk.Frame(self.list_canvas, style="Card.TFrame", padding=0)
        self._list_window = self.list_canvas.create_window(
            0, 0, window=self.list_inner, anchor="nw"
        )
        self.list_inner.bind("<Configure>", self._on_list_inner_configure, add=True)
        self.list_canvas.bind("<Configure>", self._on_list_canvas_configure, add=True)

    def _on_list_inner_configure(self, _event: tk.Event) -> None:
        try:
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        except Exception:
            pass

    def _on_list_canvas_configure(self, event: tk.Event) -> None:
        try:
            self.list_canvas.itemconfigure(self._list_window, width=event.width)
            self._update_row_wrap(event.width)
        except Exception:
            pass

    def _update_row_wrap(self, width: int | None = None) -> None:
        if width is None:
            try:
                width = int(self.list_canvas.winfo_width())
            except Exception:
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

    def _on_sidebar_canvas_configure(self, _event: tk.Event) -> None:
        if self._sidebar_window_item is None:
            return
        try:
            w = int(self.sidebar.winfo_width())
            h = int(self.sidebar.winfo_height())
        except Exception:
            return
        if w <= 1 or h <= 1:
            return

        bw = self._SIDEBAR_BORDER_WIDTH
        inner_w = max(1, w - (bw * 2))
        inner_h = max(1, h - (bw * 2))
        self.sidebar.coords(self._sidebar_window_item, bw, bw)
        self.sidebar.itemconfigure(
            self._sidebar_window_item, width=inner_w, height=inner_h
        )
        self._redraw_sidebar_border(w, h)

    def _redraw_sidebar_border(self, w: int, h: int) -> None:
        bw = self._SIDEBAR_BORDER_WIDTH
        x1 = 0
        y1 = 0
        x2 = max(1, w - 1)
        y2 = max(1, h - 1)

        outline = self._entry_border
        fill = self._palette["panel_bg"]

        if self._sidebar_fill_item is not None:
            try:
                self.sidebar.delete(self._sidebar_fill_item)
            except Exception:
                pass
            self._sidebar_fill_item = None
        for item in self._sidebar_outline_items:
            try:
                self.sidebar.delete(item)
            except Exception:
                pass
        self._sidebar_outline_items = []

        self._sidebar_fill_item = self.sidebar.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="",
            fill=fill,
            width=0,
        )
        self._sidebar_outline_items.append(
            self.sidebar.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=outline,
                fill="",
                width=bw,
            )
        )

        try:
            if self._sidebar_fill_item is not None:
                self.sidebar.tag_lower(self._sidebar_fill_item)
            if self._sidebar_window_item is not None:
                self.sidebar.tag_raise(self._sidebar_window_item)
            for item in self._sidebar_outline_items:
                self.sidebar.tag_raise(item)
        except Exception:
            pass

    def _raise_sidebar_widget(self) -> None:
        try:
            self.sidebar.tk.call("raise", self.sidebar._w)  # type: ignore[attr-defined]
        except Exception:
            pass

    def toggle(self) -> None:
        if self._sidebar_open:
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if self._on_open_cb is not None:
            self._on_open_cb()
        self._sidebar_open = True
        self._recompute_sidebar_target()
        if self._sidebar_width_target <= 1:
            self._sidebar_width_target = 320
        if not self.sidebar.winfo_ismapped():
            y, h = self._sidebar_y_and_height()
            self._sidebar_width_current = 0.0
            self.sidebar.place(
                relx=1.0,
                x=-self._sidebar_margin + self._sidebar_width_target,
                y=y,
                anchor="ne",
                width=self._sidebar_width_target,
                height=h,
            )
        self._raise_sidebar_widget()
        self.header_bar.lift()
        self._start_sidebar_animation()

    def close(self) -> None:
        self._sidebar_open = False
        self._start_sidebar_animation()

    def set_on_open(self, callback: callable | None) -> None:
        self._on_open_cb = callback

    def _recompute_sidebar_target(self) -> None:
        prev = self._sidebar_width_target
        width = self.root.winfo_width()
        if width <= 1:
            return
        max_width = max(200, width - (self._sidebar_margin * 2))
        if self._sidebar_manual_width is not None:
            target = self._sidebar_manual_width
        else:
            target = int(width * 0.9)
        self._sidebar_width_target = min(max_width, max(480, min(max_width, target)))
        if (
            prev > 0
            and self._sidebar_width_target > 0
            and prev != self._sidebar_width_target
        ):
            frac = max(0.0, min(1.0, self._sidebar_width_current / float(prev)))
            self._sidebar_width_current = frac * float(self._sidebar_width_target)

    def _sidebar_y_and_height(self) -> tuple[int, int]:
        root_h = self.root.winfo_height()
        if root_h <= 1:
            return (0, 1)
        header_h = self.header_bar.winfo_height() if self.header_bar else 0
        sep_h = self.header_sep.winfo_height() if self.header_sep else 0
        y = int(header_h + sep_h + self._sidebar_margin)
        y = max(0, min(root_h - 1, y))
        h = max(1, root_h - y - self._sidebar_margin)
        return (y, h)

    def _start_sidebar_animation(self) -> None:
        if self._sidebar_after_id is None:
            self._sidebar_tick()

    def _sidebar_tick(self) -> None:
        if self._shutdown:
            self._sidebar_after_id = None
            return
        full = float(self._sidebar_width_target)
        target = full if self._sidebar_open else 0.0
        ease = 0.28
        delta = target - self._sidebar_width_current
        if abs(delta) < 0.8:
            self._sidebar_width_current = target
        else:
            self._sidebar_width_current += delta * ease

        visible = int(round(self._sidebar_width_current))
        if visible <= 0:
            self.sidebar.place_forget()
            self._sidebar_after_id = None
            self._sidebar_width_current = 0.0
            return

        y, h = self._sidebar_y_and_height()
        shift = int(
            round(float(self._sidebar_width_target) - self._sidebar_width_current)
        )
        shift = max(0, min(self._sidebar_width_target, shift))
        self.sidebar.place_configure(
            relx=1.0,
            x=-self._sidebar_margin + shift,
            y=y,
            anchor="ne",
            width=self._sidebar_width_target,
            height=h,
        )

        if visible == int(round(target)):
            self._sidebar_after_id = None
            return

        self._sidebar_after_id = self.root.after(SIDEBAR_ANIM_MS, self._sidebar_tick)

    def on_root_configure(self, event: tk.Event) -> None:
        if getattr(event, "widget", self.root) is not self.root:
            return

        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        if self._sidebar_open:
            self._recompute_sidebar_target()
            if self._sidebar_after_id is None:
                y, h = self._sidebar_y_and_height()
                self._sidebar_width_current = float(self._sidebar_width_target)
                self.sidebar.place_configure(
                    relx=1.0,
                    x=-self._sidebar_margin,
                    y=y,
                    anchor="ne",
                    width=self._sidebar_width_target,
                    height=h,
                )
                self.header_bar.lift()

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
            label_text = f"{prefix}{idx + 1}. {url}"

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
        self._shutdown = True
        for attr in ("_sidebar_after_id",):
            after_id = getattr(self, attr, None)
            if not after_id:
                continue
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
            setattr(self, attr, None)
        try:
            self.sidebar.place_forget()
        except Exception:
            pass
