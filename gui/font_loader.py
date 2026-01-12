from __future__ import annotations

import ctypes
import ctypes.util
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

import tkinter as tk
from tkinter import font as tkfont


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _bundled_font_dir() -> Path:
    repo_root = _repo_root()
    candidates = [repo_root / "font", repo_root / "IBM_Plex_Mono"]
    return next((p for p in candidates if p.exists()), candidates[0])


def _ttf_files(font_dir: Path) -> list[Path]:
    return sorted(p for p in font_dir.glob("*.ttf") if p.is_file())


def _is_family_available(root: tk.Tk, family: str) -> bool:
    try:
        return family in set(tkfont.families(root))
    except tk.TclError:
        return False


def ensure_ibm_plex_mono(root: tk.Tk) -> bool:
    """
    Best-effort runtime registration of bundled IBM Plex Mono fonts.

    Returns True if the family appears available to Tk after this call.
    """
    family = "IBM Plex Mono"
    if _is_family_available(root, family):
        return True

    font_dir = _bundled_font_dir()
    if not font_dir.exists():
        return False
    ttf_files = _ttf_files(font_dir)
    if not ttf_files:
        return False

    system = platform.system()
    if system == "Windows":
        _register_windows_fonts(ttf_files)
    elif system == "Darwin":
        _register_macos_fonts(ttf_files)
    else:
        if not _register_linux_fontconfig_dir(font_dir):
            _install_linux_user_fonts(font_dir)

    root.update_idletasks()
    return _is_family_available(root, family)


def ensure_bundled_fonts(root: tk.Tk, font_dir: Path | None = None) -> None:
    """Best-effort runtime registration of all bundled fonts in `font/`."""
    font_dir = font_dir or _bundled_font_dir()
    if not font_dir.exists():
        return
    ttf_files = _ttf_files(font_dir)
    if not ttf_files:
        return

    system = platform.system()
    if system == "Windows":
        _register_windows_fonts(ttf_files)
    elif system == "Darwin":
        _register_macos_fonts(ttf_files)
    else:
        if not _register_linux_fontconfig_dir(font_dir):
            _install_linux_user_fonts(font_dir)

    try:
        root.update_idletasks()
    except Exception:
        pass


def _register_windows_fonts(ttf_files: Iterable[Path]) -> None:
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    add_font_resource_ex = gdi32.AddFontResourceExW
    add_font_resource_ex.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    add_font_resource_ex.restype = ctypes.c_int
    fr_private = 0x10

    for path in ttf_files:
        try:
            add_font_resource_ex(str(path), fr_private, None)
        except Exception:
            continue


def _register_macos_fonts(ttf_files: Iterable[Path]) -> None:
    coretext_path = ctypes.util.find_library("CoreText")
    corefoundation_path = ctypes.util.find_library("CoreFoundation")
    if not coretext_path or not corefoundation_path:
        return

    coretext = ctypes.CDLL(coretext_path)
    corefoundation = ctypes.CDLL(corefoundation_path)

    cfurl_create = corefoundation.CFURLCreateFromFileSystemRepresentation
    cfurl_create.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
    cfurl_create.restype = ctypes.c_void_p

    cfrelease = corefoundation.CFRelease
    cfrelease.argtypes = [ctypes.c_void_p]
    cfrelease.restype = None

    register_fonts = coretext.CTFontManagerRegisterFontsForURL
    register_fonts.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    register_fonts.restype = ctypes.c_bool

    k_ct_font_manager_scope_process = 1

    for path in ttf_files:
        url = None
        try:
            path_bytes = str(path).encode("utf-8")
            url = cfurl_create(None, path_bytes, len(path_bytes), False)
            if not url:
                continue
            error = ctypes.c_void_p()
            register_fonts(url, k_ct_font_manager_scope_process, ctypes.byref(error))
        except Exception:
            continue
        finally:
            if url:
                try:
                    cfrelease(url)
                except Exception:
                    pass


def _register_linux_fontconfig_dir(font_dir: Path) -> bool:
    lib_path = ctypes.util.find_library("fontconfig")
    if not lib_path:
        return False

    try:
        lib = ctypes.CDLL(lib_path)
    except Exception:
        return False

    fc_init = getattr(lib, "FcInit", None)
    fc_init_load = getattr(lib, "FcInitLoadConfigAndFonts", None)
    fc_config_set_current = getattr(lib, "FcConfigSetCurrent", None)
    fc_config_app_font_add_dir = getattr(lib, "FcConfigAppFontAddDir", None)
    if not all((fc_init, fc_init_load, fc_config_set_current, fc_config_app_font_add_dir)):
        return False

    fc_init.restype = ctypes.c_int
    fc_init_load.restype = ctypes.c_void_p
    fc_config_set_current.argtypes = [ctypes.c_void_p]
    fc_config_set_current.restype = ctypes.c_int
    fc_config_app_font_add_dir.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fc_config_app_font_add_dir.restype = ctypes.c_int

    try:
        if not fc_init():
            return False
        config = fc_init_load()
        if not config:
            return False
        added = fc_config_app_font_add_dir(config, str(font_dir).encode("utf-8"))
        if not added:
            return False
        fc_config_set_current(config)
        return True
    except Exception:
        return False


def _install_linux_user_fonts(font_dir: Path) -> None:
    target_dir = Path.home() / ".local" / "share" / "fonts" / "yt-dlp-gui-fonts"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for ttf in _ttf_files(font_dir):
            shutil.copy2(ttf, target_dir / ttf.name)
    except Exception:
        return

    try:
        subprocess.run(["fc-cache", "-f"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
