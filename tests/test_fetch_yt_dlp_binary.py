from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gui.common import yt_dlp_release
from scripts import fetch_yt_dlp_binary


class TestFetchYtDlpBinary(unittest.TestCase):
    def test_parse_checksums_accepts_text_and_binary_markers(self) -> None:
        first = "a" * 64
        second = "b" * 64
        parsed = fetch_yt_dlp_binary.parse_checksums(
            f"{first}  yt-dlp_macos\n{second} *yt-dlp.exe\ninvalid\n"
        )
        self.assertEqual(parsed["yt-dlp_macos"], first)
        self.assertEqual(parsed["yt-dlp.exe"], second)

    def test_fetch_latest_binary_verifies_checksum_and_writes_license(self) -> None:
        binary_payload = b"official executable"
        digest = hashlib.sha256(binary_payload).hexdigest()
        license_payload = b"third-party notices"
        release = yt_dlp_release.YtDlpReleaseAsset(
            filename="yt-dlp_macos",
            payload=binary_payload,
            sha256=digest,
        )

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "yt-dlp"
            license_output = Path(tmp) / "THIRD_PARTY_LICENSES.txt"
            with patch.object(
                fetch_yt_dlp_binary.yt_dlp_release,
                "fetch_latest_release_asset",
                return_value=release,
            ) as fetch_release:
                with patch.object(
                    fetch_yt_dlp_binary.yt_dlp_release,
                    "fetch_third_party_licenses",
                    return_value=license_payload,
                ) as fetch_licenses:
                    with patch.object(
                        fetch_yt_dlp_binary,
                        "_binary_version",
                        return_value="2026.08.19",
                    ):
                        version = fetch_yt_dlp_binary.fetch_latest_binary(
                            platform="macos",
                            output=output,
                            license_output=license_output,
                        )

            self.assertEqual(version, "2026.08.19")
            self.assertEqual(output.read_bytes(), binary_payload)
            self.assertEqual(license_output.read_bytes(), license_payload)
            self.assertEqual(
                (output.parent / "VERSION").read_text(encoding="utf-8"),
                "2026.08.19\n",
            )
        fetch_release.assert_called_once_with(platform="macos")
        fetch_licenses.assert_called_once_with("2026.08.19")

    def test_fetch_latest_binary_rejects_checksum_mismatch(self) -> None:
        checksum_payload = f"{'0' * 64}  yt-dlp.exe\n".encode()
        with patch.object(
            yt_dlp_release,
            "download_bytes",
            side_effect=(checksum_payload, b"tampered"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                yt_dlp_release.fetch_latest_release_asset(platform="windows")


if __name__ == "__main__":
    unittest.main()
