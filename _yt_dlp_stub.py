import sys
import types


def ensure_yt_dlp_stub() -> None:
    if "yt_dlp" in sys.modules:
        return

    yt_dlp_stub = types.ModuleType("yt_dlp")
    yt_dlp_utils_stub = types.ModuleType("yt_dlp.utils")

    class _DownloadCancelled(Exception):
        pass

    class _YoutubeDL:
        def __init__(self, _opts: dict | None = None) -> None:
            self.opts = _opts or {}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, _urls: list[str]) -> None:
            return None

        def extract_info(self, _url: str, download: bool, process: bool) -> dict:
            return {}

    yt_dlp_utils_stub.DownloadCancelled = _DownloadCancelled
    yt_dlp_stub.YoutubeDL = _YoutubeDL
    yt_dlp_stub.utils = yt_dlp_utils_stub
    yt_dlp_stub.version = types.SimpleNamespace(__version__="stub")
    sys.modules["yt_dlp"] = yt_dlp_stub
    sys.modules["yt_dlp.utils"] = yt_dlp_utils_stub
