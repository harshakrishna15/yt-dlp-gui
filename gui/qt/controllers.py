from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from ..common import download, format_pipeline, formats as formats_mod, yt_dlp_helpers as helpers
from ..common.types import DownloadRequest, QueueItem, QueueSettings
from ..core import error_feedback as core_error_feedback
from ..core import queue_logic as core_queue_logic
from ..core import urls as core_urls
from ..core import workflow as core_workflow
from ..services import app_service
from .ports import SideEffectPorts

if TYPE_CHECKING:
    from .app import QtYtDlpGui


def _emit_window_signal(window: object, signal_name: str, *args: object) -> bool:
    signals = getattr(window, "_signals", None)
    if signals is None:
        return False
    signal = getattr(signals, signal_name, None)
    if signal is None:
        return False
    try:
        signal.emit(*args)
    except RuntimeError:
        return False
    return True


@dataclass
class SourceState:
    fetch_request_seq: int = 0
    active_fetch_request_id: int = 0
    is_fetching: bool = False
    pending_mixed_url: str = ""
    last_formats_error_popup_key: str = ""
    playlist_mode: bool = False
    video_labels: list[str] = field(default_factory=list)
    video_lookup: dict[str, dict] = field(default_factory=dict)
    audio_labels: list[str] = field(default_factory=list)
    audio_lookup: dict[str, dict] = field(default_factory=dict)
    filtered_labels: list[str] = field(default_factory=list)
    filtered_lookup: dict[str, dict] = field(default_factory=dict)


class RunState(Enum):
    IDLE = "idle"
    SINGLE = "single"
    QUEUE = "queue"
    CANCELLING = "cancelling"


@dataclass
class RunQueueState:
    run_state: RunState = RunState.IDLE
    is_downloading: bool = False
    cancel_requested: bool = False
    cancel_event: threading.Event | None = None
    show_progress_item: bool = False
    close_after_cancel: bool = False
    queue_items: list[QueueItem] = field(default_factory=list)
    queue_active: bool = False
    queue_index: int | None = None
    queue_failed_items: int = 0
    queue_started_ts: float | None = None


class SourceController:
    def __init__(
        self,
        window: "QtYtDlpGui",
        *,
        state: SourceState,
        ports: SideEffectPorts,
    ) -> None:
        self.window = window
        self.state = state
        self._ports = ports

    def on_url_changed(self) -> None:
        w = self.window
        s = self.state

        current = w.url_edit.text()
        normalized = core_urls.strip_url_whitespace(current)
        if normalized != s.pending_mixed_url:
            s.last_formats_error_popup_key = ""
        if normalized != current:
            w.url_edit.blockSignals(True)
            w.url_edit.setText(normalized)
            w.url_edit.blockSignals(False)
        has_mixed_url = bool(normalized and core_urls.is_mixed_url(normalized))
        if has_mixed_url:
            s.pending_mixed_url = normalized
            if (
                w.status_value.text()
                != "Choose video or playlist URL before fetching formats."
            ):
                w._set_status("Choose video or playlist URL before fetching formats.")
            w._set_source_feedback(
                "Choose Single video or Playlist before loading formats.",
                tone="warning",
            )
        else:
            s.pending_mixed_url = ""

        w._fetch_timer.stop()
        s.fetch_request_seq += 1
        s.active_fetch_request_id = s.fetch_request_seq
        s.is_fetching = False
        s.playlist_mode = core_urls.is_playlist_url(normalized)

        w._set_mode_unselected()
        w._set_combo_items(
            w.container_combo, [("Select container", "")], keep_current=False
        )
        w.codec_combo.blockSignals(True)
        w.codec_combo.setCurrentIndex(0)
        w.codec_combo.blockSignals(False)
        w.convert_check.setChecked(False)
        w.playlist_items_edit.clear()
        s.video_labels = []
        s.video_lookup = {}
        s.audio_labels = []
        s.audio_lookup = {}
        s.filtered_labels = []
        s.filtered_lookup = {}
        w._set_preview_title("")
        w._set_source_summary(None)
        w.format_combo.clear()
        w._update_source_details_visibility()

        if not normalized:
            w._set_source_feedback(
                "Paste a video or playlist URL to load available formats.",
                tone="neutral",
            )
        elif (not has_mixed_url) and (not w._is_downloading):
            w._set_source_feedback(
                "URL ready. Click Analyze URL to load formats and preview details.",
                tone="neutral",
            )

        w._update_controls_state()

    def start_fetch_formats(self) -> None:
        w = self.window
        s = self.state
        if w._is_downloading:
            return
        url = w.url_edit.text().strip()
        if not url or s.pending_mixed_url:
            return
        s.fetch_request_seq += 1
        request_id = s.fetch_request_seq
        s.active_fetch_request_id = request_id
        s.is_fetching = True
        w._set_status("Fetching formats...")
        w._set_source_feedback("Loading available formats...", tone="loading")
        w._update_controls_state()
        self._ports.worker_executor.submit(self.fetch_formats_worker, request_id, url)

    def fetch_formats_worker(self, request_id: int, url: str) -> None:
        try:
            info = helpers.fetch_info(url)
            formats = formats_mod.formats_from_info(info)
            collections = format_pipeline.build_format_collections(formats)
            payload = {
                "collections": collections,
                "preview_title": format_pipeline.preview_title_from_info(info),
                "source_summary": format_pipeline.source_summary_from_info(
                    info,
                    video_format_count=len(collections.get("video_labels") or []),
                    audio_format_count=len(collections.get("audio_labels") or []),
                ),
            }
            is_playlist = bool(
                info.get("_type") == "playlist" or info.get("entries") is not None
            )
            _emit_window_signal(
                self.window,
                "formats_loaded",
                request_id, url, payload, False, is_playlist
            )
        except Exception as exc:
            _emit_window_signal(
                self.window,
                "log",
                f"[error] Could not fetch formats: {exc}",
            )
            _emit_window_signal(
                self.window,
                "formats_loaded",
                request_id,
                url,
                {},
                True,
                False,
            )

    def on_formats_loaded(
        self,
        request_id: int,
        url: str,
        payload: object,
        error: bool,
        is_playlist: bool,
    ) -> None:
        w = self.window
        s = self.state

        if request_id != s.active_fetch_request_id:
            return
        current_url = w.url_edit.text().strip()
        if url != current_url:
            s.is_fetching = False
            if current_url and not w._is_downloading:
                w._fetch_timer.start()
            w._update_controls_state()
            return
        s.is_fetching = False
        s.playlist_mode = bool(is_playlist)
        w._update_source_details_visibility()

        if error or not isinstance(payload, dict):
            s.video_labels = []
            s.video_lookup = {}
            s.audio_labels = []
            s.audio_lookup = {}
            s.filtered_labels = []
            s.filtered_lookup = {}
            w._set_preview_title("")
            w._set_source_summary(None)
            w.format_combo.clear()
            fetch_feedback = core_error_feedback.formats_fetch_failed_feedback(
                w._last_error_log
            )
            status_text = fetch_feedback.status if error else "No formats found"
            w._set_status(status_text)
            w._set_source_feedback(
                fetch_feedback.message
                if error
                else "No formats found for this URL. Try a different link.",
                tone="error" if error else "warning",
            )
            if error:
                popup_key = f"{url}|{fetch_feedback.reason}"
                if popup_key != s.last_formats_error_popup_key:
                    w._show_feedback_popup(
                        title="Could not fetch formats",
                        message=fetch_feedback.message,
                        critical=False,
                    )
                    s.last_formats_error_popup_key = popup_key
            w._update_controls_state()
            return

        collections = payload.get("collections") or {}
        s.video_labels = list(collections.get("video_labels", []))
        s.video_lookup = dict(collections.get("video_lookup", {}))
        s.audio_labels = list(collections.get("audio_labels", []))
        s.audio_lookup = dict(collections.get("audio_lookup", {}))
        preview_title = str(payload.get("preview_title") or "").strip()
        w._set_preview_title(preview_title)
        source_summary = payload.get("source_summary")
        w._set_source_summary(source_summary if isinstance(source_summary, dict) else None)
        if s.video_labels or s.audio_labels:
            w._set_status("Formats loaded")
            w._set_source_feedback(
                "Formats are ready. Choose options and start the download.",
                tone="success",
            )
        else:
            w._set_status("No formats found")
            w._set_source_feedback(
                "No formats found for this URL. Try a different link.",
                tone="warning",
            )
        w._apply_mode_formats()
        w._update_controls_state()


class RunQueueController:
    def __init__(
        self,
        window: "QtYtDlpGui",
        *,
        state: RunQueueState,
        ports: SideEffectPorts,
    ) -> None:
        self.window = window
        self.state = state
        self._ports = ports

    def _refresh_run_state(self) -> None:
        s = self.state
        if s.queue_active:
            s.run_state = RunState.QUEUE
        elif s.is_downloading and s.cancel_requested:
            s.run_state = RunState.CANCELLING
        elif s.is_downloading:
            s.run_state = RunState.SINGLE
        else:
            s.run_state = RunState.IDLE

    def on_start(self) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if s.is_downloading:
            return
        url = w.url_edit.text().strip()
        issue = core_workflow.single_start_issue(
            url=url,
            formats_loaded=bool(w._filtered_lookup),
        )
        if issue is not None:
            title, message = core_workflow.single_start_error_text(issue)
            self._ports.dialogs.critical(w, title, message)
            return

        output_dir = Path(w.output_dir_edit.text().strip()).expanduser()
        try:
            self._ports.filesystem.ensure_dir(output_dir)
        except OSError as exc:
            self._ports.dialogs.critical(
                w,
                "Output folder unavailable",
                f"Could not create/access output folder:\n{output_dir}\n\n{exc}",
            )
            return

        options = w._snapshot_download_options()
        s.run_state = RunState.SINGLE
        s.is_downloading = True
        s.cancel_requested = False
        s.cancel_event = self._ports.cancel_events.new_event()
        s.show_progress_item = True
        w._clear_logs()
        w._reset_progress_summary()
        w._clear_last_output_path()
        w._set_metrics_visible(True)
        w._set_status("Downloading...")
        w._set_source_feedback("", tone="hidden")
        w._update_controls_state()

        request, was_normalized = app_service.build_single_download_request(
            url=url,
            output_dir=output_dir,
            fmt_info=w._selected_format_info(),
            fmt_label=w._selected_format_label(),
            format_filter=w._current_container(),
            convert_to_mp4=bool(w.convert_check.isChecked()),
            playlist_enabled=bool(w._playlist_mode),
            playlist_items_raw=w.playlist_items_edit.text(),
            options=options,
        )
        if was_normalized:
            w._append_log("[info] Playlist items normalized (spaces removed).")
        if request["playlist_enabled"]:
            w._append_log(
                f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}"
            )
        self._ports.worker_executor.submit(
            self.run_single_download_worker,
            request=request,
        )

    def run_single_download_worker(self, *, request: DownloadRequest) -> None:
        result = app_service.run_download_request(
            request=request,
            cancel_event=self.state.cancel_event,
            log=lambda msg: _emit_window_signal(self.window, "log", str(msg)),
            update_progress=lambda payload: _emit_window_signal(
                self.window, "progress", dict(payload)
            ),
            record_output=lambda p: _emit_window_signal(
                self.window,
                "record_output",
                str(p),
                str(request["url"]),
            ),
        )
        _emit_window_signal(self.window, "download_done", str(result))

    def on_download_done(self, result: str) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if s.queue_active:
            return
        s.run_state = RunState.IDLE
        s.is_downloading = False
        s.cancel_requested = False
        s.cancel_event = None
        s.show_progress_item = False
        w._reset_progress_summary()
        if result == download.DOWNLOAD_SUCCESS:
            w._set_status("Download complete")
            w._set_source_feedback(
                "Download complete. You can paste another URL anytime.",
                tone="success",
            )
            w._maybe_open_output_folder()
        elif result == download.DOWNLOAD_CANCELLED:
            w._set_status("Cancelled")
            w._set_source_feedback(
                "Download cancelled. Update settings or URL and try again.",
                tone="warning",
            )
            w._clear_last_output_path()
        else:
            failure = core_error_feedback.download_failed_feedback(w._last_error_log)
            w._set_status(failure.status)
            w._set_source_feedback(
                failure.message,
                tone="error",
            )
            w._show_feedback_popup(
                title="Download failed",
                message=failure.message,
                critical=True,
            )
            w._clear_last_output_path()
        w._update_controls_state()
        w._maybe_close_after_cancel()

    def on_cancel(self) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if not s.is_downloading or s.cancel_requested:
            return
        s.cancel_requested = True
        if s.cancel_event is not None:
            s.cancel_event.set()
        s.run_state = RunState.CANCELLING
        w._set_status("Cancelling...")
        w._update_controls_state()

    def _normalize_selected_indices(self, selected_indices: list[int]) -> list[int]:
        return core_queue_logic.normalize_selected_indices(
            selected_indices,
            queue_length=len(self.state.queue_items),
        )

    def on_queue_remove_selected(self, selected_indices: list[int]) -> None:
        s = self.state
        w = self.window
        if s.queue_active:
            return
        normalized = self._normalize_selected_indices(selected_indices)
        if not normalized:
            return
        s.queue_items = core_queue_logic.remove_selected_queue_items(
            s.queue_items,
            normalized,
        )
        w._refresh_queue_panel()
        w._update_controls_state()

    def on_queue_move_up(self, selected_indices: list[int]) -> None:
        s = self.state
        w = self.window
        if s.queue_active:
            return
        updated, moved = core_queue_logic.move_selected_queue_items_up(
            s.queue_items,
            self._normalize_selected_indices(selected_indices),
        )
        if not moved:
            return
        s.queue_items = updated
        w._refresh_queue_panel()

    def on_queue_move_down(self, selected_indices: list[int]) -> None:
        s = self.state
        w = self.window
        if s.queue_active:
            return
        updated, moved = core_queue_logic.move_selected_queue_items_down(
            s.queue_items,
            self._normalize_selected_indices(selected_indices),
        )
        if not moved:
            return
        s.queue_items = updated
        w._refresh_queue_panel()

    def on_queue_clear(self) -> None:
        s = self.state
        w = self.window
        if s.queue_active:
            return
        updated, cleared = core_queue_logic.clear_queue_items(s.queue_items)
        if not cleared:
            return
        s.queue_items = updated
        w._refresh_queue_panel()
        w._update_controls_state()

    def on_add_to_queue(self) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if s.is_downloading:
            return
        url = core_urls.strip_url_whitespace(w.url_edit.text().strip())

        settings = w._capture_queue_settings()
        issue = core_queue_logic.queue_add_issue(
            url=url,
            playlist_mode=bool(w._playlist_mode or core_urls.is_playlist_url(url)),
            formats_loaded=bool(w._filtered_lookup),
            settings=settings,
        )
        if issue:
            status_text, log_text = core_queue_logic.queue_add_feedback(issue)
            w._set_status(status_text)
            w._append_log(log_text)
            return

        s.queue_items.append(core_queue_logic.queue_item(url, settings))
        w._refresh_queue_panel()
        w._set_status("Added item to queue")
        w._update_controls_state()

    def on_start_queue(self) -> None:
        self.start_queue_download()

    def start_queue_download(self) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        queue_check = core_workflow.validate_queue_start(
            is_downloading=s.is_downloading,
            queue_items=s.queue_items,
        )
        if not queue_check.can_start:
            if queue_check.invalid_index is None or queue_check.invalid_issue is None:
                return
            self._ports.dialogs.critical(
                w,
                "Missing settings",
                (
                    "Queue item "
                    f"{queue_check.invalid_index} is missing "
                    f"{core_queue_logic.queue_start_missing_detail(queue_check.invalid_issue)}."
                ),
            )
            return

        s.run_state = RunState.QUEUE
        s.queue_active = True
        s.queue_index = 0
        s.queue_failed_items = 0
        s.queue_started_ts = self._ports.clock.now_ts()
        s.is_downloading = True
        s.show_progress_item = True
        s.cancel_requested = False
        s.cancel_event = self._ports.cancel_events.new_event()
        w._clear_logs()
        w._reset_progress_summary()
        w._clear_last_output_path()
        w._set_metrics_visible(True)
        w._set_status("Downloading queue...")
        w._set_source_feedback("", tone="hidden")
        w._update_controls_state()
        w._refresh_queue_panel()
        self.start_next_queue_item()

    def start_next_queue_item(self) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if not s.queue_active or s.queue_index is None:
            return
        next_item = core_workflow.next_queue_run_item(s.queue_items, s.queue_index)
        if next_item is None:
            self.finish_queue()
            return
        s.queue_index = next_item.index
        w._append_log(
            f"[queue] item {next_item.display_index}/{next_item.total} {next_item.url}"
        )
        w._set_current_item_display(
            progress=f"{next_item.display_index}/{next_item.total}",
            title="Resolving title...",
        )
        w._refresh_queue_panel()

        self._ports.worker_executor.submit(
            self.run_queue_download_worker,
            url=next_item.url,
            settings=next_item.settings,
            index=next_item.display_index,
            total=next_item.total,
            default_output_dir=w.output_dir_edit.text().strip(),
        )

    def resolve_format_for_url(
        self, url: str, settings: QueueSettings
    ) -> dict[str, object]:
        return app_service.resolve_format_for_url(
            url=url,
            settings=settings,
            log=lambda msg: _emit_window_signal(self.window, "log", msg),
        )

    def run_queue_download_worker(
        self,
        *,
        url: str,
        settings: QueueSettings,
        index: int,
        total: int,
        default_output_dir: str,
    ) -> None:
        had_error = False
        cancelled = False
        try:
            resolved = self.resolve_format_for_url(url, settings)
            item_text = f"{index}/{total} {resolved.get('title') or url}"
            _emit_window_signal(self.window, "progress", {"status": "item", "item": item_text})

            request = app_service.build_queue_download_request(
                url=url,
                settings=settings,
                resolved=resolved,
                default_output_dir=default_output_dir,
            )

            if request["playlist_enabled"]:
                _emit_window_signal(
                    self.window,
                    "log",
                    f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}",
                )
            result = app_service.run_download_request(
                request=request,
                cancel_event=self.state.cancel_event,
                log=lambda msg: _emit_window_signal(self.window, "log", str(msg)),
                update_progress=lambda payload: _emit_window_signal(
                    self.window, "progress", dict(payload)
                ),
                record_output=lambda p: _emit_window_signal(
                    self.window, "record_output", str(p), url
                ),
                ensure_output_dir=True,
            )
            had_error = result == download.DOWNLOAD_ERROR
            cancelled = result == download.DOWNLOAD_CANCELLED
        except Exception as exc:
            had_error = True
            _emit_window_signal(self.window, "log", f"[queue] failed: {exc}")
        finally:
            _emit_window_signal(self.window, "queue_item_done", had_error, cancelled)

    def on_queue_item_done(self, had_error: bool, cancelled: bool) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state
        if not s.queue_active or s.queue_index is None:
            return
        progress = core_workflow.advance_queue_progress(
            queue_length=len(s.queue_items),
            current_index=s.queue_index,
            failed_items=s.queue_failed_items,
            cancel_requested=s.cancel_requested,
            had_error=had_error,
            cancelled=cancelled,
        )
        s.queue_failed_items = progress.failed_items
        s.cancel_requested = progress.cancel_requested
        if progress.should_finish:
            if progress.finish_cancelled:
                w._append_log("[queue] cancelled")
            self.finish_queue(cancelled=progress.finish_cancelled)
            return
        s.queue_index = progress.next_index
        if s.queue_index is None:
            w._append_log("[queue] cancelled")
            self.finish_queue()
            return
        w._reset_progress_summary()
        self.start_next_queue_item()

    def finish_queue(self, *, cancelled: bool = False) -> None:
        self._refresh_run_state()
        w = self.window
        s = self.state

        failed_items = s.queue_failed_items
        queue_started_ts = s.queue_started_ts
        s.run_state = RunState.IDLE
        s.queue_active = False
        s.queue_index = None
        s.queue_failed_items = 0
        s.queue_started_ts = None
        s.is_downloading = False
        s.show_progress_item = False
        s.cancel_requested = False
        s.cancel_event = None

        outcome = core_workflow.queue_finish_outcome(
            cancelled=cancelled,
            failed_items=failed_items,
        )
        if outcome == "cancelled":
            w._append_log("[queue] stopped by cancellation")
            w._set_status("Queue cancelled")
            w._set_source_feedback(
                "Queue cancelled. You can adjust items and restart.",
                tone="warning",
            )
            w._clear_last_output_path()
        elif outcome == "failed":
            w._append_log(f"[queue] finished with {failed_items} failed item(s)")
            failure = core_error_feedback.download_failed_feedback(w._last_error_log)
            item_label = "item" if failed_items == 1 else "items"
            w._set_status("Queue finished with errors")
            w._set_source_feedback(
                (
                    f"Queue finished with {failed_items} failed {item_label}. "
                    f"Last issue: {failure.reason}. Check Logs and retry."
                ),
                tone="warning",
            )
            w._show_feedback_popup(
                title="Queue finished with errors",
                message=(
                    f"Queue finished with {failed_items} failed {item_label}. "
                    f"Last issue: {failure.reason}."
                ),
                critical=False,
            )
        else:
            w._append_log("[queue] finished successfully")
            w._set_status("Queue complete")
            w._set_source_feedback(
                "Queue complete. Paste another URL or review your history.",
                tone="success",
            )

        if queue_started_ts is not None:
            elapsed_s = max(0.0, self._ports.clock.now_ts() - queue_started_ts)
            w._append_log(
                f"[time] Queue total time: {download.format_duration(elapsed_s)}"
            )

        if outcome != "cancelled":
            w._maybe_open_output_folder()

        w._reset_progress_summary()
        w._update_controls_state()
        w._refresh_queue_panel()
        w._maybe_close_after_cancel()
