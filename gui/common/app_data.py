"""Remove only explicitly owned support paths, never download destinations."""

from __future__ import annotations

import shutil
import re
from dataclasses import dataclass
from pathlib import Path

from . import settings_store, yt_dlp_binary


@dataclass(frozen=True)
class CleanupResult:
    errors: tuple[str, ...] = ()


def cleanup_paths() -> tuple[Path, ...]:
    directory = yt_dlp_binary.managed_binary_dir()
    paths = [settings_store.user_settings_path()]
    # Do not recursively remove the configurable data root or an arbitrary bin.
    paths.extend(directory / name for name in (
        "runtime", ".runtime.backup", "yt-dlp", "yt-dlp.exe",
        "VERSION", "THIRD_PARTY_LICENSES.txt", "yt-dlp.backup", "yt-dlp.exe.backup",
        "VERSION.backup", "THIRD_PARTY_LICENSES.txt.backup",
    ))
    if directory.is_dir() and not _redirected_parent(directory / "placeholder"):
        paths.extend(path for path in directory.iterdir()
                     if re.fullmatch(r"\.runtime-[a-z0-9_]{8}", path.name)
                     or re.fullmatch(r"\.(yt-dlp(?:\.exe)?|VERSION|THIRD_PARTY_LICENSES\.txt)\.\d+\.tmp", path.name))
    return tuple(paths)


def _redirected_parent(path: Path) -> bool:
    aliases = {Path("/tmp"): Path("/private/tmp"), Path("/var"): Path("/private/var")}
    return any(parent.is_symlink() and parent.resolve() != aliases.get(parent)
               for parent in path.parents if parent != Path.home())


def remove_app_data(paths: tuple[Path, ...]) -> CleanupResult:
    errors = []
    for path in paths:
        try:
            # A redirected parent could turn a support-file deletion into an
            # unrelated deletion. Leaf symlinks are unlinked, never followed.
            if _redirected_parent(path):
                raise OSError("Refusing to remove data through a symlinked parent")
            if path.is_symlink():
                path.unlink()
            elif path.is_dir():
                if path.name not in {"runtime", ".runtime.backup"} and not re.fullmatch(r"\.runtime-[a-z0-9_]{8}", path.name):
                    raise OSError("Expected a support file, found a directory")
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    # Only empty app-specific parents are removed; unrelated siblings stay put.
    settings_parent = settings_store.user_settings_path().parent
    binary_dir = yt_dlp_binary.managed_binary_dir()
    for path in (settings_parent, binary_dir, binary_dir.parent):
        if path.name not in {".yt-dlp-gui", "yt-dlp-gui", "bin"} or path.is_symlink() or _redirected_parent(path):
            continue
        try:
            path.rmdir()
        except OSError:
            pass
    yt_dlp_binary._reset_bootstrap_cache()
    return CleanupResult(tuple(errors))
