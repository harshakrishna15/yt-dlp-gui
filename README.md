## yt-dlp-gui

A front-end for `yt-dlp`. Paste a URL, pick a format, and download—no command line needed.

### Requirements

- Python 3.10+ with Tk support
- `yt-dlp` (installed via `requirements.txt`)
- FFmpeg (optional for local dev if you place binaries in `bundled_tools/`)

### Quick start

1. Install Python with Tk support.
   - python.org builds include Tk.
   - Homebrew users: install the `python-tk` formula matching your Python (example: `brew install python-tk@3.11`).

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Launch:

```bash
python3 run_gui.py
```

Paste a URL, choose container/codec, select a format, and pick an output folder. Keep the window open until downloads finish; progress and errors show in the UI.

### Playlists

Playlist URLs are supported. Use **Playlist items** to download a range (for example: `1-5,7,10-`). Leave it blank to download the whole playlist.

### Downloadable app builds

This repo includes a PyInstaller build config that produces:

- macOS: `yt-dlp-gui.app` (zipped for distribution)
- Windows: `yt-dlp-gui.exe` (zipped for distribution)

You can bundle binaries by placing them in `bundled_tools/` before building:

- macOS/Linux: `bundled_tools/ffmpeg`, `bundled_tools/ffprobe`, `bundled_tools/yt-dlp`
- Windows: `bundled_tools/ffmpeg.exe`, `bundled_tools/ffprobe.exe`, `bundled_tools/yt-dlp.exe`

At runtime, the app resolves tools in this order:
1. Bundled binaries (`tools/` inside the packaged app)
2. System `PATH`
3. For `yt-dlp`, the Python module fallback (`yt_dlp`)

#### Build locally (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller yt-dlp-gui.spec
```

Your app will be at `dist/yt-dlp-gui.app`.

#### Build locally (Windows)

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller yt-dlp-gui.spec
```

Your app will be at `dist\yt-dlp-gui\yt-dlp-gui.exe`.

#### GitHub Releases

Publishing a GitHub Release runs the CI workflow and uploads:

- `yt-dlp-gui-macos.zip`
- `yt-dlp-gui-windows.zip`

### FFmpeg

`yt-dlp` can download many formats without FFmpeg, but FFmpeg is needed for common operations:

- Merging separate video and audio streams
- Re-encoding WebM → MP4 when “Convert to MP4” is enabled
- Some container conversions and post-processing steps

Install FFmpeg and ensure it’s on your `PATH` if you are not bundling it:

- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg` (or install the official build and add `ffmpeg.exe` to `PATH`)
- Linux (Debian/Ubuntu): `sudo apt-get install -y ffmpeg`

Note: FFmpeg is a native binary, so it is not listed in `requirements.txt`.
