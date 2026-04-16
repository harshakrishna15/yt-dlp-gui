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


def detect_gpu_preferences() -> tuple[str, ...]:
    """Return detected GPU vendors in auto-selection priority order."""
    if sys.platform == "darwin":
        return ("apple",)
    if sys.platform == "win32":
        return _prioritized_gpu_vendors(_windows_gpu_names())
    if sys.platform.startswith("linux"):
        vendors = _linux_gpu_vendors_from_sysfs()
        if vendors:
            return _prioritized_gpu_vendors(vendors)
        return _prioritized_gpu_vendors(_linux_gpu_names())
    return ()


def _prioritized_gpu_vendors(values: Iterable[str]) -> tuple[str, ...]:
    detected: set[str] = set()
    for value in values:
        vendor = _gpu_vendor_from_name(value)
        if vendor is not None:
            detected.add(vendor)
    priority = ("nvidia", "amd", "intel", "apple")
    return tuple(vendor for vendor in priority if vendor in detected)


def _gpu_vendor_from_name(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip().casefold())
    if not cleaned:
        return None
    if re.search(r"\b(nvidia|geforce|quadro|tesla|titan)\b", cleaned):
        return "nvidia"
    if re.search(r"\b(amd|advanced micro devices|radeon|firepro|instinct)\b", cleaned):
        return "amd"
    if re.search(r"\b(intel|iris|uhd graphics|hd graphics)\b", cleaned):
        return "intel"
    if re.search(r"\bapple\b", cleaned):
        return "apple"
    return None


def _windows_gpu_names() -> tuple[str, ...]:
    commands = (
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        ],
        ["wmic", "path", "win32_VideoController", "get", "name"],
    )
    for cmd in commands:
        names = _run_gpu_name_command(cmd)
        if names:
            return names
    return ()


def _run_gpu_name_command(cmd: list[str]) -> tuple[str, ...]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            creationflags=creationflags,
        )
    except OSError:
        return ()
    if result.returncode != 0:
        return ()
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.lower() == "name":
            continue
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return tuple(lines)


def _linux_gpu_vendors_from_sysfs() -> tuple[str, ...]:
    pci_vendor_map = {
        "0x10de": "nvidia",
        "0x1002": "amd",
        "0x1022": "amd",
        "0x8086": "intel",
    }
    detected: list[str] = []
    seen: set[str] = set()
    for vendor_path in sorted(Path("/sys/class/drm").glob("card*/device/vendor")):
        try:
            vendor_id = vendor_path.read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        vendor = pci_vendor_map.get(vendor_id)
        if vendor is None or vendor in seen:
            continue
        seen.add(vendor)
        detected.append(vendor)
    return tuple(detected)


def _linux_gpu_names() -> tuple[str, ...]:
    try:
        result = subprocess.run(
            ["lspci", "-nn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return ()
    if result.returncode != 0:
        return ()
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in result.stdout.splitlines():
        lowered = raw_line.casefold()
        if (
            "vga compatible controller" not in lowered
            and "3d controller" not in lowered
            and "display controller" not in lowered
        ):
            continue
        line = raw_line.split(":", 2)[-1].strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return tuple(lines)


def missing_required_binaries() -> list[str]:
    missing: list[str] = []
    for tool in ("ffmpeg", "ffprobe"):
        path, _source = resolve_binary(tool)
        if path is None:
            missing.append(tool)
    return missing
