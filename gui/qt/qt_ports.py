from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .ports import (
    SideEffectPorts,
    SystemClockPort,
    SystemFilesystemPort,
    ThreadCancelEventFactory,
    ThreadWorkerExecutor,
)


class QtDialogPort:
    def critical(self, parent: object, title: str, message: str) -> None:
        QMessageBox.critical(parent, title, message)

    def warning(self, parent: object, title: str, message: str) -> None:
        QMessageBox.warning(parent, title, message)

    def information(self, parent: object, title: str, message: str) -> None:
        QMessageBox.information(parent, title, message)

    def question(
        self,
        parent: object,
        title: str,
        message: str,
        *,
        default_yes: bool,
    ) -> bool:
        yes_no = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        default = (
            QMessageBox.StandardButton.Yes
            if default_yes
            else QMessageBox.StandardButton.No
        )
        choice = QMessageBox.question(parent, title, message, yes_no, default)
        return choice == QMessageBox.StandardButton.Yes


class QtFolderDialogPort:
    def pick_directory(self, parent: object, title: str) -> str:
        return str(QFileDialog.getExistingDirectory(parent, title) or "")


class QtDesktopPort:
    def open_path(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class QtClipboardPort:
    def get_text(self) -> str:
        return str(QApplication.clipboard().text() or "")

    def set_text(self, value: str) -> None:
        QApplication.clipboard().setText(str(value))


def build_qt_side_effect_ports() -> SideEffectPorts:
    return SideEffectPorts(
        dialogs=QtDialogPort(),
        file_dialogs=QtFolderDialogPort(),
        filesystem=SystemFilesystemPort(),
        desktop=QtDesktopPort(),
        clipboard=QtClipboardPort(),
        clock=SystemClockPort(),
        cancel_events=ThreadCancelEventFactory(),
        worker_executor=ThreadWorkerExecutor(),
    )
