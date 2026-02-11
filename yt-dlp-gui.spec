# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

project_root = Path.cwd()
binaries = []


def add_tool_if_present(relative_path: str, target_dir: str = "tools") -> None:
    src = project_root / relative_path
    if src.exists():
        binaries.append((str(src), target_dir))


if os.name == "nt":
    add_tool_if_present("bundled_tools/ffmpeg.exe")
    add_tool_if_present("bundled_tools/ffprobe.exe")
    add_tool_if_present("bundled_tools/yt-dlp.exe")
else:
    add_tool_if_present("bundled_tools/ffmpeg")
    add_tool_if_present("bundled_tools/ffprobe")
    add_tool_if_present("bundled_tools/yt-dlp")

a = Analysis(
    ['pyinstaller_entry.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=[('font', 'font')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='yt-dlp-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='yt-dlp-gui',
)
app = BUNDLE(
    coll,
    name='yt-dlp-gui.app',
    icon=None,
    bundle_identifier=None,
)
