from __future__ import annotations

import queue
import re
import tkinter as tk
from tkinter import ttk

LAYOUT_ANIM_MS = 16
POLL_MS = 100
SIDEBAR_ANIM_MS = 16
LOG_BATCH_MAX = 200
LOG_MAX_LINES = 5000


class LogSidebar:
    _ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
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
    ) -> None:
        self.root = root
        self.header_bar = header_bar
        self.header_sep = header_sep
        self._palette = palette
        self._text_fg = text_fg
        self._entry_border = entry_border
        self._fonts = fonts

        self._queue: "queue.Queue[str]" = queue.Queue()
        self._poll_after_id: str | None = None
        self._shutdown = False

        self._log_sidebar_after_id: str | None = None
        self._log_sidebar_open = False
        self._log_sidebar_width_target = 0
        # Visible width during slide animation; the sidebar widget itself keeps a fixed width
        # to avoid internal layout reflow (which can cause button flicker/jank).
        self._log_sidebar_width_current = 0.0
        self._log_sidebar_margin = 0
        self._log_sidebar_manual_width: int | None = None
        self._logs_unread = False
        self._on_open_cb: callable | None = None

        self._layout_anim_after_id: str | None = None
        self._layout_target_lines: int | None = None
        self._layout_current_lines: float | None = None
        self._layout_last_applied_lines: int | None = None

        self._build_header_controls(header_wrap)
        self._build_sidebar()
        self._poll_queue()

    def _build_header_controls(self, header_wrap: ttk.Frame) -> None:
        self.button = ttk.Button(header_wrap, text="Logs", command=self.toggle)
        self.button.grid(column=0, row=0, sticky="e")

        self._dot = tk.Canvas(
            header_wrap,
            width=10,
            height=10,
            highlightthickness=0,
            borderwidth=0,
            bd=0,
            background=self._palette["base_bg"],
        )
        self._dot.grid(column=1, row=0, padx=(6, 0), sticky="e")
        self._dot_item = self._dot.create_oval(
            2, 2, 8, 8, fill="#dc2626", outline="#dc2626", state="hidden"
        )

    def _build_sidebar(self) -> None:
        # Use a Canvas so we can draw a rounded outline for the sidebar container.
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
            text="Logs",
            style="Subheader.TLabel",
            font=self._fonts["subheader"],
        ).grid(column=0, row=0, sticky="w")
        ttk.Button(header, text="Clear", command=self.clear).grid(
            column=1, row=0, sticky="e"
        )

        body = ttk.Frame(self._sidebar_content, style="Card.TFrame", padding=0)
        body.grid(column=0, row=1, sticky="nsew")
        self._sidebar_content.columnconfigure(0, weight=1)
        self._sidebar_content.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.text = tk.Text(
            body,
            height=12,
            wrap="word",
            state="disabled",
            background=self._palette["panel_bg"],
            foreground=self._text_fg,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(
            yscrollcommand=lambda f, l: self._autohide_text_scrollbar(scrollbar, f, l)
        )
        self.text.grid(column=0, row=0, sticky="nsew")
        scrollbar.grid(column=1, row=0, sticky="ns")
        scrollbar.grid_remove()

    def _on_sidebar_canvas_configure(self, _event: tk.Event) -> None:
        # Keep the inner content inset from the border, then redraw the rounded outline.
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
        # Use integer coordinates to avoid macOS/Tk anti-aliasing artifacts.
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
        # Canvas overrides lift/tkraise to operate on canvas items (requires a tag/id),
        # so raise the widget via the Tk "raise" command instead.
        try:
            self.sidebar.tk.call("raise", self.sidebar._w)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _autohide_text_scrollbar(
        self, scrollbar: ttk.Scrollbar, first: str, last: str
    ) -> None:
        scrollbar.set(first, last)
        try:
            f = float(first)
            l = float(last)
        except Exception:
            return
        should_show = not (f <= 0.0 and l >= 1.0)
        if should_show:
            if not scrollbar.winfo_ismapped():
                scrollbar.grid()
        else:
            if scrollbar.winfo_ismapped():
                scrollbar.grid_remove()

    def _set_unread(self, unread: bool) -> None:
        self._logs_unread = unread
        state = "normal" if unread else "hidden"
        try:
            self._dot.itemconfigure(self._dot_item, state=state)
        except Exception:
            pass

    def toggle(self) -> None:
        if self._log_sidebar_open:
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if self._on_open_cb is not None:
            self._on_open_cb()
        self._log_sidebar_open = True
        self._recompute_sidebar_target()
        if self._log_sidebar_width_target <= 1:
            self._log_sidebar_width_target = 320
        if not self.sidebar.winfo_ismapped():
            y, h = self._sidebar_y_and_height()
            # Place fully off-screen and slide in by adjusting x, keeping width fixed.
            self._log_sidebar_width_current = 0.0
            self.sidebar.place(
                relx=1.0,
                x=-self._log_sidebar_margin + self._log_sidebar_width_target,
                y=y,
                anchor="ne",
                width=self._log_sidebar_width_target,
                height=h,
            )
        self._raise_sidebar_widget()
        self.header_bar.lift()
        self._set_unread(False)
        self._start_sidebar_animation()

    def close(self) -> None:
        self._log_sidebar_open = False
        self._start_sidebar_animation()

    def set_on_open(self, callback: callable | None) -> None:
        self._on_open_cb = callback

    def _recompute_sidebar_target(self) -> None:
        prev = self._log_sidebar_width_target
        width = self.root.winfo_width()
        if width <= 1:
            return
        max_width = max(200, width - (self._log_sidebar_margin * 2))
        if self._log_sidebar_manual_width is not None:
            target = self._log_sidebar_manual_width
        else:
            target = int(width * 0.42)
        self._log_sidebar_width_target = min(420, max(260, min(max_width, target)))
        if (
            prev > 0
            and self._log_sidebar_width_target > 0
            and prev != self._log_sidebar_width_target
        ):
            # Preserve the current visible fraction during resizes.
            frac = max(0.0, min(1.0, self._log_sidebar_width_current / float(prev)))
            self._log_sidebar_width_current = frac * float(
                self._log_sidebar_width_target
            )

    def _sidebar_y_and_height(self) -> tuple[int, int]:
        root_h = self.root.winfo_height()
        if root_h <= 1:
            return (0, 1)
        header_h = self.header_bar.winfo_height() if self.header_bar else 0
        sep_h = self.header_sep.winfo_height() if self.header_sep else 0
        y = int(header_h + sep_h + self._log_sidebar_margin)
        y = max(0, min(root_h - 1, y))
        h = max(1, root_h - y - self._log_sidebar_margin)
        return (y, h)

    def _start_sidebar_animation(self) -> None:
        if self._log_sidebar_after_id is None:
            self._sidebar_tick()

    def _sidebar_tick(self) -> None:
        if self._shutdown:
            self._log_sidebar_after_id = None
            return
        full = float(self._log_sidebar_width_target)
        target = full if self._log_sidebar_open else 0.0
        ease = 0.28
        delta = target - self._log_sidebar_width_current
        if abs(delta) < 0.8:
            self._log_sidebar_width_current = target
        else:
            self._log_sidebar_width_current += delta * ease

        visible = int(round(self._log_sidebar_width_current))
        if visible <= 0:
            self.sidebar.place_forget()
            self._log_sidebar_after_id = None
            self._log_sidebar_width_current = 0.0
            return

        y, h = self._sidebar_y_and_height()
        # Slide the fixed-width sidebar by shifting it right as it closes.
        shift = int(
            round(
                float(self._log_sidebar_width_target) - self._log_sidebar_width_current
            )
        )
        shift = max(0, min(self._log_sidebar_width_target, shift))
        self.sidebar.place_configure(
            relx=1.0,
            x=-self._log_sidebar_margin + shift,
            y=y,
            anchor="ne",
            width=self._log_sidebar_width_target,
            height=h,
        )

        if visible == int(round(target)):
            self._log_sidebar_after_id = None
            return

        self._log_sidebar_after_id = self.root.after(
            SIDEBAR_ANIM_MS, self._sidebar_tick
        )

    def on_root_configure(self, event: tk.Event) -> None:
        if getattr(event, "widget", self.root) is not self.root:
            return

        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        try:
            from tkinter import font as tkfont

            line_px = tkfont.nametofont("TkFixedFont").metrics("linespace") or 16
        except Exception:
            line_px = 16

        compact = height < 720
        log_target_px = int(height * (0.25 if compact else 0.33))
        log_min = 4 if compact else 6
        log_max = 12 if compact else 18
        log_lines = max(log_min, min(log_max, max(1, log_target_px // line_px)))
        self._layout_target_lines = log_lines
        if self._layout_anim_after_id is None:
            self._layout_tick()

        if self._log_sidebar_open:
            self._recompute_sidebar_target()
            if self._log_sidebar_after_id is None:
                y, h = self._sidebar_y_and_height()
                self._log_sidebar_width_current = float(self._log_sidebar_width_target)
                self.sidebar.place_configure(
                    relx=1.0,
                    x=-self._log_sidebar_margin,
                    y=y,
                    anchor="ne",
                    width=self._log_sidebar_width_target,
                    height=h,
                )
                self.header_bar.lift()

    def _layout_tick(self) -> None:
        if self._shutdown:
            self._layout_anim_after_id = None
            return
        if self._layout_target_lines is None:
            self._layout_anim_after_id = None
            return

        if self._layout_current_lines is None:
            self._layout_current_lines = float(self._layout_target_lines)

        ease = 0.35
        delta = float(self._layout_target_lines) - self._layout_current_lines
        if abs(delta) > 0.01:
            self._layout_current_lines += delta * ease
            done = False
        else:
            done = True

        log_lines = int(round(self._layout_current_lines))
        if log_lines != self._layout_last_applied_lines:
            self._layout_last_applied_lines = log_lines
            try:
                self.text.configure(height=log_lines)
            except tk.TclError:
                pass

        if done:
            self._layout_current_lines = None
            self._layout_anim_after_id = None
            return

        self._layout_anim_after_id = self.root.after(LAYOUT_ANIM_MS, self._layout_tick)

    def _strip_ansi(self, text: str) -> str:
        return self._ANSI_RE.sub("", text)

    def queue(self, message: str) -> None:
        self._queue.put(message)

    def _poll_queue(self) -> None:
        if self._shutdown:
            self._poll_after_id = None
            return
        lines: list[str] = []
        try:
            for _ in range(LOG_BATCH_MAX):
                lines.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self._append_batch(lines)
        next_delay = 0 if not self._queue.empty() else POLL_MS
        self._poll_after_id = self.root.after(next_delay, self._poll_queue)

    def _append(self, message: str) -> None:
        self._append_batch([message])

    def _append_batch(self, messages: list[str]) -> None:
        if not messages:
            return
        cleaned = [self._strip_ansi(msg) for msg in messages]
        if not self._log_sidebar_open:
            self._set_unread(True)
        self.text.configure(state="normal")
        self.text.insert("end", "\n".join(cleaned) + "\n")
        if LOG_MAX_LINES > 0:
            try:
                line_count = int(float(self.text.index("end-1c").split(".")[0]))
            except Exception:
                line_count = 0
            excess = line_count - LOG_MAX_LINES
            if excess > 0:
                self.text.delete("1.0", f"{excess + 1}.0")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._set_unread(False)

    def shutdown(self) -> None:
        self._shutdown = True
        for attr in (
            "_poll_after_id",
            "_layout_anim_after_id",
            "_log_sidebar_after_id",
        ):
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
