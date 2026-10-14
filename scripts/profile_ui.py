#!/usr/bin/env python3
"""Run a repeatable native Qt stress workload without network or user data.

Measures event dispatch, backing-store updates, and animation callback cadence.
These are diagnostic timings, not compositor presentation FPS. Use a native
Instruments recording alongside this workload to validate presentation deadlines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import threading
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase-seconds", type=float, default=8)
    parser.add_argument("--start-delay", type=float, default=5)
    parser.add_argument("--queue-size", type=int, default=500)
    parser.add_argument("--phases", nargs="+", default=[
        "navigation", "advanced", "queue_scroll", "download_progress", "queue_download", "visible_logs", "resize",
    ], choices=["navigation", "advanced", "queue_scroll", "download_progress", "queue_download", "visible_logs", "resize"])
    args = parser.parse_args()
    if args.phase_seconds < 2 or args.queue_size < 1:
        parser.error("Use at least 2 seconds per phase and one queue item")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="yt-dlp-gui-profile-") as directory:
        os.environ["YT_DLP_GUI_SETTINGS_PATH"] = str(Path(directory) / "settings.json")
        os.environ["YT_DLP_GUI_DATA_DIR"] = str(Path(directory) / "data")
        from PySide6.QtCore import QEvent, QTimer, Qt
        from PySide6.QtWidgets import QApplication
        from gui.qt.app import QtYtDlpGui
        from gui.qt.widgets import AnimatedSegmentedRail

        samples: dict[str, dict[str, list[float]]] = {}
        exposure: dict[str, dict[str, int]] = {}
        phase_windows: list[dict[str, object]] = []
        phase = "warmup"
        animations: dict[int, float] = {}

        def record(kind: str, value: float) -> None:
            if phase != "warmup":
                samples.setdefault(phase, {}).setdefault(kind, []).append(value)

        class ProfileApp(QApplication):
            def notify(self, receiver, event):
                started = time.perf_counter_ns()
                try:
                    return super().notify(receiver, event)
                finally:
                    elapsed = (time.perf_counter_ns() - started) / 1e6
                    if event.type() == QEvent.Type.UpdateRequest:
                        record("backing_store_ms", elapsed)
                    if event.type() == QEvent.Type.Paint:
                        record("widget_paint_ms", elapsed)
                    if elapsed > 1:
                        record("dispatch_over_1ms", elapsed)

        original_selection = AnimatedSegmentedRail._set_selection_rect

        def selection_frame(rail, value):
            now = time.perf_counter()
            identity = id(rail._selection_anim)
            if identity in animations:
                interval = (now - animations[identity]) * 1000
                if interval < 100:
                    record("selection_callback_interval_ms", interval)
            animations[identity] = now
            original_selection(rail, value)

        AnimatedSegmentedRail._set_selection_rect = selection_frame
        app = ProfileApp([])
        app.setApplicationName("yt-dlp-gui Performance")
        window = QtYtDlpGui()
        window.setWindowTitle("yt-dlp-gui Performance (synthetic data)")
        # A covered Cocoa window can stop painting entirely. Keep this isolated
        # test surface visible, and record exposure rather than accepting zeros.
        window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        window._tool_checks_pending = False
        window._tool_checks_started = True
        class NoopExecutor:
            def submit(self, *_args, **_kwargs):
                pass
        window._effects.worker_executor = NoopExecutor()
        window.url_edit.setText("https://example.test/profile")
        window._video_labels = ["1080p MP4"]
        window._video_lookup = {"1080p MP4": {
            "format_id": "137", "ext": "mp4", "vcodec": "avc1", "acodec": "none",
        }}
        window._audio_labels = ["Best audio only"]
        window._audio_lookup = {"Best audio only": {
            "custom_format": "bestaudio/best", "is_audio_only": True,
        }}
        window._apply_output_defaults()
        window._apply_mode_formats()
        window.queue_items = [
            {"url": f"https://example.test/{index}", "title": f"Stress video {index} " + "long title " * 8,
             "settings": {"mode": "video", "format_filter": "mp4", "codec_filter": "avc1",
                          "format_label": "1080p MP4", "output_dir": directory}}
            for index in range(args.queue_size)
        ]
        window._refresh_queue_panel()
        for index in range(1000):
            window._append_log(f"[profile] Existing log line {index} " + "detail " * 20)
        window._update_controls_state()
        window.resize(1100, 820)
        window.show()
        window.raise_()
        window.activateWindow()

        original_reveal = window._apply_advanced_reveal
        previous_reveal = [None]

        def reveal(progress):
            now = time.perf_counter()
            if previous_reveal[0] is not None:
                interval = (now - previous_reveal[0]) * 1000
                if 1 < interval < 100:
                    record("advanced_callback_interval_ms", interval)
            previous_reveal[0] = now
            started = time.perf_counter_ns()
            original_reveal(progress)
            record("advanced_layout_ms", (time.perf_counter_ns() - started) / 1e6)

        window._apply_advanced_reveal = reveal
        phases = args.phases
        started = time.perf_counter() + args.start_delay
        previous_phase = [None]
        step = [0]
        stop_worker = threading.Event()
        worker_enabled = threading.Event()

        def worker():
            index = 0
            while not stop_worker.wait(0.001):
                if not worker_enabled.is_set():
                    continue
                index += 1
                window._signals.progress.emit({"status": "downloading", "percent": (index % 10000) / 100,
                                               "speed": "20 MiB/s", "eta": "00:30"})
                if index % 10 == 0:
                    window._signals.log.emit(f"[profile] Download log {index} " + "detail " * 20)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def tick():
            nonlocal phase, started
            elapsed = time.perf_counter() - started
            if elapsed < 0:
                return
            if previous_phase[0] is None and not window.windowHandle().isExposed():
                started = time.perf_counter() + 0.5
                return
            index = int(elapsed / args.phase_seconds)
            if index >= len(phases):
                if phase_windows:
                    phase_windows[-1]["end_epoch_s"] = time.time()
                timer.stop()
                stop_worker.set()
                app.quit()
                return
            phase = phases[index]
            if previous_phase[0] != phase:
                now_epoch = time.time()
                if phase_windows:
                    phase_windows[-1]["end_epoch_s"] = now_epoch
                phase_windows.append({"phase": phase, "start_epoch_s": now_epoch})
                previous_phase[0] = phase
                step[0] = 0
                worker_enabled.clear()
                window._is_downloading = False
                window.queue_active = False
                window._show_main_workspace()
                window._update_controls_state()
                if phase == "queue_scroll":
                    window._open_panel("queue")
                if phase == "queue_download":
                    window._run_queue_controller.start_queue_download()
                    window._open_panel("queue")
                    worker_enabled.set()
                if phase in {"download_progress", "visible_logs"}:
                    window._is_downloading = True
                    window._show_progress_item = True
                    window._update_controls_state()
                    worker_enabled.set()
                    if phase == "visible_logs":
                        for line in range(1000):
                            window._append_log(f"[profile] Existing log {line} " + "detail " * 20)
                        window._open_panel("logs")
                print(f"PHASE {phase}", flush=True)
            step[0] += 1
            counts = exposure.setdefault(phase, {"ticks": 0, "exposed_ticks": 0, "active_ticks": 0})
            counts["ticks"] += 1
            counts["exposed_ticks"] += bool(window.windowHandle().isExposed())
            counts["active_ticks"] += bool(window.isActiveWindow())
            started_work = time.perf_counter_ns()
            if phase == "navigation" and step[0] % 20 == 1:
                if (step[0] // 20) % 3 == 0:
                    window._open_panel("queue")
                elif (step[0] // 20) % 3 == 1:
                    window._open_panel("settings")
                else:
                    window._show_main_workspace()
            elif phase == "advanced" and step[0] % 25 == 1:
                window.advanced_toggle.click()
            elif phase == "queue_scroll":
                bar = window.queue_list.verticalScrollBar()
                bar.setValue((step[0] * 27) % max(1, bar.maximum()))
            elif phase == "download_progress" and step[0] % 25 == 1:
                window.advanced_toggle.click()
            elif phase == "queue_download" and step[0] % 50 == 1:
                window._run_queue_controller.on_queue_item_done(False, False)
            elif phase == "visible_logs" and step[0] % 25 == 1:
                bar = window.logs_view.verticalScrollBar()
                bar.setValue(bar.maximum() if step[0] % 50 == 1 else 0)
            elif phase == "resize":
                window.resize(1100 + round(170 * math.sin(step[0] / 25)),
                              820 + round(170 * math.sin(step[0] / 31)))
            record("workload_action_ms", (time.perf_counter_ns() - started_work) / 1e6)

        timer = QTimer()
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.setInterval(16)
        timer.timeout.connect(tick)
        timer.start()
        print(f"READY pid={os.getpid()} platform={app.platformName()} refresh_hz={app.primaryScreen().refreshRate()}", flush=True)
        exit_code = app.exec()
        stop_worker.set()
        thread.join(timeout=2)
        window._is_downloading = False
        window.queue_active = False
        window.close()

        def summary(values):
            ordered = sorted(values)
            return {"count": len(ordered), "p50": ordered[len(ordered)//2],
                    "p95": ordered[min(len(ordered)-1, int(len(ordered)*.95))],
                    "max": ordered[-1], "over_16_67ms": sum(v > 1000/60 for v in ordered)}

        result = {"platform": app.platformName(), "refresh_hz": app.primaryScreen().refreshRate(),
                  "queue_size": args.queue_size, "phase_seconds": args.phase_seconds,
                  "exposure": exposure,
                  "phase_windows": phase_windows,
                  "phases": {name: {kind: summary(values) for kind, values in kinds.items()}
                             for name, kinds in samples.items()},
                  "limitations": "Callback cadence and backing-store CPU time are not compositor presentation FPS. Synthetic workload; no network or user data."}
        result["source_sha256"] = {
            name: hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
            for name in ("gui/qt/app.py", "gui/qt/controllers.py", "gui/qt/widgets.py")
        }
        result["native_visible_capture"] = bool(
            app.platformName() == "cocoa" and exposure
            and all(counts["exposed_ticks"] == counts["ticks"] for counts in exposure.values())
            and all(samples.get(name, {}).get("widget_paint_ms") for name in phases)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
