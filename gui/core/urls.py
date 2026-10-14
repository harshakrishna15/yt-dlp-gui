from __future__ import annotations

import re
from urllib.parse import ParseResult, parse_qs, urlencode, urlparse


def strip_url_whitespace(url: str) -> str:
    return re.sub(r"\s+", "", url or "")


def _has_video(parsed: ParseResult, query: dict[str, list[str]]) -> bool:
    if query.get("v"):
        return True
    host = (parsed.hostname or "").lower()
    parts = parsed.path.strip("/").split("/")
    if host in {"youtu.be", "www.youtu.be"}:
        return len(parts) == 1 and bool(parts[0])
    youtube_host = host == "youtube.com" or host.endswith(".youtube.com")
    return bool(
        youtube_host and len(parts) >= 2
        and parts[0] in {"shorts", "live", "embed"} and parts[1]
    )


def is_mixed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        return _has_video(parsed, query) and bool(query.get("list"))
    except Exception:
        return False


def is_playlist_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        return bool(query.get("list")) and not _has_video(parsed, query)
    except Exception:
        return False


def strip_list_param(url: str) -> str:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        for param in ("list", "index", "start"):
            query.pop(param, None)
        new_query = urlencode(query, doseq=True)
        return parsed._replace(query=new_query).geturl()
    except Exception:
        return url


def to_playlist_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        list_id = (query.get("list") or [None])[0]
        if not list_id:
            return url
        host = (parsed.hostname or "").lower()
        netloc = (
            "www.youtube.com" if host in {"youtu.be", "www.youtu.be"}
            else parsed.netloc
        )
        return parsed._replace(
            netloc=netloc, path="/playlist",
            query=urlencode({"list": list_id}), fragment="",
        ).geturl()
    except Exception:
        return url

