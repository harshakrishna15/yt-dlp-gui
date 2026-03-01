## yt-dlp-gui

A small desktop GUI for `yt-dlp`.
This is a hobby project.
Paste a URL, pick a format, and download.

### Supported Platforms

- macOS
- Windows

### Prerequisites

- Python 3.10+
- `ffmpeg` and `ffprobe` in `PATH`
- Qt dependency: `PySide6` (installed from `requirements.txt`)

### Install and Run

Run these steps in the project folder.

#### macOS

1. Open **Terminal**.
2. Go to this project folder.
3. Run:

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 run_gui.py
```

4. Next time, run:

```bash
cd /path/to/yt-dlp-gui
source .venv/bin/activate
python3 run_gui.py
```

#### Windows

1. Open **PowerShell**.
2. Go to this project folder.
3. Run:

```powershell
winget install ffmpeg
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_gui.py
```

4. Next time, run:

```powershell
cd C:\path\to\yt-dlp-gui
.\.venv\Scripts\Activate.ps1
python run_gui.py
```

#### Check ffmpeg

Run `ffmpeg -version`.  
If you see a version, it is installed.

### Run Tests

Tests include core unit tests and Qt UI tests (offscreen). No network calls.

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

### Code Structure

Core logic is shared across the Qt app:

- `gui/common/`: shared helpers, download/runtime integration, types, diagnostics/history stores
- `gui/core/`: UI-agnostic logic (queue checks, download planning, URL helpers, format selection, option parsing)
- `gui/services/`: shared orchestration used by the frontend (request building/execution, history recording)
- `gui/qt/`: Qt-specific frontend modules

### Build Packaged App

Build distributable app output from source.

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

macOS: run `brew install ffmpeg`, then restart Terminal.  
Windows: run `winget install ffmpeg`, then open a new PowerShell window.

#### 2) PySide6 is missing

macOS: activate `.venv`, then run `python3 -m pip install -r requirements.txt`.  
Windows: activate `.venv`, then run `python -m pip install -r requirements.txt`.

#### 3) Build/run command differences

macOS: `source .venv/bin/activate`  
Windows: `.\.venv\Scripts\Activate.ps1`

#### 4) PowerShell blocks the Windows build script (unsigned script policy)

If the script is blocked because there is no trusted signature, run the build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

This bypass only applies to that one command.

### Usage Notes

- You can download playlists.
- Use **Playlist items** for ranges like `1-5,7,10-`.
- Leave Playlist items blank to download the full playlist.

### Support Policy

This is maintained in my spare time.
I might fix things when I can, but there are no guarantees for support, updates, or compatibility fixes.

Issues and PRs are welcome, but implementing fixes depends on my free time.

### Legal

Only download content you are authorized to download.
Platform terms may still restrict downloads.
By using this app, you are responsible for complying with local law and platform terms.

See:

- `docs/licenses/LICENSE`
- `docs/licenses/NOTICE`
- `docs/licenses/THIRD_PARTY_NOTICES.md`
- `docs/licenses/mutagen-GPL-2.0-or-later.txt`
- `docs/licenses/RELEASE_COMPLIANCE_CHECKLIST.md`
