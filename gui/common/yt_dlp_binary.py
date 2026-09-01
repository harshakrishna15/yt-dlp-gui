from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from . import yt_dlp_release


_BINARY_OVERRIDE_ENV = "YT_DLP_GUI_BINARY"
_DATA_DIR_OVERRIDE_ENV = "YT_DLP_GUI_DATA_DIR"
_BUNDLED_DIR_NAME = "yt_dlp_bin"
_LICENSE_FILENAME = "THIRD_PARTY_LICENSES.txt"
_VERSION_FILENAME = "VERSION"
_UPDATE_LOCK = threading.Lock()
_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAP_RESULT: "YtDlpBinary | None" = None
_BOOTSTRAP_COMPLETE = False


@dataclass(frozen=True)
class YtDlpBinary:
    path: Path
    source: str
    version: str


@dataclass(frozen=True)
class YtDlpUpdateResult:
    success: bool
    changed: bool
    version: str
    message: str


def executable_name(*, platform: str | None = None) -> str:
    target = str(platform or sys.platform)
    return "yt-dlp.exe" if target == "win32" else "yt-dlp"


def managed_binary_dir(*, platform: str | None = None) -> Path:
    override = os.environ.get(_DATA_DIR_OVERRIDE_ENV, "").strip()
    if override:
        return Path(override).expanduser() / "bin"

    target = str(platform or sys.platform)
    if target == "darwin":
        root = Path.home() / "Library" / "Application Support"
    elif target == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        root = (
            Path(local_app_data).expanduser()
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
        root = (
            Path(xdg_data_home).expanduser()
            if xdg_data_home
            else Path.home() / ".local" / "share"
        )
    return root / "yt-dlp-gui" / "bin"


def managed_binary_path(*, platform: str | None = None) -> Path:
    return managed_binary_dir(platform=platform) / executable_name(platform=platform)


def managed_license_path(*, platform: str | None = None) -> Path:
    return managed_binary_dir(platform=platform) / _LICENSE_FILENAME


def managed_version_path(*, platform: str | None = None) -> Path:
    return managed_binary_dir(platform=platform) / _VERSION_FILENAME


def bundled_binary_path() -> Path | None:
    name = executable_name()
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidate = Path(str(frozen_root)) / _BUNDLED_DIR_NAME / name
        if _is_executable(candidate):
            return candidate

    explicit = os.environ.get("YT_DLP_GUI_BUNDLED_BINARY", "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if _is_executable(candidate):
            return candidate
    return None


def bundled_license_path() -> Path | None:
    binary = bundled_binary_path()
    if binary is None:
        return None
    candidate = binary.parent / _LICENSE_FILENAME
    return candidate if candidate.is_file() else None


def bundled_version_path() -> Path | None:
    binary = bundled_binary_path()
    if binary is None:
        return None
    candidate = binary.parent / _VERSION_FILENAME
    return candidate if candidate.is_file() else None


def resolve_yt_dlp_binary(*, bootstrap: bool = True) -> YtDlpBinary | None:
    override = os.environ.get(_BINARY_OVERRIDE_ENV, "").strip()
    if override:
        candidate = Path(override).expanduser()
        if _is_executable(candidate):
            return _describe_binary(candidate, "override")

    if bootstrap:
        bootstrapped = _bootstrap_managed_binary()
        if bootstrapped is not None:
            return bootstrapped
    else:
        managed = managed_binary_path()
        if _is_executable(managed):
            return _describe_binary(managed, "managed")

    seed = bundled_binary_path()
    if seed is not None:
        return _describe_binary(seed, "bundled")

    beside_python = Path(sys.executable).resolve().parent / executable_name()
    if _is_executable(beside_python):
        return _describe_binary(beside_python, "environment")

    system = shutil.which("yt-dlp")
    if system:
        candidate = Path(system)
        if _is_executable(candidate):
            return _describe_binary(candidate, "system")
    return None


def current_yt_dlp_version() -> str:
    resolved = resolve_yt_dlp_binary()
    return resolved.version if resolved is not None else "unavailable"


def update_managed_yt_dlp() -> YtDlpUpdateResult:
    with _UPDATE_LOCK:
        resolved = resolve_yt_dlp_binary()
        if resolved is None:
            return YtDlpUpdateResult(
                success=False,
                changed=False,
                version="unavailable",
                message="No yt-dlp executable is available.",
            )
        if resolved.source != "managed":
            return YtDlpUpdateResult(
                success=False,
                changed=False,
                version=resolved.version,
                message=(
                    "The managed yt-dlp executable is unavailable. "
                    "Install a packaged build before using the in-app updater."
                ),
            )

        path = resolved.path
        license_path = path.parent / _LICENSE_FILENAME
        version_path = path.parent / _VERSION_FILENAME
        staged_binary = _staged_binary_path(path)
        staged_license = license_path.with_name(
            f".{license_path.name}.{os.getpid()}.update"
        )
        staged_version = version_path.with_name(
            f".{version_path.name}.{os.getpid()}.update"
        )
        try:
            release = yt_dlp_release.fetch_latest_release_asset(
                platform=_release_platform()
            )
            _write_payload(staged_binary, release.payload, executable=True)
            new_version = _read_version(staged_binary)
            if not new_version:
                raise RuntimeError(
                    f"Downloaded {release.filename} did not report a version."
                )
            if _version_key(new_version) < _version_key(resolved.version):
                _remove_files(staged_binary)
                return YtDlpUpdateResult(
                    success=True,
                    changed=False,
                    version=resolved.version,
                    message=(
                        f"yt-dlp {resolved.version} is newer than the current "
                        f"stable release {new_version}."
                    ),
                )
            license_payload = yt_dlp_release.fetch_third_party_licenses(new_version)
            _write_payload(staged_license, license_payload, executable=False)
            _write_payload(
                staged_version,
                f"{new_version}\n".encode("utf-8"),
                executable=False,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            _remove_files(staged_binary, staged_license, staged_version)
            return YtDlpUpdateResult(
                success=False,
                changed=False,
                version=resolved.version,
                message=f"Could not download the yt-dlp update: {exc}",
            )

        backup = path.with_name(f"{path.name}.backup")
        license_backup = license_path.with_name(f"{license_path.name}.backup")
        version_backup = version_path.with_name(f"{version_path.name}.backup")
        had_license = license_path.is_file()
        had_version = version_path.is_file()
        try:
            _remove_files(backup, license_backup, version_backup)
            shutil.copy2(path, backup)
            _make_executable(backup)
            if had_license:
                shutil.copy2(license_path, license_backup)
            if had_version:
                shutil.copy2(version_path, version_backup)
        except OSError as exc:
            _remove_files(
                staged_binary,
                staged_license,
                staged_version,
                backup,
                license_backup,
                version_backup,
            )
            return YtDlpUpdateResult(
                success=False,
                changed=False,
                version=resolved.version,
                message=f"Could not prepare the yt-dlp update: {exc}",
            )

        try:
            os.replace(staged_binary, path)
            _make_executable(path)
            os.replace(staged_license, license_path)
            os.replace(staged_version, version_path)
        except OSError as exc:
            _restore_update_files(
                binary_path=path,
                binary_backup=backup,
                license_path=license_path,
                license_backup=license_backup,
                had_license=had_license,
                version_path=version_path,
                version_backup=version_backup,
                had_version=had_version,
            )
            _remove_files(staged_binary, staged_license, staged_version)
            return YtDlpUpdateResult(
                success=False,
                changed=False,
                version=resolved.version,
                message=f"Could not install the yt-dlp update: {exc}",
            )

        _remove_files(backup, license_backup, version_backup)
        changed = new_version != resolved.version
        message = (
            f"yt-dlp updated to {new_version}."
            if changed
            else f"yt-dlp {new_version} is already current."
        )
        _set_bootstrap_cache(
            YtDlpBinary(path=path, source="managed", version=new_version)
        )
        return YtDlpUpdateResult(
            success=True,
            changed=changed,
            version=new_version,
            message=message,
        )


def _bootstrap_managed_binary() -> YtDlpBinary | None:
    global _BOOTSTRAP_COMPLETE, _BOOTSTRAP_RESULT
    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_COMPLETE:
            return _BOOTSTRAP_RESULT

        managed = managed_binary_path()
        seed = bundled_binary_path()
        resolved_version = ""
        if seed is not None:
            managed_version = (
                _read_version_metadata(managed.parent / _VERSION_FILENAME)
                or _read_version(managed)
                if _is_executable(managed)
                else ""
            )
            seed_version_path = bundled_version_path()
            seed_version = (
                _read_version_metadata(seed_version_path)
                if seed_version_path is not None
                else ""
            ) or _read_version(seed)
            resolved_version = managed_version
            if not managed_version or _version_key(seed_version) > _version_key(
                managed_version
            ):
                try:
                    _copy_binary(seed, managed)
                except OSError:
                    pass
                else:
                    resolved_version = seed_version
                    seed_license = bundled_license_path()
                    if seed_license is not None:
                        try:
                            _copy_file(seed_license, managed.parent / _LICENSE_FILENAME)
                        except OSError:
                            pass
                    if seed_version:
                        try:
                            _write_payload(
                                managed.parent / _VERSION_FILENAME,
                                f"{seed_version}\n".encode("utf-8"),
                                executable=False,
                            )
                        except OSError:
                            pass
        elif _is_executable(managed):
            resolved_version = _read_version_metadata(
                managed.parent / _VERSION_FILENAME
            ) or _read_version(managed)

        _BOOTSTRAP_RESULT = (
            YtDlpBinary(
                path=managed,
                source="managed",
                version=resolved_version or "unknown",
            )
            if _is_executable(managed)
            else None
        )
        _BOOTSTRAP_COMPLETE = True
        return _BOOTSTRAP_RESULT


def _copy_binary(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(source, temporary)
        _make_executable(temporary)
        os.replace(temporary, destination)
        _make_executable(destination)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        _remove_files(temporary)


def _write_payload(destination: Path, payload: bytes, *, executable: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        handle.write(payload)
    if executable:
        _make_executable(destination)


def _restore_update_files(
    *,
    binary_path: Path,
    binary_backup: Path,
    license_path: Path,
    license_backup: Path,
    had_license: bool,
    version_path: Path,
    version_backup: Path,
    had_version: bool,
) -> None:
    try:
        if binary_backup.is_file():
            os.replace(binary_backup, binary_path)
            _make_executable(binary_path)
    except OSError:
        pass
    try:
        if had_license and license_backup.is_file():
            os.replace(license_backup, license_path)
        elif not had_license:
            license_path.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        if had_version and version_backup.is_file():
            os.replace(version_backup, version_path)
        elif not had_version:
            version_path.unlink(missing_ok=True)
    except OSError:
        pass
    _reset_bootstrap_cache()


def _remove_files(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _describe_binary(path: Path, source: str) -> YtDlpBinary:
    return YtDlpBinary(path=path, source=source, version=_read_version(path) or "unknown")


def _read_version(path: Path) -> str:
    if not _is_executable(path):
        return ""
    try:
        completed = subprocess.run(
            [str(path), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
            creationflags=_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return _last_output_line(completed.stdout)


def _read_version_metadata(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""
    return value if _version_key(value) else ""


def _last_output_line(*values: str) -> str:
    for value in values:
        lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return ""


def _version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", str(value or ""))
    return tuple(int(number) for number in numbers[:6])


def _staged_binary_path(path: Path) -> Path:
    return path.with_name(
        f".{path.stem}.{os.getpid()}.update{path.suffix}"
    )


def _release_platform() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def _is_executable(path: Path) -> bool:
    if not path.is_file():
        return False
    if sys.platform == "win32":
        return True
    return os.access(path, os.X_OK)


def _make_executable(path: Path) -> None:
    if sys.platform != "win32":
        path.chmod(path.stat().st_mode | 0o755)


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if sys.platform == "win32" else 0


def _reset_bootstrap_cache() -> None:
    global _BOOTSTRAP_COMPLETE, _BOOTSTRAP_RESULT
    with _BOOTSTRAP_LOCK:
        _BOOTSTRAP_COMPLETE = False
        _BOOTSTRAP_RESULT = None


def _set_bootstrap_cache(result: YtDlpBinary | None) -> None:
    global _BOOTSTRAP_COMPLETE, _BOOTSTRAP_RESULT
    with _BOOTSTRAP_LOCK:
        _BOOTSTRAP_COMPLETE = True
        _BOOTSTRAP_RESULT = result
