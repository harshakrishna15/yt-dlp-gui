from __future__ import annotations

import queue
import re
import tkinter as tk
from tkinter import ttk

LAYOUT_ANIM_MS = 16
POLL_MS = 100
SIDEBAR_ANIM_MS = 16


class LogSidebar:
    _ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

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

        self._log_sidebar_after_id: str | None = None
        self._log_sidebar_open = False
        self._log_sidebar_width_target = 0
        self._log_sidebar_width_current = 0.0
        self._log_sidebar_margin = 0
        self._logs_unread = False

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
        self.sidebar = ttk.Frame(self.root, style="OutputPath.TFrame", padding=6)
        self.sidebar.place_forget()

        header = ttk.Frame(self.sidebar, style="Card.TFrame", padding=0)
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

        body = ttk.Frame(self.sidebar, style="Card.TFrame", padding=0)
        body.grid(column=0, row=1, sticky="nsew")
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.text = tk.Text(
            body,
            height=12,
            wrap="word",
            state="disabled",
            background=self._palette["panel_bg"],
            foreground=self._text_fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self._entry_border,
            highlightcolor=self._entry_border,
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(
            yscrollcommand=lambda f, l: self._autohide_text_scrollbar(scrollbar, f, l)
        )
        self.text.grid(column=0, row=0, sticky="nsew")
        scrollbar.grid(column=1, row=0, sticky="ns")
        scrollbar.grid_remove()

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
        self._log_sidebar_open = True
        self._recompute_sidebar_target()
        if not self.sidebar.winfo_ismapped():
            y, h = self._sidebar_y_and_height()
            self.sidebar.place(
                relx=1.0,
                x=-self._log_sidebar_margin,
                y=y,
                anchor="ne",
                width=1,
                height=h,
            )
        self.header_bar.lift()
        self._set_unread(False)
        self._start_sidebar_animation()

    def close(self) -> None:
        self._log_sidebar_open = False
        self._log_sidebar_width_target = 0
        self._start_sidebar_animation()

    def _recompute_sidebar_target(self) -> None:
        width = self.root.winfo_width()
        if width <= 1:
            return
        max_width = max(200, width - (self._log_sidebar_margin * 2))
        self._log_sidebar_width_target = min(
            420, max(260, min(max_width, int(width * 0.42)))
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
        target = float(self._log_sidebar_width_target)
        ease = 0.28
        delta = target - self._log_sidebar_width_current
        if abs(delta) < 0.8:
            self._log_sidebar_width_current = target
        else:
            self._log_sidebar_width_current += delta * ease

        w = int(round(self._log_sidebar_width_current))
        if w <= 0:
            self.sidebar.place_forget()
            self._log_sidebar_after_id = None
            self._log_sidebar_width_current = 0.0
            return

        y, h = self._sidebar_y_and_height()
        self.sidebar.place_configure(
            relx=1.0,
            x=-self._log_sidebar_margin,
            y=y,
            anchor="ne",
            width=w,
            height=h,
        )
        self.sidebar.lift()
        self.header_bar.lift()

        if w == int(round(target)):
            self._log_sidebar_after_id = None
            return

        self._log_sidebar_after_id = self.root.after(SIDEBAR_ANIM_MS, self._sidebar_tick)

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
        try:
            while True:
                line = self._queue.get_nowait()
                self._append(line)
        except queue.Empty:
            pass
        self._poll_after_id = self.root.after(POLL_MS, self._poll_queue)

    def _append(self, message: str) -> None:
        message = self._strip_ansi(message)
        if not self._log_sidebar_open:
            self._set_unread(True)
        self.text.configure(state="normal")
        self.text.insert("end", message + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._set_unread(False)

    def shutdown(self) -> None:
        for attr in ("_poll_after_id", "_layout_anim_after_id", "_log_sidebar_after_id"):
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

