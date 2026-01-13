## yt-dlp GUI

A lightweight Tkinter interface for `yt-dlp` that handles installs and downloads for you without a command line.

### Requirements

- Python 3.10+ with Tk support (python.org builds include Tk)
- `yt-dlp` (installed via `requirements.txt`)
- FFmpeg (recommended; required for some merges/conversions)

### Quick start

1. Install Python with Tk support

   - python.org builds include Tk.
   - Homebrew users: `brew install python-tk@3.12`.

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Launch the app:

```bash
python -m gui
```

Paste a video URL, choose container/codec, select a format, and pick an output folder. Keep the window open until downloads finish; progress and errors are shown in the UI.

### FFmpeg

`yt-dlp` can download many formats without FFmpeg, but FFmpeg is needed for some common operations:

- Merging separate video+audio streams into a single file
- Re-encoding WebM → MP4 when “Convert to MP4” is enabled
- Some container conversions and post-processing steps

Install FFmpeg and ensure it’s on your `PATH`:

- macOS: `brew install ffmpeg`
- Windows: install FFmpeg and add `ffmpeg.exe` to `PATH`

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

The scripts set up a venv and install dependencies. If your Python build lacks Tk, install a Tk-enabled build first.

### Running without activating the venv

`run_gui.py` prefers the local `.venv` interpreter if present:

```bash
python run_gui.py
```

### Fonts

The app ships with IBM Plex Mono in `font/` and will try to register it at runtime so the UI looks consistent even on systems where it isn’t installed.

- Enforce IBM Plex Mono: run with `YTDLP_GUI_REQUIRE_PLEX_MONO=1` (the app will exit with an error if Tk can’t find the font).
- Show a warning when missing: run with `YTDLP_GUI_WARN_MISSING_FONT=1`.
- Override the family entirely: `YTDLP_GUI_FONT_FAMILY="Menlo"` (or any font family visible to Tk).
