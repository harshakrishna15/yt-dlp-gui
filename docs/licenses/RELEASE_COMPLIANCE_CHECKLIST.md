## Release Compliance Checklist

Use this checklist when publishing binary releases.

1. Tag the exact source commit used for the build.
2. Keep `requirements.txt` pinned for that release.
3. Include these files with the release:
- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_NOTICES.md`
- `mutagen-GPL-2.0-or-later.txt`
4. Keep the generated yt-dlp `THIRD_PARTY_LICENSES.txt` beside the bundled
   standalone executable.
5. Make sure the release points to the exact source tag/commit.
6. Keep the "authorized content only" warning in docs/release notes.

This checklist is practical guidance, not legal advice.
