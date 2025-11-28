## yt-dlp GUI

A lightweight Tkinter interface for `yt-dlp` that handles installs and downloads for you—no command line needed.

### Quick start

1) Install Python with Tk support  
   - python.org builds include Tk.  
   - Homebrew users: `brew install python-tk@3.12`.

2) Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3) Launch the app:

```bash
python gui/app.py
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

The UI prefers IBM Plex Mono when available and otherwise falls back to your system monospace font. The font is optional; the app works without it.
