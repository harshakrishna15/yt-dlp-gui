from __future__ import annotations

import threading
from tkinter import messagebox

from ..common import download
from ..common.types import QueueSettings
from ..core import queue_logic as core_queue_logic
from ..core import urls as core_urls
from ..core import workflow as core_workflow
from ..services import app_service


class QueueFlowMixin:
    def _queue_refresh(self) -> None:
        active_index = self.queue_index if self.queue_active else None
        self.queue_panel.refresh(
            self.queue_items,
            active_index=active_index,
            editable=not self.queue_active,
        )

    def _queue_remove_selected(self, indices: list[int]) -> None:
        if self.queue_active:
            return
        if not indices:
            return
        removed = sorted(set(indices), reverse=True)
        for idx in removed:
            if 0 <= idx < len(self.queue_items):
                self.queue_items.pop(idx)
        if self.queue_active and self.queue_index is not None:
            for idx in removed:
                if idx < self.queue_index:
                    self.queue_index -= 1
            if self.queue_index >= len(self.queue_items):
                self.queue_index = max(0, len(self.queue_items) - 1)
        self._queue_refresh()
        self._update_controls_state()

    def _queue_move_up(self, indices: list[int]) -> None:
        if self.queue_active:
            return
        if not indices:
            return
        moved = False
        for idx in sorted(set(indices)):
            if idx <= 0 or idx >= len(self.queue_items):
                continue
            self.queue_items[idx - 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx - 1],
            )
            moved = True
        if moved:
            self._queue_refresh()

    def _queue_move_down(self, indices: list[int]) -> None:
        if self.queue_active:
            return
        if not indices:
            return
        moved = False
        for idx in sorted(set(indices), reverse=True):
            if idx < 0 or idx >= len(self.queue_items) - 1:
                continue
            self.queue_items[idx + 1], self.queue_items[idx] = (
                self.queue_items[idx],
                self.queue_items[idx + 1],
            )
            moved = True
        if moved:
            self._queue_refresh()

    def _queue_clear(self) -> None:
        if self.queue_active:
            return
        if not self.queue_items:
            return
        self.queue_items.clear()
        self.queue_index = None
        self._queue_refresh()
        self._update_controls_state()

    def _on_add_to_queue(self) -> None:
        if self.is_downloading:
            return
        url = core_urls.strip_url_whitespace(self.url_var.get())
        settings = self._capture_queue_settings()
        issue = core_queue_logic.queue_add_issue(
            url=url,
            playlist_mode=bool(self.is_playlist or core_urls.is_playlist_url(url)),
            formats_loaded=bool(self.formats.filtered_lookup),
            settings=settings,
        )
        if issue:
            status_text, log_text = core_queue_logic.queue_add_feedback(issue)
            self.status_var.set(status_text)
            self._log(log_text)
            return

        self.queue_items.append(core_queue_logic.queue_item(url, settings))
        self._queue_refresh()
        self._update_controls_state()

    def _on_start_queue(self) -> None:
        self._start_queue_download()

    def _capture_queue_settings(self) -> QueueSettings:
        fmt_label = self.format_var.get()
        fmt_info = self.formats.filtered_lookup.get(fmt_label) or {}
        options = self._snapshot_download_options()
        return app_service.build_queue_settings(
            mode=self.mode_var.get(),
            format_filter=self.format_filter_var.get(),
            codec_filter=self.codec_filter_var.get(),
            convert_to_mp4=bool(self.convert_to_mp4_var.get()),
            format_label=fmt_label,
            format_info=fmt_info,
            output_dir=self.output_dir_var.get(),
            playlist_items=self.playlist_items_var.get(),
            options=options,
        )

    def _start_queue_download(self) -> None:
        queue_check = core_workflow.validate_queue_start(
            is_downloading=self.is_downloading,
            queue_items=self.queue_items,
        )
        if not queue_check.can_start:
            if queue_check.invalid_index is None or queue_check.invalid_issue is None:
                return
            messagebox.showerror(
                "Missing settings",
                (
                    "Queue item "
                    f"{queue_check.invalid_index} is missing "
                    f"{core_queue_logic.queue_start_missing_detail(queue_check.invalid_issue)}."
                ),
            )
            return

        self.queue_active = True
        self.queue_index = 0
        self.queue_settings = None
        self._queue_failed_items = 0
        self.is_downloading = True
        self._show_progress_item = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self.simple_state_var.set("Downloading queue")
        self.status_var.set("Downloading queue...")
        self.logs.clear()
        self._reset_progress_summary()
        self._update_controls_state()
        self._queue_refresh()
        self._start_next_queue_item()

    def _resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        return app_service.resolve_format_for_url(
            url=url,
            settings=settings,
            log=self._log,
        )

    def _start_next_queue_item(self) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        next_item = core_workflow.next_queue_run_item(self.queue_items, self.queue_index)
        if next_item is None:
            self._finish_queue()
            return
        self.queue_index = next_item.index
        self._log(f"[queue] item {next_item.display_index}/{next_item.total} {next_item.url}")
        self._queue_refresh()
        self.download_thread = threading.Thread(
            target=self._run_queue_download,
            kwargs={
                "url": next_item.url,
                "settings": next_item.settings,
                "index": next_item.display_index,
                "total": next_item.total,
                "default_output_dir": self.output_dir_var.get(),
            },
            daemon=True,
        )
        self.download_thread.start()

    def _run_queue_download(
        self,
        url: str,
        settings: QueueSettings,
        index: int,
        total: int,
        default_output_dir: str,
    ) -> None:
        had_error = False
        cancelled = False
        try:
            resolved = self._resolve_format_for_url(url, settings)
            title = resolved.get("title") or url
            item_text = f"{index}/{total} {title}"
            self._post_ui(self.progress_item_var.set, item_text)
            request = app_service.build_queue_download_request(
                url=url,
                settings=settings,
                resolved=resolved,
                default_output_dir=default_output_dir,
            )
            if request["playlist_enabled"]:
                self._log(
                    f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}"
                )
            result = app_service.run_download_request(
                request=request,
                cancel_event=self._cancel_event,
                log=self._log,
                update_progress=lambda u: self._post_ui(self._on_progress_update, u),
                record_output=lambda p: self._post_ui(self._record_download_output, p, url),
                ensure_output_dir=True,
            )
            had_error = result == download.DOWNLOAD_ERROR
            cancelled = result == download.DOWNLOAD_CANCELLED
        except Exception as exc:
            had_error = True
            self._log(f"[queue] failed: {exc}")
        finally:
            self._post_ui(self._on_queue_item_finish, had_error, cancelled)

    def _on_queue_item_finish(
        self,
        had_error: bool = False,
        cancelled: bool = False,
    ) -> None:
        if not self.queue_active or self.queue_index is None:
            return
        progress = core_workflow.advance_queue_progress(
            queue_length=len(self.queue_items),
            current_index=self.queue_index,
            failed_items=self._queue_failed_items,
            cancel_requested=self._cancel_requested,
            had_error=had_error,
            cancelled=cancelled,
        )
        self._queue_failed_items = progress.failed_items
        self._cancel_requested = progress.cancel_requested
        if progress.should_finish:
            if progress.finish_cancelled:
                self._log("[queue] cancelled")
            self._finish_queue(cancelled=progress.finish_cancelled)
            return
        self.queue_index = progress.next_index
        self._reset_progress_summary()
        self._start_next_queue_item()

    def _finish_queue(self, *, cancelled: bool = False) -> None:
        failed_items = self._queue_failed_items
        self.queue_active = False
        self.queue_index = None
        self.queue_settings = None
        self._queue_failed_items = 0
        self.is_downloading = False
        self._show_progress_item = False
        self._cancel_requested = False
        self._cancel_event = None
        outcome = core_workflow.queue_finish_outcome(
            cancelled=cancelled,
            failed_items=failed_items,
        )
        if outcome == "cancelled":
            self._log("[queue] stopped by cancellation")
        elif outcome == "failed":
            self._log(f"[queue] finished with {failed_items} failed item(s)")
        else:
            self._log("[queue] finished successfully")
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self._reset_progress_summary()
        self._update_controls_state()
        self._queue_refresh()
