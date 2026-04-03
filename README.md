# yt-dlp-gui

Simple GUI for `yt-dlp` downloads.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` available in `PATH`
- Python dependencies from `requirements.txt`

## Quick Start

Run these steps from the project root once.

### 1. Install dependencies once

macOS:

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Windows:

```powershell
winget install ffmpeg
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Run from source with `run_gui.py`

This is the main source-based way to launch the app. `run_gui.py` prefers the repo-local `.venv` interpreter when it exists, then runs the Qt app for you.

macOS:

```bash
python3 run_gui.py
```

Windows:

```powershell
python run_gui.py
```

You can still run the app directly if you want:

```bash
./.venv/bin/python -m gui
```

## Build A Packaged App

Use the packaging scripts when you want a standalone app instead of running from source.

### macOS

```bash
chmod +x scripts/build-macos.sh
./scripts/build-macos.sh
open dist/yt-dlp-gui.app
```

Output:

- `dist/yt-dlp-gui.app`

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
.\dist\yt-dlp-gui\yt-dlp-gui.exe
```

Output:

- `dist\yt-dlp-gui\yt-dlp-gui.exe`

## How To Use

1. Paste a video or playlist URL.
2. Click `Analyze URL`.
3. Choose audio or video settings.
4. Click `Download` to start immediately, or `Add to Queue` to send it to the queue panel.
5. Use `Queue`, `Logs`, and `Preferences` as needed.

Preferences are stored locally at `~/.yt-dlp-gui/settings.json` by default. You can override that path with `YT_DLP_GUI_SETTINGS_PATH`.

## Troubleshooting

### `ffmpeg` or `ffprobe` not found

macOS:

```bash
brew install ffmpeg
```

Windows:

```powershell
winget install ffmpeg
```

Then restart the terminal or app and try again.

### PySide6 is missing

Reinstall the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

If you are using source mode, make sure you are running the launcher from the project root so it can find `.venv`.

### Windows blocks the build script

Run the build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

That bypass applies only to that command.

### `Activate.ps1` is blocked

Run this once in the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the virtual environment again and continue with the install steps.

### The packaged app was built but does not work

Check that:

- `ffmpeg` and `ffprobe` are installed on the machine
- the app exists at `dist/yt-dlp-gui.app` on macOS or `dist\yt-dlp-gui\yt-dlp-gui.exe` on Windows
- you built it from the project root, not from inside `scripts/`

## Support Policy

This project is made just for fun, so I might support it or not depending on my time. Please, let me know what problems might come up and I'll try to fix them.

## Legal

Only download content you are authorized to download.
Platform terms may still restrict downloads.
By using this app, you are responsible for complying with local law and platform terms.

See:

- `docs/licenses/LICENSE`
- `docs/licenses/NOTICE`
- `docs/licenses/THIRD_PARTY_NOTICES.md`
- `docs/licenses/mutagen-GPL-2.0-or-later.txt`
- `docs/licenses/RELEASE_COMPLIANCE_CHECKLIST.md`
