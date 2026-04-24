from __future__ import annotations

import sys


APP_REPO_NAME = "yt-dlp-gui"
APP_DISPLAY_NAME = APP_REPO_NAME
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Fast local downloads."
APP_PRIVACY_NOTE = "Downloads stay on this machine."
APP_SHORTCUT_LINES = (
    "Cmd/Ctrl+L: Focus source actions",
    "Cmd/Ctrl+V: Paste URL when another text field is not active",
    "Cmd/Ctrl+,: Open settings",
    "F1: About",
)
APP_ORGANIZATION_NAME = "yt-dlp-gui"
APP_ORGANIZATION_DOMAIN = "local.yt-dlp-gui"
APP_BUNDLE_IDENTIFIER = "local.yt-dlp-gui.desktop"
MACOS_APP_ICON_FILENAME = "tmp-mac-app-icon.png"
WINDOWS_APP_ICON_FILENAME = "tmp-windows-app-icon.png"


def app_icon_filename_for_platform(platform: str) -> str:
    if platform.startswith("win"):
        return WINDOWS_APP_ICON_FILENAME
    return MACOS_APP_ICON_FILENAME


APP_ICON_FILENAME = app_icon_filename_for_platform(sys.platform)
