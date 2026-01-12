from __future__ import annotations

from dataclasses import dataclass, field

try:
    from .shared_types import FormatLookup, FormatsCacheEntry
except ImportError:  # Support running as a script (python gui/app.py)
    from shared_types import FormatLookup, FormatsCacheEntry  # type: ignore


@dataclass(slots=True)
class FormatState:
    is_fetching: bool = False
    last_fetched_url: str = ""
    fetch_after_id: str | None = None
    last_fetch_failed: bool = False
    last_codec_fallback_notice: tuple[str, str, str] | None = None

    # Raw formats split by type.
    video_labels: list[str] = field(default_factory=list)
    video_lookup: FormatLookup = field(default_factory=dict)
    audio_labels: list[str] = field(default_factory=list)
    audio_lookup: FormatLookup = field(default_factory=dict)

    # Filtered formats shown in the dropdown (depends on mode/container/codec).
    filtered_labels: list[str] = field(default_factory=list)
    filtered_lookup: FormatLookup = field(default_factory=dict)

    # Cache processed formats per URL to avoid repeated probes.
    cache: dict[str, FormatsCacheEntry] = field(default_factory=dict)

