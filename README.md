## yt-dlp-gui

Small desktop UI for `yt-dlp`.
Paste a URL, pick a format, and download without using the terminal.

This is a hobby and personal-use project.

### Requirements

- Python 3.10+ (with Tk)
- Dependencies in `requirements.txt` (includes Python `yt-dlp`)
- `ffmpeg` and `ffprobe` available on your `PATH`

### Quick Start

1. Install Python with Tk support.
2. Create and activate a virtual environment.
3. Install dependencies and run the app.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run_gui.py
```

Homebrew note: if Tk is missing, install the matching `python-tk` formula (for example `brew install python-tk@3.11`).

### FFmpeg / FFprobe

`yt-dlp` can download some formats without FFmpeg, but FFmpeg/FFprobe are needed for common tasks like merging streams and format conversion.

Install before running:

- macOS: `brew install ffmpeg`
- Windows: `winget install ffmpeg` (or `winget install -e --id Gyan.FFmpeg`)
- Linux (Debian/Ubuntu): `sudo apt-get install -y ffmpeg`

### Playlists

Playlist URLs work.  
Use **Playlist items** for ranges like `1-5,7,10-`, or leave it blank for the full playlist.

### Building with PyInstaller

This repo includes `yt-dlp-gui.spec`.

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller yt-dlp-gui.spec
```

Output: `dist/yt-dlp-gui.app`

Windows:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller yt-dlp-gui.spec
```

Output: `dist\yt-dlp-gui\yt-dlp-gui.exe`

### Support / Maintenance

This project is built and maintained in my spare time.

I might fix bugs or ship updates when I can, but there is no guaranteed timeline.
I can't promise support, compatibility fixes, or long-term maintenance.

If you open an issue or PR, I'll take a look when I have time.

### Legal / Usage

Only download content you are authorized to download.
Platform terms can still restrict downloads even if the tool supports them.
By using this app, you are responsible for complying with local law and platform terms.

See `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md`.
