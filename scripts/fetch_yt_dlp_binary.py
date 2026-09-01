#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from gui.common import yt_dlp_release


ASSETS = {
    "macos": yt_dlp_release.ASSETS["macos"],
    "windows": yt_dlp_release.ASSETS["windows"],
}


parse_checksums = yt_dlp_release.parse_checksums
sha256_bytes = yt_dlp_release.sha256_bytes


def fetch_latest_binary(
    *,
    platform: str,
    output: Path,
    license_output: Path | None = None,
) -> str:
    release_asset = yt_dlp_release.fetch_latest_release_asset(platform=platform)
    _write_atomic(output, release_asset.payload, executable=True)
    version = _binary_version(output)
    if not version:
        raise RuntimeError(
            f"Downloaded {release_asset.filename} did not report a version."
        )
    _write_atomic(
        output.parent / "VERSION",
        f"{version}\n".encode("utf-8"),
        executable=False,
    )

    if license_output is not None:
        license_payload = yt_dlp_release.fetch_third_party_licenses(version)
        _write_atomic(license_output, license_payload, executable=False)
    return version


def _write_atomic(path: Path, payload: bytes, *, executable: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        if executable and sys.platform != "win32":
            temporary.chmod(0o755)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _binary_version(path: Path) -> str:
    creationflags = (
        int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if sys.platform == "win32"
        else 0
    )
    completed = subprocess.run(
        [str(path), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        return ""
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and verify the latest stable yt-dlp executable."
    )
    parser.add_argument("--platform", choices=tuple(ASSETS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--license-output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        version = fetch_latest_binary(
            platform=args.platform,
            output=args.output,
            license_output=args.license_output,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    print(f"[ok] bundled yt-dlp {version}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
