## yt-dlp GUI

A small Tkinter wrapper that uses the bundled `yt-dlp` checkout to download videos without the command line.

### Run it

1. From the repository root, ensure Python 3 with Tkinter is available.
2. Launch the GUI:

```bash
python gui/app.py
```

Paste a video URL, pick an output folder (defaults to `./downloads`), optionally tweak the format string, and click **Start download**. Progress and errors will appear in the log panel. Keep the window open until downloads finish.
