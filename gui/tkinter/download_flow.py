from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from ..common import download
from ..common.types import DownloadOptions
from ..core import workflow as core_workflow
from ..services import app_service
from .constants import PROGRESS_ANIM_MS


class DownloadFlowMixin:
    def _reset_progress_summary(self) -> None:
        self.progress_pct_var.set("—")
        self.progress_speed_var.set("—")
        self.progress_eta_var.set("—")
        self.progress_item_var.set("—")
        self._progress_pct_target = 0.0
        self._progress_pct_display = 0.0
        self._cancel_after("_progress_anim_after_id")

    def _on_progress_update(self, update: dict) -> None:
        status = update.get("status")
        if status == "downloading":
            pct = update.get("percent")
            if isinstance(pct, (int, float)):
                self._progress_pct_target = float(max(0.0, min(100.0, pct)))
                if self._progress_anim_after_id is None:
                    self._progress_anim_tick()
            speed = update.get("speed")
            eta = update.get("eta")
            if isinstance(speed, str):
                self.progress_speed_var.set(speed or "—")
            # Hold last known ETA if the new value is blank/unknown.
            if isinstance(eta, str):
                eta_clean = eta.strip()
                if eta_clean and eta_clean != "—":
                    self.progress_eta_var.set(eta_clean)
        elif status == "item":
            if not self._show_progress_item:
                return
            item = update.get("item")
            if isinstance(item, str) and item.strip():
                self.progress_item_var.set(item.strip())
        elif status == "finished":
            self._progress_pct_target = 100.0
            if self._progress_anim_after_id is None:
                self._progress_anim_tick()
        elif status == "cancelled":
            self._progress_pct_target = 0.0

    def _progress_anim_tick(self) -> None:
        ease = 0.22
        delta = self._progress_pct_target - self._progress_pct_display
        if abs(delta) < 0.05:
            self._progress_pct_display = self._progress_pct_target
            self.progress_pct_var.set(f"{self._progress_pct_display:.1f}%")
            self._progress_anim_after_id = None
            return
        self._progress_pct_display += delta * ease
        self.progress_pct_var.set(f"{self._progress_pct_display:.1f}%")
        self._progress_anim_after_id = self._safe_after(
            PROGRESS_ANIM_MS, self._progress_anim_tick
        )

    def _snapshot_download_options(self) -> DownloadOptions:
        custom_filename_var = getattr(self, "custom_filename_var", None)
        custom_filename = ""
        if custom_filename_var is not None:
            try:
                custom_filename = str(custom_filename_var.get())
            except (
                tk.TclError,
                RuntimeError,
                TypeError,
                ValueError,
                AttributeError,
            ):
                custom_filename = ""
        return app_service.build_download_options(
            network_timeout_raw=self.network_timeout_var.get(),
            network_retries_raw=self.network_retries_var.get(),
            retry_backoff_raw=self.retry_backoff_var.get(),
            subtitle_languages_raw=self.subtitle_languages_var.get(),
            write_subtitles_requested=bool(self.write_subtitles_var.get()),
            embed_subtitles_requested=bool(self.embed_subtitles_var.get()),
            is_video_mode=self.mode_var.get() == "video",
            audio_language_raw=self.audio_language_var.get(),
            custom_filename_raw=custom_filename,
        )

    def _on_start(self) -> None:
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        issue = core_workflow.single_start_issue(
            url=url,
            formats_loaded=bool(self.formats.filtered_lookup),
        )
        if issue is not None:
            title, message = core_workflow.single_start_error_text(issue)
            messagebox.showerror(title, message)
            return
        output_dir = self._ensure_output_dir(self.output_dir_var.get())
        if output_dir is None:
            return
        fmt_label = self.format_var.get()
        fmt_info = self.formats.filtered_lookup.get(fmt_label)
        format_filter = self.format_filter_var.get()
        playlist_enabled = bool(self.playlist_enabled_var.get())
        playlist_items_raw = (self.playlist_items_var.get() or "").strip()
        convert_to_mp4 = bool(self.convert_to_mp4_var.get())
        options = self._snapshot_download_options()

        self.is_downloading = True
        self._cancel_requested = False
        self._cancel_event = threading.Event()
        self._show_progress_item = bool(playlist_enabled and self.is_playlist)
        self.simple_state_var.set("Downloading")
        self.status_var.set("Downloading...")
        self.logs.clear()
        self._reset_progress_summary()
        self._update_controls_state()
        self.download_thread = threading.Thread(
            target=self._run_download,
            kwargs={
                "url": url,
                "output_dir": output_dir,
                "fmt_label": fmt_label,
                "fmt_info": fmt_info,
                "format_filter": format_filter,
                "playlist_enabled": playlist_enabled,
                "playlist_items_raw": playlist_items_raw,
                "convert_to_mp4": convert_to_mp4,
                "network_timeout_s": options["network_timeout_s"],
                "network_retries": options["network_retries"],
                "retry_backoff_s": options["retry_backoff_s"],
                "subtitle_languages": options["subtitle_languages"],
                "write_subtitles": options["write_subtitles"],
                "embed_subtitles": options["embed_subtitles"],
                "audio_language": options["audio_language"],
                "custom_filename": options["custom_filename"],
            },
            daemon=True,
        )
        self.download_thread.start()

    def _on_cancel(self) -> None:
        if not self.is_downloading or self._cancel_requested:
            return
        self._cancel_requested = True
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.simple_state_var.set("Cancelling…")
        self.status_var.set("Cancelling download…")
        self._log("[cancel] Cancellation requested.")
        self._update_controls_state()

    def _run_download(
        self,
        url: str,
        output_dir: Path,
        fmt_label: str,
        fmt_info: dict | None,
        format_filter: str,
        playlist_enabled: bool,
        playlist_items_raw: str,
        convert_to_mp4: bool,
        network_timeout_s: int = download.YDL_SOCKET_TIMEOUT_SECONDS,
        network_retries: int = download.YDL_ATTEMPT_RETRIES,
        retry_backoff_s: float = download.YDL_RETRY_BACKOFF_SECONDS,
        subtitle_languages: list[str] | None = None,
        write_subtitles: bool = False,
        embed_subtitles: bool = False,
        audio_language: str = "",
        custom_filename: str = "",
    ) -> None:
        options: DownloadOptions = {
            "network_timeout_s": network_timeout_s,
            "network_retries": network_retries,
            "retry_backoff_s": retry_backoff_s,
            "subtitle_languages": list(subtitle_languages or []),
            "write_subtitles": bool(write_subtitles),
            "embed_subtitles": bool(embed_subtitles),
            "audio_language": audio_language,
            "custom_filename": custom_filename,
        }
        request, was_normalized = app_service.build_single_download_request(
            url=url,
            output_dir=output_dir,
            fmt_info=fmt_info,
            fmt_label=fmt_label,
            format_filter=format_filter,
            convert_to_mp4=convert_to_mp4,
            playlist_enabled=playlist_enabled,
            playlist_items_raw=playlist_items_raw,
            options=options,
        )
        if was_normalized:
            self._log("[info] Playlist items normalized (spaces removed).")
        if request["playlist_enabled"]:
            self._log(f"[playlist] enabled=1 items={request['playlist_items'] or 'none'}")

        result = app_service.run_download_request(
            request=request,
            cancel_event=self._cancel_event,
            log=self._log,
            update_progress=lambda u: self._post_ui(self._on_progress_update, u),
            record_output=lambda p: self._post_ui(self._record_download_output, p, url),
        )
        if result == download.DOWNLOAD_ERROR:
            self._log("[status] Download finished with errors.")
        self._post_ui(self._on_finish)

    def _on_finish(self) -> None:
        self.is_downloading = False
        self._cancel_requested = False
        self._cancel_event = None
        self._show_progress_item = False
        self.simple_state_var.set("Idle")
        self.status_var.set("Idle")
        self._reset_progress_summary()
        self._update_controls_state()
