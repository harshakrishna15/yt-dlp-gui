## yt-dlp-gui

A simple GUI for `yt-dlp`.
Paste a link, choose a format, and download.

This is a hobby project that I'm using myself.

### Requirements

- Python 3.10+ (with Tk)
- Python dependencies from `requirements.txt`
- `ffmpeg` and `ffprobe` on your `PATH`

Install FFmpeg first:

- macOS: `brew install ffmpeg`
- Windows: `winget install -e --id Gyan.FFmpeg`
- Linux (Debian/Ubuntu): `sudo apt-get install -y ffmpeg`

### Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run_gui.py
```

If Tk is missing on Homebrew Python, install matching `python-tk` (example: `brew install python-tk@3.11`).

### Build App

Use the scripts in `scripts/`.

- macOS:

```bash
chmod +x scripts/build-macos.sh
./scripts/build-macos.sh
```

Output: `dist/yt-dlp-gui.app`

- Windows:

```powershell
.\scripts\build-windows.ps1
```

Output: `dist\yt-dlp-gui\yt-dlp-gui.exe`

### Usage Notes

- Playlist URLs work.
- Use **Playlist items** for ranges like `1-5,7,10-`.
- Leave Playlist items blank to download the full playlist.

### Support Policy

This is maintained in my spare time.
I might fix things when I can, but there are no guarantees for support, updates, or compatibility fixes.
Issues and PRs are welcome, and I review them when I have time.

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
