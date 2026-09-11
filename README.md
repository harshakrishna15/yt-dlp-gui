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
Each build downloads and verifies the latest stable official yt-dlp release.
macOS uses the official unpacked runtime, installed once instead of unpacking a
single-file executable on every Analyze or Download. First-run validation can
still take several seconds; later launches reuse the installed runtime. The
in-app updater verifies and replaces the executable and libraries together, with
rollback if installation fails.
Packaged apps keep an updateable copy in the user's application-data directory;
use `Update yt-dlp` in Preferences for later yt-dlp releases.
The updater shows download progress, transfer speed, and an estimated download
time remaining when the server supplies a file size. Checking, verification,
and installation use a loading indicator rather than a guessed completion time.

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
5. Use `Queue` to manage pending downloads. Activity logs are available under `Preferences` > `View logs`.

Analysis shows live yt-dlp status, an activity indicator, elapsed time, and
`Cancel analysis` in the status row. Changing the URL cancels the previous lookup;
closing the window waits for active lookups to stop. Metadata requests use a
15-second socket timeout, one retry, and a 90-second overall limit. Network and
site response times still affect how long analysis takes.

The window opens before background tool checks finish. Progress rendering is
limited to ten updates per second, while cancellation, errors, and completion
remain immediate. Logs are buffered while their panel is hidden, and queue rows
are updated without rebuilding the list on every progress tick.

Revisiting a video can reuse its format preview for up to two minutes during the
same session. This cache holds at most 12 previews and 4 MiB of serialized data;
it does not store stream URLs, headers, or fragments. Live videos and playlists
are not cached. `Refresh formats` bypasses the cache, and engine updates or
closing the app clear it. Downloads still resolve fresh media through yt-dlp.
The preview cache is never written to disk and does not retain folder choices.

New queue items save a yt-dlp format selector (not media URLs), avoiding a second
analysis request when downloading. Older queue settings still use cancellable
metadata resolution. Queue rows retain session-only Completed, Failed, or
Cancelled results; `Retry failed` leaves successful items alone. Right-click a
completed row to reveal its output file.

Destination creation, write checks, media-tool checks, and estimated disk-space
checks run in download workers. Known sizes include processing headroom; unknown
sizes do not block downloads. These are estimates, not space reservations.
MP4 files are inspected before edit-friendly processing. Compatible H.264/AAC
streams with verified constant packet timing are kept without re-encoding;
unsupported or uncertain files still use the existing encoder fallback.

Preferences are stored locally at `~/.yt-dlp-gui/settings.json` by default. You can
override that path with `YT_DLP_GUI_SETTINGS_PATH`. The output folder is
session-only and resets to the computer's Downloads folder each time the app starts.

Before deleting the app, use `Preferences` > `Remove app data and quit...`.
The confirmation lists the settings file and managed engine support paths. The
cleanup runs only while idle, preserves unrelated files and downloaded media,
and quits without recreating settings. Opening the app again recreates its engine.
Deleting the `.app` alone does not remove these external support files.
yt-dlp disk caching is disabled for analysis and downloads. Pre-existing shared
yt-dlp caches, system-installed tools, and exported logs/diagnostics are not
deleted because they may belong to other programs or were explicitly saved.

### Appearance

The interface uses flat controls and the system font. Download progress and
Cancel appear only during a download; update progress remains in Preferences.
Results use a single dismissible status row, with Show in Finder (or Show in folder) after a successful
download and View details for errors. Update results stay in Preferences without
an extra popup; progress and estimated download time remain visible while updating.
The main form shows media type, quality, and destination. Container, codec, and
custom filename are under Advanced, with a summary of custom settings when
collapsed. Video defaults to MP4/H.264 and audio to M4A after analysis. The folder
name is shown inline; hover it for the full path or use the folder button to change it.
Advanced settings open and close with a short, smooth reveal.
Set `YT_DLP_GUI_REDUCE_MOTION=1` to disable navigation and Advanced animations.
This is a launch-time environment override, not a saved preference.

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
