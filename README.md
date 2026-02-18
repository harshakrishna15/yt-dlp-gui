## yt-dlp-gui

A small desktop GUI for `yt-dlp`.
This is a hobby project.
Paste a URL, pick a format, and download.

### Supported Platforms

- macOS
- Windows

### Prerequisites

- Python 3.10+ (with Tk/Tkinter)
- Dependencies from `requirements.txt`
- `ffmpeg` and `ffprobe` available in `PATH`
- Optional for Qt spike UI: `requirements-qt.txt`

### Set Up From Source (Developer Setup)

This section installs dependencies for running the code from this repo.
It does not install a packaged app.

- macOS

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- Windows

```powershell
winget install ffmpeg
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Optional: Install Qt Spike UI

This is an alternate frontend experiment (`PySide6`) to evaluate a cleaner layout.
It does not yet replace the full Tk feature set.

- macOS / Windows

```bash
pip install -r requirements-qt.txt
```

### Run From Source

- macOS

```bash
source .venv/bin/activate
python3 run_gui.py
```

- Windows

```powershell
.\.venv\Scripts\Activate.ps1
python run_gui.py
```

Run the Qt spike frontend:

- macOS

```bash
source .venv/bin/activate
python3 run_gui.py --ui qt
```

- Windows

```powershell
.\.venv\Scripts\Activate.ps1
python run_gui.py --ui qt
```

### Run Tests

The tests are pure unit tests (no GUI startup, no network calls).

- macOS

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests -v
```

- Windows

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

### Build Packaged App

This section builds distributable app output from the source code.

- macOS

```bash
chmod +x scripts/build-macos.sh
./scripts/build-macos.sh
```

Output: `dist/yt-dlp-gui.app`

- Windows

```powershell
.\scripts\build-windows.ps1
```

Output: `dist\yt-dlp-gui\yt-dlp-gui.exe`

### Common Problems

#### 1) `ffmpeg` or `ffprobe` not found

macOS:
Install with `brew install ffmpeg`, then restart your terminal.

Windows:
Install with `winget install ffmpeg`, then open a new PowerShell window so `PATH` refreshes.

#### 2) Tkinter is missing

macOS:
If you use Homebrew Python and Tk is missing, install matching Tk support (example: `brew install python-tk@3.11`).

Windows:
Reinstall Python from `python.org` and make sure Tcl/Tk is included (default installer option), then recreate `.venv`.

#### 3) Build/run command differences

macOS:
Use `source .venv/bin/activate`. Paths use `/`.

Windows:
Use `.venv\Scripts\Activate.ps1`. Paths use `\`.

#### 4) PowerShell blocks the Windows build script (unsigned script policy)

If the script is blocked because there is no trusted signature, run the build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

This command runs a new powershell processes, bypasses the execution check for ONLY this process, and runs the script.

Use this command to allow the script to install needed build dependencies and build the app in the current session.

### Usage Notes

- You can download playlists.
- Use **Playlist items** for ranges like `1-5,7,10-`.
- Leave Playlist items blank to download the full playlist.

### Support Policy

This is maintained in my spare time.
I might fix things when I can, but there are no guarantees for support, updates, or compatibility fixes.

Issues and PRs are welcome, and but implementing fixes is based on my free time.

### Legal

Only download content you are authorized to download.
Platform terms may still restrict downloads.
By using this app, you are responsible for complying with local law and platform terms.

See:

- `licenses/LICENSE`
- `licenses/NOTICE`
- `licenses/THIRD_PARTY_NOTICES.md`
- `licenses/mutagen-GPL-2.0-or-later.txt`
- `licenses/RELEASE_COMPLIANCE_CHECKLIST.md`
