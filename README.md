# yt-dlp-gui

Small desktop GUI for local `yt-dlp` downloads on macOS and Windows.

The app is built around a simple workflow:

1. Paste a video or playlist URL.
2. Analyze the URL to load available formats.
3. Choose output settings.
4. Download immediately or add the item to a queue.

Downloads, logs, and preferences stay on your machine. This is a spare-time project and support is best-effort.

## Supported Platforms

- macOS
- Windows

## Current Features

- Analyze a URL before downloading to load available audio and video formats
- Download a single item immediately or build a reusable download queue
- Choose audio or video mode, output container, codec, and quality
- Handle playlist URLs, including optional playlist ranges like `1-5,7,10-`
- Prompt for mixed YouTube URLs that contain both a direct video ID and a playlist ID
- Set a custom filename for single-video downloads
- Re-encode WebM video to MP4 when needed
- Review activity in the built-in logs panel
- Reorder, edit, or clear queued items from the queue panel
- Save preferences such as output folder behavior and edit-friendly MP4 encoder selection
- Export a diagnostics report to the selected output folder

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` available in `PATH`
- Python dependencies from `requirements.txt`

`yt-dlp` is installed as a Python dependency from `requirements.txt`; you do not need a separate standalone `yt-dlp` binary for local development.

## Install And Run

Run these steps from the project root. Setup is the same either way; after that you can launch the app directly with `python -m gui` or use `run_gui.py`.

### 1. Install dependencies once

#### macOS

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

#### Windows

```powershell
winget install ffmpeg
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If `Activate.ps1` is blocked by your PowerShell policy, run this once in the current PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the environment and continue with the install steps.

### 2. Choose how to launch the app from source

#### Option A: Run the app directly

Use this when you already have the virtual environment activated and want the most explicit entry point.

macOS:

```bash
source .venv/bin/activate
python3 -m gui
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m gui
```

#### Option B: Use `run_gui.py`

Use this when you want a simple launcher command or want to double-click the script. `run_gui.py` prefers the local `.venv` Python interpreter when it exists, then runs `python -m gui` for you.

macOS:

```bash
python3 run_gui.py
```

Windows:

```powershell
python run_gui.py
```

You can also pass normal app arguments through the launcher, for example:

```bash
python3 run_gui.py --ui qt
```

## How To Use The App

1. Paste a video or playlist URL.
2. Click `Analyze URL` to load formats and preview details.
3. If the URL can be treated as either a single video or a playlist, choose the mode you want.
4. Pick `Video` or `Audio`, then choose the container, codec, and quality you want.
5. Optionally set:
   - `Playlist items` for playlist downloads
   - `File name` for single-video downloads
   - output folder
6. Click `Download` to start immediately, or `Add to queue` to save the current URL and settings as a queue item.
7. Use the `Queue` panel to reorder items, edit an existing item, or clear the queue.
8. Use the `Logs` panel to inspect format fetches, download progress, and failures.
9. Open `Preferences` to:
   - choose the edit-friendly MP4 encoder preference
   - enable opening the output folder after downloads finish
   - export a diagnostics report

Preferences are stored locally at `~/.yt-dlp-gui/settings.json` by default. You can override that path with `YT_DLP_GUI_SETTINGS_PATH`.

## Entry Points

- `python -m gui`
  Direct source entry point. Best when your virtual environment is already active.
- `python run_gui.py`
  Convenience launcher. Best when you want the repo-local `.venv` to be picked automatically or want a double-clickable script.

## Run Tests

The test suite includes core unit tests and Qt UI tests. It does not require live network access.

### macOS

```bash
source .venv/bin/activate
python3 scripts/run_tests.py -v
```

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_tests.py -v
```

## Build Standalone Apps

Use the packaging scripts when you want a standalone app bundle instead of running from source. The scripts create `.venv` if needed, install build dependencies, generate fresh app icons, and run PyInstaller.

### macOS

```bash
chmod +x scripts/build-macos.sh
./scripts/build-macos.sh
python3 scripts/check_packaged_assets.py dist/yt-dlp-gui.app
```

Output: `dist/yt-dlp-gui.app`

Run the built app:

```bash
open dist/yt-dlp-gui.app
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
python scripts/check_packaged_assets.py dist\yt-dlp-gui
```

Output: `dist\yt-dlp-gui\yt-dlp-gui.exe`

Run the built app:

```powershell
.\dist\yt-dlp-gui\yt-dlp-gui.exe
```

Packaged builds still expect `ffmpeg` and `ffprobe` to be available on the system.

## Project Layout

- `gui/common/`: shared helpers for downloads, settings, diagnostics, and format handling
- `gui/core/`: UI-agnostic logic for queue handling, option parsing, workflow checks, and presentation shaping
- `gui/services/`: app-facing orchestration for building and running download requests
- `gui/qt/`: Qt application, controllers, widgets, assets, and styling
- `scripts/`: build, packaging, and test helpers
- `tests/`: unit and Qt UI tests

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

Activate the virtual environment and reinstall dependencies:

```bash
python -m pip install -r requirements.txt
```

### Format loading or downloads fail

Open the `Logs` panel first. If you need to share or inspect more context, use `Preferences -> Export diagnostics` to write a diagnostics report into the current output folder.

### Windows blocks the build script

Run the build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

That bypass applies only to that command.

## Support Policy

This project is maintained in spare time. Issues and pull requests are welcome, but there is no guaranteed support timeline.

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
