from __future__ import annotations

import hashlib
import ssl
import urllib.request
from dataclasses import dataclass


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


def fetch_latest_release_asset(*, platform: str) -> YtDlpReleaseAsset:
    try:
        filename = ASSETS[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported yt-dlp release platform: {platform}") from exc

    checksum_payload = download_bytes(f"{LATEST_RELEASE_BASE}/{CHECKSUM_ASSET}")
    checksums = parse_checksums(checksum_payload.decode("utf-8", errors="replace"))
    expected = checksums.get(filename)
    if not expected:
        raise RuntimeError(f"No checksum was published for {filename}.")

    payload = download_bytes(f"{LATEST_RELEASE_BASE}/{filename}")
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


def download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "yt-dlp-gui/1.0"},
    )
    with urllib.request.urlopen(
        request,
        timeout=120,
        context=_tls_context(),
    ) as response:
        return response.read()


def _tls_context() -> ssl.SSLContext:
    try:
        import certifi
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
