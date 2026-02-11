import shutil
from pathlib import Path
from typing import Tuple


def resolve_binary(tool: str) -> Tuple[Path | None, str]:
    """Resolve tool on system PATH. Source is one of: system, missing."""
    system_path = shutil.which(tool)
    if system_path:
        return Path(system_path), "system"
    return None, "missing"


def missing_required_binaries() -> list[str]:
    missing: list[str] = []
    for tool in ("ffmpeg", "ffprobe"):
        path, _source = resolve_binary(tool)
        if path is None:
            missing.append(tool)
    return missing
