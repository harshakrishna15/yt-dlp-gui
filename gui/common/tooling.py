import shutil
import sys
from pathlib import Path
from typing import Tuple


def _is_executable(path: Path) -> bool:
    return path.exists() and path.is_file()


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


def missing_required_binaries() -> list[str]:
    missing: list[str] = []
    for tool in ("ffmpeg", "ffprobe"):
        path, _source = resolve_binary(tool)
        if path is None:
            missing.append(tool)
    return missing
