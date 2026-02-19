import tkinter as tk
from tkinter import ttk

TOOLTIP_DELAY_MS = 450
TOOLTIP_VISIBLE_MS = 1800
SCROLLBAR_PAD_PX = 4
SCROLL_OVERFLOW_PX = 2


class Tooltip:
    def __init__(
        self,
        root: tk.Tk,
        widget: tk.Widget,
        text: str,
        *,
        delay_ms: int = TOOLTIP_DELAY_MS,
        visible_ms: int = TOOLTIP_VISIBLE_MS,
    ) -> None:
        self.root = root
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.visible_ms = visible_ms
        self._after_id: str | None = None
        self._hide_after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        self._last_xy: tuple[int, int] | None = None
        self._hovering = False

        widget.bind("<Enter>", self._on_enter, add=True)
        widget.bind("<Leave>", self._on_leave, add=True)
        widget.bind("<Motion>", self._on_motion, add=True)

    def _on_enter(self, event: tk.Event) -> None:
        self._hovering = True
        self._last_xy = (
            int(getattr(event, "x_root", 0)),
            int(getattr(event, "y_root", 0)),
        )
        if self._tip is None:
            self._schedule()

    def _on_motion(self, event: tk.Event) -> None:
        self._last_xy = (
            int(getattr(event, "x_root", 0)),
            int(getattr(event, "y_root", 0)),
        )
        if self._tip is not None:
            self._position()
            return
        self._schedule()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovering = False
        self._cancel_show()
        self._cancel_hide()
        self._hide()

    def _schedule(self) -> None:
        self._cancel_show()
        if not self._hovering:
            return
        self._after_id = self.root.after(self.delay_ms, self._show)

    def _cancel_show(self) -> None:
        if self._after_id is None:
            return
        try:
            self.root.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    def _schedule_hide(self) -> None:
        self._cancel_hide()
        self._hide_after_id = self.root.after(self.visible_ms, self._auto_hide)

    def _cancel_hide(self) -> None:
        if self._hide_after_id is None:
            return
        try:
            self.root.after_cancel(self._hide_after_id)
        except Exception:
            pass
        self._hide_after_id = None

    def _auto_hide(self) -> None:
        self._hide_after_id = None
        self._hide()

    def _position(self) -> None:
        if self._tip is None:
            return
        x, y = self._last_xy or (0, 0)
        x += 14
        y += 14
        self._tip.geometry(f"+{x}+{y}")

    def _show(self) -> None:
        self._after_id = None
        if not self._hovering:
            return
        if self._tip is not None:
            return
        self._tip = tk.Toplevel(self.root)
        self._tip.wm_overrideredirect(True)
        try:
            self._tip.attributes("-topmost", True)
        except Exception:
            pass

        label = tk.Label(
            self._tip,
            text=self.text,
            justify="left",
            background="#fff8dc",
            foreground="#111827",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
        )
        label.pack()
        self._position()
        self._schedule_hide()

    def _hide(self) -> None:
        self._cancel_hide()
        if self._tip is None:
            return
        try:
            self._tip.destroy()
        except Exception:
            pass
        self._tip = None


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, *, padding: int = 0, bg: str | None = None) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        if bg is not None:
            self.canvas.configure(background=bg)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self._scrollbar_pad = SCROLLBAR_PAD_PX
        self._last_canvas_width: int | None = None
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas, padding=padding)
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.grid(column=0, row=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel(self.canvas)
        self._update_scrollbar_visibility()

    def _on_content_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._last_canvas_width = int(getattr(event, "width", 0) or 0)
        self._update_content_width()
        self._update_scrollbar_visibility()

    def _update_content_width(self) -> None:
        if not self._last_canvas_width or self._last_canvas_width <= 1:
            return
        width = self._last_canvas_width
        if self.scrollbar.winfo_ismapped():
            try:
                sb_w = self.scrollbar.winfo_reqwidth()
            except tk.TclError:
                sb_w = 16
            reserve = int(sb_w) + (int(self._scrollbar_pad) * 2)
            width = max(1, width - reserve)
        self.canvas.itemconfigure(self._window_id, width=width)

    def _update_scrollbar_visibility(self) -> None:
        try:
            canvas_h = self.canvas.winfo_height()
        except tk.TclError:
            return
        if canvas_h <= 1:
            return
        bbox = self.canvas.bbox(self._window_id) or self.canvas.bbox("all")
        if not bbox:
            return
        content_h = int(bbox[3] - bbox[1])
        should_show = content_h > (canvas_h + SCROLL_OVERFLOW_PX)
        if should_show:
            if not self.scrollbar.winfo_ismapped():
                pad = int(self._scrollbar_pad)
                sb_height = max(1, canvas_h - (pad * 2))
                self.scrollbar.place(
                    relx=1.0,
                    x=-pad,
                    y=pad,
                    anchor="ne",
                    height=sb_height,
                )
                self._update_content_width()
        else:
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.place_forget()
                self._update_content_width()

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        def can_scroll() -> bool:
            try:
                canvas_h = self.canvas.winfo_height()
            except tk.TclError:
                return False
            if canvas_h <= 1:
                return False
            bbox = self.canvas.bbox(self._window_id) or self.canvas.bbox("all")
            if not bbox:
                return False
            content_h = int(bbox[3] - bbox[1])
            return content_h > (canvas_h + SCROLL_OVERFLOW_PX)

        def on_mousewheel(event: tk.Event) -> str:
            if not can_scroll():
                return ""
            if getattr(event, "delta", 0):
                widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"
            return ""

        def on_button4(_event: tk.Event) -> str:
            if not can_scroll():
                return ""
            widget.yview_scroll(-1, "units")
            return "break"

        def on_button5(_event: tk.Event) -> str:
            if not can_scroll():
                return ""
            widget.yview_scroll(1, "units")
            return "break"

        widget.bind_all("<MouseWheel>", on_mousewheel)
        widget.bind_all("<Button-4>", on_button4)
        widget.bind_all("<Button-5>", on_button5)
