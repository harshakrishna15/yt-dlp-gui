import os
import shutil
import sys
from pathlib import Path
from typing import Tuple


def _tool_filename(tool: str) -> str:
    if os.name == "nt":
        return f"{tool}.exe"
    return tool


def _is_executable(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if os.name == "nt":
        return True
    return os.access(path, os.X_OK)


def _bundled_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir / "tools")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass) / "tools")
    else:
        project_root = Path(__file__).resolve().parent.parent
        roots.append(project_root / "bundled_tools")
    return roots


def resolve_binary(tool: str) -> Tuple[Path | None, str]:
    """
    Resolve tool binary path.
    Returns (path, source) where source is one of: bundled, system, missing.
    """
    filename = _tool_filename(tool)

    for root in _bundled_roots():
        candidate = root / filename
        if _is_executable(candidate):
            return candidate, "bundled"

    system_path = shutil.which(tool)
    if system_path:
        return Path(system_path), "system"
    return None, "missing"
