import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Tuple


def _is_executable(path: Path) -> bool:
    return path.exists() and path.is_file() and os.access(path, os.X_OK)


def resolve_binary(tool: str) -> Tuple[Path | None, str]:
    """Resolve tool on system PATH. Source is one of: system, missing."""
    system_path = shutil.which(tool)
    if system_path:
        return Path(system_path), "system"

    # macOS app launches (e.g. Finder) may not inherit Homebrew PATH entries.
    if sys.platform == "darwin":
        for candidate in (
            Path("/opt/homebrew/bin") / tool,
            Path("/usr/local/bin") / tool,
        ):
            if _is_executable(candidate):
                return candidate, "system"
    return None, "missing"


def available_ffmpeg_encoders(
    ffmpeg_path: Path,
    *,
    candidates: Iterable[str],
) -> set[str]:
    cmd = [str(ffmpeg_path), "-hide_banner", "-encoders"]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    text = f"{result.stdout}\n{result.stderr}"
    found: set[str] = set()
    for codec in set(candidates):
        if re.search(rf"\b{re.escape(codec)}\b", text):
            found.add(codec)
    return found


def missing_required_binaries() -> list[str]:
    missing: list[str] = []
    for tool in ("ffmpeg", "ffprobe"):
        path, _source = resolve_binary(tool)
        if path is None:
            missing.append(tool)
    return missing
