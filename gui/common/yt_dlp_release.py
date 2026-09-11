from __future__ import annotations

import hashlib
import io
import ssl
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


LATEST_RELEASE_BASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download"
RAW_RELEASE_BASE = "https://raw.githubusercontent.com/yt-dlp/yt-dlp"
CHECKSUM_ASSET = "SHA2-256SUMS"
LICENSE_ASSET = "THIRD_PARTY_LICENSES.txt"
ASSETS = {
    "linux": "yt-dlp",
    "macos": "yt-dlp_macos",
    "windows": "yt-dlp.exe",
}


@dataclass(frozen=True)
class YtDlpReleaseAsset:
    filename: str
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class YtDlpUpdateProgress:
    stage: Literal["checking", "downloading", "verifying", "licenses", "installing"]
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    elapsed_seconds: float = 0.0

    @property
    def bytes_per_second(self) -> float | None:
        if self.elapsed_seconds < 1 or self.downloaded_bytes <= 0:
            return None
        return self.downloaded_bytes / self.elapsed_seconds

    @property
    def eta_seconds(self) -> float | None:
        speed = self.bytes_per_second
        if not speed or not self.total_bytes or self.downloaded_bytes >= self.total_bytes:
            return None
        return (self.total_bytes - self.downloaded_bytes) / speed


ProgressCallback = Callable[[YtDlpUpdateProgress], None]


def fetch_latest_release_asset(
    *, platform: str, on_progress: ProgressCallback | None = None
) -> YtDlpReleaseAsset:
    try:
        filename = ASSETS[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported yt-dlp release platform: {platform}") from exc

    if on_progress:
        on_progress(YtDlpUpdateProgress("checking"))
    checksum_payload = download_bytes(f"{LATEST_RELEASE_BASE}/{CHECKSUM_ASSET}")
    checksums = parse_checksums(checksum_payload.decode("utf-8", errors="replace"))
    expected = checksums.get(filename)
    if not expected:
        raise RuntimeError(f"No checksum was published for {filename}.")

    payload = download_bytes(f"{LATEST_RELEASE_BASE}/{filename}", on_progress=on_progress)
    if on_progress:
        on_progress(YtDlpUpdateProgress("verifying"))
    actual = sha256_bytes(payload)
    if actual != expected:
        raise RuntimeError(
            f"Checksum mismatch for {filename}: expected {expected}, got {actual}."
        )
    return YtDlpReleaseAsset(
        filename=filename,
        payload=payload,
        sha256=actual,
    )


def fetch_third_party_licenses(version: str) -> bytes:
    clean_version = str(version or "").strip()
    if not clean_version:
        raise ValueError("A yt-dlp version is required for license retrieval.")
    return download_bytes(
        f"{RAW_RELEASE_BASE}/{clean_version}/{LICENSE_ASSET}"
    )


def parse_checksums(payload: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for raw_line in str(payload or "").splitlines():
        parts = raw_line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, filename = parts
        filename = filename.lstrip("*").strip()
        if len(digest) == 64 and filename:
            checksums[filename] = digest.lower()
    return checksums


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def download_bytes(url: str, *, on_progress: ProgressCallback | None = None) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "yt-dlp-gui/1.0"},
    )
    if on_progress:
        on_progress(YtDlpUpdateProgress("downloading"))
    with urllib.request.urlopen(
        request,
        timeout=120,
        context=_tls_context(),
    ) as response:
        try:
            length = int(response.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            length = 0
        total = length if length > 0 else None
        received = 0
        started = time.monotonic()
        last_report = started
        if on_progress:
            on_progress(YtDlpUpdateProgress("downloading", total_bytes=total))
        with io.BytesIO() as payload:
            while chunk := response.read(256 * 1024):
                payload.write(chunk)
                received += len(chunk)
                now = time.monotonic()
                # Bound queued UI updates even on very fast connections.
                if on_progress and now - last_report >= 0.1:
                    on_progress(YtDlpUpdateProgress("downloading", received, total, now - started))
                    last_report = now
            if total is not None and received != total:
                raise RuntimeError(f"Incomplete download: received {received} of {total} bytes.")
            if on_progress:
                on_progress(YtDlpUpdateProgress("downloading", received, total, time.monotonic() - started))
            return payload.getvalue()


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
