## yt-dlp GUI

A lightweight Tkinter interface for `yt-dlp` that handles installs and downloads for you without a command line.

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

### Fonts

The app ships with IBM Plex Mono in `IBM_Plex_Mono/` and will try to register it at runtime so the UI looks consistent even on systems where it isn’t installed.

- Enforce IBM Plex Mono: run with `YTDLP_GUI_REQUIRE_PLEX_MONO=1` (the app will exit with an error if Tk can’t find the font).
- Show a warning when missing: run with `YTDLP_GUI_WARN_MISSING_FONT=1`.
- Override the family entirely: `YTDLP_GUI_FONT_FAMILY="Menlo"` (or any font family visible to Tk).

- Enforce IBM Plex Mono: run with `YTDLP_GUI_REQUIRE_PLEX_MONO=1` (the app will exit with an error if Tk can’t find the font).
- Show a one-time warning when missing: run with `YTDLP_GUI_WARN_MISSING_FONT=1`.
- Override the family entirely: `YTDLP_GUI_FONT_FAMILY="Menlo"` (or any font family visible to Tk).
