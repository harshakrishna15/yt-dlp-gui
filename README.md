## yt-dlp GUI

A clean Tkinter desktop wrapper for `yt-dlp` that handles downloads without a command line.

### Requirements

- Python 3.10+ with Tk support (python.org builds include Tk)
- `yt-dlp` (installed via `requirements.txt`)
- FFmpeg (recommended; required for some merges/conversions)

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
python -m gui
```

Paste a URL, choose container/codec, select a format, and pick an output folder. Keep the window open until downloads finish; progress and errors appear in the UI.

### Playlists

Enable **Download playlist** to grab all items from a playlist URL. To download only part of a playlist, enter item ranges in **Playlist items** (e.g., `1-5,7,10-`). Leave it blank to download the full playlist.

### FFmpeg

`yt-dlp` can download many formats without FFmpeg, but FFmpeg is needed for common operations:

- Merging separate video and audio streams
- Re-encoding WebM → MP4 when “Convert to MP4” is enabled
- Some container conversions and post-processing steps

Install FFmpeg and ensure it’s on your `PATH`:

- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg` (or install the official build and add `ffmpeg.exe` to `PATH`)
- Linux (Debian/Ubuntu): `sudo apt-get install -y ffmpeg`

Note: FFmpeg is a system binary, so it is not listed in `requirements.txt`.

### Convenience scripts

- macOS: `scripts/setup_mac.sh`
- Windows: `scripts/setup_windows.bat`
- Linux: create a venv, install Tk, then install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
sudo apt-get install -y python3-tk
pip install -r requirements.txt
python run_gui.py
```

The scripts set up a venv and install dependencies. If your Python build lacks Tk, install a Tk-enabled build first. If you upgrade Python later, recreate the venv (or run `python3 -m venv --upgrade .venv`) so it tracks your current interpreter.

### Running without activating the venv

`run_gui.py` prefers the local `.venv` interpreter if present:

```bash
python run_gui.py
```

### Fonts

The app ships with IBM Plex Mono in `font/` and registers it at runtime so the UI looks consistent even when the font isn’t installed system-wide.

- Enforce IBM Plex Mono: `YTDLP_GUI_REQUIRE_PLEX_MONO=1`
- Warn if missing: `YTDLP_GUI_WARN_MISSING_FONT=1`
- Override family: `YTDLP_GUI_FONT_FAMILY="Menlo"`
