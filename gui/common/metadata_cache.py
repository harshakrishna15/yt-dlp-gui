from __future__ import annotations

import json
import time
from collections import OrderedDict
from collections.abc import Callable


_FORMAT_FIELDS = frozenset({
    "format_id", "ext", "vcodec", "acodec", "width", "height", "fps",
    "format_note", "abr", "tbr", "filesize", "filesize_approx", "language",
    "custom_format", "is_audio_only",
})


class MetadataPreviewCache:
    """Bounded, session-only GUI previews, never reusable download URLs."""

    def __init__(
        self, *, ttl_seconds: float = 120, max_entries: int = 12,
        max_bytes: int = 4 * 1024 * 1024, clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, bytes]] = OrderedDict()

    def clear(self) -> None:
        self._entries.clear()

    def discard(self, url: str) -> None:
        self._entries.pop(url, None)

    def _prune(self) -> None:
        now = self._clock()
        for url, (expires, _data) in list(self._entries.items()):
            if now >= expires:
                del self._entries[url]

    def get(self, url: str) -> dict | None:
        self._prune()
        entry = self._entries.get(url)
        if entry is None:
            return None
        self._entries.move_to_end(url)
        return json.loads(entry[1])

    def put(self, url: str, payload: dict) -> bool:
        self.discard(url)
        if self._max_entries <= 0 or self._ttl <= 0:
            return False
        collections = payload.get("collections") or {}
        compact = {
            key: collections.get(key, [])
            for key in ("video_labels", "audio_labels", "audio_languages")
        }
        for key in ("video_lookup", "audio_lookup"):
            lookup = collections.get(key) or {}
            if len(lookup) > 1000:
                return False
            compact[key] = {
                label: {key: value for key, value in info.items() if key in _FORMAT_FIELDS}
                for label, info in lookup.items()
            }
        preview = {
            "collections": compact,
            "preview_title": payload.get("preview_title", ""),
            "source_summary": payload.get("source_summary"),
        }
        try:
            encoded = json.dumps(preview, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            return False
        if len(encoded) > self._max_bytes:
            return False
        self._prune()
        self._entries[url] = (self._clock() + self._ttl, encoded)
        while (len(self._entries) > self._max_entries
               or sum(len(data) for _, data in self._entries.values()) > self._max_bytes):
            self._entries.popitem(last=False)
        return True
