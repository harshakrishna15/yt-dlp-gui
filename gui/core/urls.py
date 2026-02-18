from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse


def strip_url_whitespace(url: str) -> str:
    return re.sub(r"\s+", "", url or "")


def is_mixed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
    except Exception:
        return False
    return bool(query.get("v")) and bool(query.get("list"))


def is_playlist_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
    except Exception:
        return False
    if parsed.path.startswith("/playlist") and query.get("list"):
        return True
    if query.get("list") and not query.get("v"):
        return True
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
        return parsed._replace(path="/playlist", query=f"list={list_id}").geturl()
    except Exception:
        return url

