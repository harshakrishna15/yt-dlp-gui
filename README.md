# yt-dlp-gui

A desktop app for downloading video and audio with yt-dlp, built with Python and Qt.

- Preview video details and available formats before downloading.
- Choose video or audio quality, with container, codec, and filename options under **Advanced**.
- Download immediately or build a queue, retry failed items, and reveal completed files.
- Update the bundled yt-dlp engine from **Preferences** in packaged apps.

## Getting started

You’ll need **Python 3.10+** and **FFmpeg** (`ffmpeg` and `ffprobe` available in `PATH`).
Run the commands below from the project root. The examples use the virtual environment
directly, so activation is optional.

### macOS

```bash
brew install ffmpeg
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
python3 run_gui.py
```

### Windows

```powershell
winget install ffmpeg
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py -3 run_gui.py
```

After setup, launch the app again with `python3 run_gui.py` on macOS or
`py -3 run_gui.py` on Windows. The launcher automatically uses the project’s `.venv`.

## Using the app

1. Paste a video or playlist URL and select **Analyze URL**.
2. Choose **video or audio**, quality, and a destination folder.
3. Select **Download** to start immediately, or **Add to Queue** to save it for later.
4. Open **Queue → Start queue** to download queued items.

Video defaults to MP4/H.264 and audio to M4A. Open **Advanced** to change the
container, codec, or filename. The destination resets to your Downloads folder
whenever the app starts.

**Download** always starts the current link. **Start queue** includes queued,
failed, and cancelled items, and skips completed items. **Retry failed** retries
only failures. Queue results are kept for the current session; clearing the queue
never deletes downloaded files.

Use **Show in Finder** on macOS or **Show in folder** on Windows to reveal a completed
download. In the queue, **F2** edits an item, **Delete** removes it, and **Return**
reveals a completed file.

Analysis can be cancelled. Recent format previews may be reused during the same
session; **Refresh formats** requests a fresh preview. Downloads always resolve
fresh media through yt-dlp.

## Building a standalone app

Build on the platform you want to run. The scripts install build dependencies and
download and verify the latest stable official yt-dlp release. FFmpeg must still
be installed on the computer running the app.

### macOS

```bash
bash scripts/build-macos.sh
open dist/yt-dlp-gui.app
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
.\dist\yt-dlp-gui\yt-dlp-gui.exe
```

Packaged apps keep an updateable engine in your application-data directory.
Use **Preferences → Update yt-dlp** to install later releases. On macOS, the engine
is installed once and reused; first-run validation can take several seconds.

## Preferences and app data

Settings are stored locally at `~/.yt-dlp-gui/settings.json` by default.

| Environment variable | Effect |
| --- | --- |
| `YT_DLP_GUI_SETTINGS_PATH` | Use a different settings file. |
| `YT_DLP_GUI_REDUCE_MOTION=1` | Disable navigation and Advanced animations at launch. |

Before uninstalling, use **Preferences → Remove app data and quit...** while the
app is idle. The confirmation lists the settings and managed engine files to be
removed. Downloaded media and unrelated files are preserved. Deleting the app
alone leaves these support files behind; reopening it recreates its engine.

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `ffmpeg` or `ffprobe` is missing | Install FFmpeg using the command for your platform above, then restart the terminal and app. |
| PySide6 is missing | Repeat the dependency-install command above using the project’s `.venv` interpreter. |
| Analysis or a download fails | Open **Preferences → View logs** for details. In a packaged app, try **Update yt-dlp** if a site has changed. |
| Windows blocks the build script | Use the PowerShell command in the build instructions. Its execution-policy bypass applies only to that command. |
| The packaged app won’t run | Confirm FFmpeg is installed and launch the output at `dist/yt-dlp-gui.app` on macOS or `dist\yt-dlp-gui\yt-dlp-gui.exe` on Windows. |

## Support

This is a hobby project, and support depends on available time. Bug reports are welcome.

## License and responsible use

Only download content you’re authorized to download, and follow applicable laws
and platform terms.

See the [license](docs/licenses/LICENSE), [notice](docs/licenses/NOTICE), and
[third-party notices](docs/licenses/THIRD_PARTY_NOTICES.md), including the
[Mutagen license](docs/licenses/mutagen-GPL-2.0-or-later.txt).
Release maintainers should also review the
[compliance checklist](docs/licenses/RELEASE_COMPLIANCE_CHECKLIST.md).
