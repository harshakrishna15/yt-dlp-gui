from __future__ import annotations

import queue
import re
import tkinter as tk
from tkinter import ttk

from .sidebar_host import SidebarHost, SidebarSizeSpec

LAYOUT_ANIM_MS = 16
POLL_MS = 100
SIDEBAR_ANIM_MS = 16
LOG_BATCH_MAX = 200
LOG_MAX_LINES = 5000


class LogSidebar:
    _ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

    def __init__(
        self,
        root: tk.Tk,
        *,
        header_bar: ttk.Frame,
        header_sep: ttk.Separator,
        header_button: ttk.Button,
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

        self._logs_unread = False

        self._layout_anim_after_id: str | None = None
        self._layout_target_lines: int | None = None
        self._layout_current_lines: float | None = None
        self._layout_last_applied_lines: int | None = None

        self._build_header_controls(header_button, header_wrap)
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
        self._poll_queue()

    def _build_header_controls(
        self,
        header_button: ttk.Button,
        header_wrap: ttk.Frame,
    ) -> None:
        self.button = header_button
        self.button.configure(command=self.toggle)

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

    def _autohide_text_scrollbar(
        self, scrollbar: ttk.Scrollbar, first: str, last: str
    ) -> None:
        scrollbar.set(first, last)
        try:
            f = float(first)
            l = float(last)
        except (TypeError, ValueError):
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
        except (tk.TclError, RuntimeError):
            pass

    def toggle(self) -> None:
        self._host.toggle()

    def open(self) -> None:
        self._host.open()
        self._set_unread(False)

    def close(self) -> None:
        self._host.close()

    def is_open(self) -> bool:
        host = getattr(self, "_host", None)
        if host is None:
            return bool(getattr(self, "_log_sidebar_open", False))
        return host.is_open()

    def set_on_open(self, callback: callable | None) -> None:
        self._host.set_on_open(callback)

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
        except (tk.TclError, RuntimeError):
            line_px = 16

        compact = height < 720
        log_target_px = int(height * (0.25 if compact else 0.33))
        log_min = 4 if compact else 6
        log_max = 12 if compact else 18
        log_lines = max(log_min, min(log_max, max(1, log_target_px // line_px)))
        self._layout_target_lines = log_lines
        if self._layout_anim_after_id is None:
            self._layout_tick()

        self._host.on_root_configure(event)

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
        if not self.is_open():
            self._set_unread(True)
        self.text.configure(state="normal")
        self.text.insert("end", "\n".join(cleaned) + "\n")
        if LOG_MAX_LINES > 0:
            try:
                line_count = int(float(self.text.index("end-1c").split(".")[0]))
            except (tk.TclError, RuntimeError, TypeError, ValueError):
                line_count = 0
            excess = line_count - LOG_MAX_LINES
            if excess > 0:
                self.text.delete("1.0", f"{excess + 1}.0")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._set_unread(False)

    def get_text(self) -> str:
        try:
            return self.text.get("1.0", "end-1c")
        except (tk.TclError, RuntimeError):
            return ""

    def shutdown(self) -> None:
        self._shutdown = True
        for attr in (
            "_poll_after_id",
            "_layout_anim_after_id",
        ):
            after_id = getattr(self, attr, None)
            if not after_id:
                continue
            try:
                self.root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
            setattr(self, attr, None)
        self._host.shutdown()
