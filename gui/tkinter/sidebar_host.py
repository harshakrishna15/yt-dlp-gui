from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class SidebarSizeSpec:
    width_ratio: float
    min_width: int
    max_width: int | None = None
    margin: int = 0


class SidebarHost:
    def __init__(
        self,
        root: tk.Tk,
        *,
        header_bar: ttk.Frame,
        header_sep: ttk.Separator,
        palette: dict[str, str],
        entry_border: str,
        size_spec: SidebarSizeSpec,
        border_width: int = 2,
        anim_ms: int = 16,
        anim_ease: float = 0.28,
    ) -> None:
        self.root = root
        self.header_bar = header_bar
        self.header_sep = header_sep
        self._palette = palette
        self._entry_border = entry_border
        self._size_spec = size_spec
        self._border_width = max(0, int(border_width))
        self._anim_ms = max(1, int(anim_ms))
        self._anim_ease = max(0.05, min(0.95, float(anim_ease)))

        self._after_id: str | None = None
        self._open = False
        self._width_target = 0
        self._width_current = 0.0
        self._manual_width: int | None = None
        self._shutdown = False
        self._on_open_cb: callable | None = None

        self.canvas = tk.Canvas(
            self.root,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            background=self._palette["base_bg"],
        )
        self.canvas.place_forget()

        self._fill_item: int | None = None
        self._outline_items: list[int] = []
        self._window_item: int | None = None
        self.content = ttk.Frame(self.canvas, style="Card.TFrame", padding=6)
        self._window_item = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add=True)

    @staticmethod
    def compute_target_width(
        *,
        root_width: int,
        content_width: int,
        width_ratio: float,
        min_width: int,
        max_width: int | None,
        margin: int,
        manual_width: int | None,
    ) -> int:
        if root_width <= 1:
            return max(1, min_width)
        max_possible = max(200, root_width - (margin * 2))
        if manual_width is not None:
            target = int(manual_width)
        else:
            ratio_target = int(root_width * width_ratio)
            target = max(min_width, ratio_target, content_width)
        if max_width is not None:
            target = min(max_width, target)
        return min(max_possible, max(1, target))

    def set_on_open(self, callback: callable | None) -> None:
        self._on_open_cb = callback

    def set_manual_width(self, width: int | None) -> None:
        self._manual_width = int(width) if width is not None else None

    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        if self._on_open_cb is not None:
            self._on_open_cb()
        self._open = True
        self._recompute_target()
        if self._width_target <= 1:
            self._width_target = max(1, self._size_spec.min_width)
        if not self.canvas.winfo_ismapped():
            y, h = self._y_and_height()
            self._width_current = 0.0
            self.canvas.place(
                relx=1.0,
                x=-self._size_spec.margin + self._width_target,
                y=y,
                anchor="ne",
                width=self._width_target,
                height=h,
            )
        self._raise_widget()
        self.header_bar.lift()
        self._start_animation()

    def close(self) -> None:
        self._open = False
        self._start_animation()

    def toggle(self) -> None:
        if self._open:
            self.close()
        else:
            self.open()

    def on_root_configure(self, event: tk.Event) -> None:
        if getattr(event, "widget", self.root) is not self.root:
            return

        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        if self._open:
            self._recompute_target()
            if self._after_id is None:
                y, h = self._y_and_height()
                self._width_current = float(self._width_target)
                self.canvas.place_configure(
                    relx=1.0,
                    x=-self._size_spec.margin,
                    y=y,
                    anchor="ne",
                    width=self._width_target,
                    height=h,
                )
                self.header_bar.lift()

    def shutdown(self) -> None:
        self._shutdown = True
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self.canvas.place_forget()
        except Exception:
            pass

    def _content_req_width(self) -> int:
        try:
            self.content.update_idletasks()
            # Add a small cushion to avoid clipping when widgets have internal padding.
            return max(1, int(self.content.winfo_reqwidth()) + 12)
        except Exception:
            return 1

    def _recompute_target(self) -> None:
        prev = self._width_target
        self._width_target = self.compute_target_width(
            root_width=int(self.root.winfo_width()),
            content_width=self._content_req_width(),
            width_ratio=self._size_spec.width_ratio,
            min_width=self._size_spec.min_width,
            max_width=self._size_spec.max_width,
            margin=self._size_spec.margin,
            manual_width=self._manual_width,
        )
        if prev > 0 and self._width_target > 0 and prev != self._width_target:
            frac = max(0.0, min(1.0, self._width_current / float(prev)))
            self._width_current = frac * float(self._width_target)

    def _y_and_height(self) -> tuple[int, int]:
        root_h = self.root.winfo_height()
        if root_h <= 1:
            return (0, 1)
        header_h = self.header_bar.winfo_height() if self.header_bar else 0
        sep_h = self.header_sep.winfo_height() if self.header_sep else 0
        y = int(header_h + sep_h + self._size_spec.margin)
        y = max(0, min(root_h - 1, y))
        h = max(1, root_h - y - self._size_spec.margin)
        return (y, h)

    def _start_animation(self) -> None:
        if self._after_id is None:
            self._tick()

    def _tick(self) -> None:
        if self._shutdown:
            self._after_id = None
            return
        full = float(self._width_target)
        target = full if self._open else 0.0
        delta = target - self._width_current
        if abs(delta) < 0.8:
            self._width_current = target
        else:
            self._width_current += delta * self._anim_ease

        visible = int(round(self._width_current))
        if visible <= 0:
            self.canvas.place_forget()
            self._after_id = None
            self._width_current = 0.0
            return

        y, h = self._y_and_height()
        shift = int(round(float(self._width_target) - self._width_current))
        shift = max(0, min(self._width_target, shift))
        self.canvas.place_configure(
            relx=1.0,
            x=-self._size_spec.margin + shift,
            y=y,
            anchor="ne",
            width=self._width_target,
            height=h,
        )

        if visible == int(round(target)):
            self._after_id = None
            return

        self._after_id = self.root.after(self._anim_ms, self._tick)

    def _on_canvas_configure(self, _event: tk.Event) -> None:
        if self._window_item is None:
            return
        try:
            w = int(self.canvas.winfo_width())
            h = int(self.canvas.winfo_height())
        except Exception:
            return
        if w <= 1 or h <= 1:
            return

        bw = self._border_width
        inner_w = max(1, w - (bw * 2))
        inner_h = max(1, h - (bw * 2))
        self.canvas.coords(self._window_item, bw, bw)
        self.canvas.itemconfigure(self._window_item, width=inner_w, height=inner_h)
        self._redraw_border(w, h)

    def _redraw_border(self, w: int, h: int) -> None:
        bw = self._border_width
        x1 = 0
        y1 = 0
        x2 = max(1, w - 1)
        y2 = max(1, h - 1)

        outline = self._entry_border
        fill = self._palette["panel_bg"]

        if self._fill_item is not None:
            try:
                self.canvas.delete(self._fill_item)
            except Exception:
                pass
            self._fill_item = None
        for item in self._outline_items:
            try:
                self.canvas.delete(item)
            except Exception:
                pass
        self._outline_items = []

        self._fill_item = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="",
            fill=fill,
            width=0,
        )
        self._outline_items.append(
            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=outline if bw > 0 else "",
                fill="",
                width=bw,
            )
        )

        try:
            if self._fill_item is not None:
                self.canvas.tag_lower(self._fill_item)
            if self._window_item is not None:
                self.canvas.tag_raise(self._window_item)
            for item in self._outline_items:
                self.canvas.tag_raise(item)
        except Exception:
            pass

    def _raise_widget(self) -> None:
        try:
            self.canvas.tk.call("raise", self.canvas._w)  # type: ignore[attr-defined]
        except Exception:
            pass
