#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from gui.app_meta import APP_DESCRIPTION, APP_DISPLAY_NAME, APP_REPO_NAME, APP_VERSION


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in str(version).split(".") if part.strip()]
    ints = [int(part) for part in parts[:4]]
    while len(ints) < 4:
        ints.append(0)
    return tuple(ints[:4])


def build_version_info() -> str:
    version = _version_tuple(APP_VERSION)
    version_text = ".".join(str(part) for part in version)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version},
    prodvers={version},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{APP_REPO_NAME}'),
          StringStruct('FileDescription', '{APP_DESCRIPTION}'),
          StringStruct('FileVersion', '{version_text}'),
          StringStruct('InternalName', '{APP_REPO_NAME}'),
          StringStruct('OriginalFilename', '{APP_REPO_NAME}.exe'),
          StringStruct('ProductName', '{APP_DISPLAY_NAME}'),
          StringStruct('ProductVersion', '{version_text}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a PyInstaller version-info file for Windows packaging."
    )
    parser.add_argument(
        "--output",
        default="build/pyinstaller-version-info.txt",
        help="Output path for the generated version-info text",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_version_info(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
