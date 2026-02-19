from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import parse_qs, urlparse, urlencode

from .types import DownloadOptions, HistoryItem, QueueItem


def sanitize_url_for_report(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        query = parse_qs(parsed.query)
        safe_query: dict[str, list[str]] = {}
        for key in ("v", "list"):
            if key in query:
                safe_query[key] = query[key]
        sanitized_query = urlencode(safe_query, doseq=True)
        return parsed._replace(query=sanitized_query, fragment="").geturl()
    except ValueError:
        return raw


def build_report_payload(
    *,
    generated_at: datetime,
    status: str,
    simple_state: str,
    url: str,
    mode: str,
    container: str,
    codec: str,
    format_label: str,
    queue_items: list[QueueItem],
    queue_active: bool,
    is_downloading: bool,
    preview_title: str,
    options: DownloadOptions,
    history_items: list[HistoryItem],
    logs_text: str,
) -> str:
    lines: list[str] = []
    lines.append(f"generated_at={generated_at.isoformat(timespec='seconds')}")
    lines.append(f"status={status}")
    lines.append(f"simple_state={simple_state}")
    lines.append(f"url={sanitize_url_for_report(url)}")
    lines.append(f"mode={mode}")
    lines.append(f"container={container}")
    lines.append(f"codec={codec}")
    lines.append(f"format={format_label}")
    lines.append(f"queue_items={len(queue_items)}")
    lines.append(f"queue_active={int(queue_active)}")
    lines.append(f"is_downloading={int(is_downloading)}")
    lines.append(f"preview_title={preview_title[:120] if preview_title else ''}")
    lines.append(f"network_timeout_s={options['network_timeout_s']}")
    lines.append(f"network_retries={options['network_retries']}")
    lines.append(f"retry_backoff_s={options['retry_backoff_s']}")
    lines.append(f"write_subtitles={int(bool(options['write_subtitles']))}")
    lines.append(f"embed_subtitles={int(bool(options['embed_subtitles']))}")
    lines.append(
        f"subtitle_languages={','.join(options['subtitle_languages']) if options['subtitle_languages'] else ''}"
    )
    lines.append(f"audio_language={options['audio_language']}")
    lines.append(f"custom_filename={options['custom_filename']}")
    lines.append("")
    lines.append("[queue]")
    for idx, item in enumerate(queue_items, start=1):
        settings = item.get("settings") or {}
        lines.append(
            json.dumps(
                {
                    "index": idx,
                    "url": sanitize_url_for_report(str(item.get("url", ""))),
                    "mode": settings.get("mode"),
                    "container": settings.get("format_filter"),
                    "codec": settings.get("codec_filter"),
                    "format": settings.get("format_label"),
                },
                ensure_ascii=True,
            )
        )
    lines.append("")
    lines.append("[history]")
    for item in history_items[:50]:
        lines.append(
            json.dumps(
                {
                    "timestamp": item.get("timestamp", ""),
                    "name": item.get("name", ""),
                    "path": item.get("path", ""),
                    "source_url": sanitize_url_for_report(item.get("source_url", "")),
                },
                ensure_ascii=True,
            )
        )
    lines.append("")
    lines.append("[logs]")
    lines.append(logs_text)
    return "\n".join(lines).strip() + "\n"
