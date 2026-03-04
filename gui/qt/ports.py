from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


class WorkerExecutor(Protocol):
    def submit(
        self,
        target: Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> None:
        ...


class ThreadWorkerExecutor:
    def submit(
        self,
        target: Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> None:
        worker = threading.Thread(
            target=target,
            args=args,
            kwargs=kwargs,
            daemon=True,
        )
        worker.start()


class InlineWorkerExecutor:
    def submit(
        self,
        target: Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> None:
        target(*args, **kwargs)


class DialogPort(Protocol):
    def critical(self, parent: object, title: str, message: str) -> None:
        ...

    def warning(self, parent: object, title: str, message: str) -> None:
        ...

    def information(self, parent: object, title: str, message: str) -> None:
        ...

    def question(
        self,
        parent: object,
        title: str,
        message: str,
        *,
        default_yes: bool,
    ) -> bool:
        ...


class FilesystemPort(Protocol):
    def ensure_dir(self, path: Path) -> None:
        ...

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        ...


class DesktopPort(Protocol):
    def open_path(self, path: Path) -> None:
        ...


class ClipboardPort(Protocol):
    def get_text(self) -> str:
        ...

    def set_text(self, value: str) -> None:
        ...


class ClockPort(Protocol):
    def now(self) -> datetime:
        ...

    def now_ts(self) -> float:
        ...


class FolderDialogPort(Protocol):
    def pick_directory(self, parent: object, title: str) -> str:
        ...


class CancelEventFactory(Protocol):
    def new_event(self) -> threading.Event:
        ...


class SystemFilesystemPort:
    def ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        path.write_text(content, encoding=encoding)


class SystemClockPort:
    def now(self) -> datetime:
        return datetime.now()

    def now_ts(self) -> float:
        return time.time()


class ThreadCancelEventFactory:
    def new_event(self) -> threading.Event:
        return threading.Event()


@dataclass
class SideEffectPorts:
    dialogs: DialogPort
    file_dialogs: FolderDialogPort
    filesystem: FilesystemPort
    desktop: DesktopPort
    clipboard: ClipboardPort
    clock: ClockPort
    cancel_events: CancelEventFactory
    worker_executor: WorkerExecutor
