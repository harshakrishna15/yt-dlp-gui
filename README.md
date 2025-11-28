## yt-dlp GUI

A small Tkinter GUI for yt-dlp. It installs yt-dlp from PyPI (`yt-dlp[default]`) and lets you download without the command line.

### Run it

1. From the repository root, ensure you have a Python build with Tk installed (python.org installers include Tk; Homebrew users can `brew install python-tk@3.12`).
2. Create/activate a venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Launch the GUI:

```bash
python gui/app.py
```

Use the UI to paste a URL, select container/codec, pick a format, and choose an output folder. Progress and errors appear in the app. Keep the window open until downloads finish.

### Fonts

The UI uses IBM Plex Mono if installed; otherwise it will fall back to a system mono font. You do not need to install the font for the app to work.

### Quick setup scripts

Convenience scripts are provided:

- macOS: `scripts/setup_mac.sh`
- Windows: `scripts/setup_windows.bat`

They create a venv and install requirements. You may still need to install a Tk-enabled Python if your current one lacks Tk.
