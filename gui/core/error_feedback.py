from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureFeedback:
    status: str
    message: str
    reason: str


def error_text_from_log(line: str) -> str | None:
    clean = str(line or "").strip()
    if not clean:
        return None
    lower = clean.lower()
    if clean.startswith("[error]"):
        return clean[len("[error]") :].strip()
    if lower.startswith("[queue] failed:"):
        return clean.split(":", 1)[1].strip() if ":" in clean else clean
    return None


def _classify_reason(error_text: str) -> str:
    text = str(error_text or "").strip().lower()
    if not text:
        return "unknown"

    if "ffmpeg" in text or "ffprobe" in text:
        if "not found" in text or "missing" in text:
            return "missing_ffmpeg"

    if (
        "sign in to confirm you're not a bot" in text
        or "login required" in text
        or "members-only" in text
        or "membership required" in text
    ):
        return "login_required"

    if "private video" in text or "this video is private" in text:
        return "private_video"

    if (
        "not available in your country" in text
        or "geo-restricted" in text
        or "geo restricted" in text
    ):
        return "geo_restricted"

    if "requested format is not available" in text or "no video formats found" in text:
        return "format_unavailable"

    if "unsupported url" in text or "no suitable extractor" in text:
        return "unsupported_url"

    if "http error 429" in text or "too many requests" in text:
        return "rate_limited"

    if (
        "http error 403" in text
        or "forbidden" in text
        or "http error 401" in text
        or "unauthorized" in text
    ):
        return "access_denied"

    if (
        "timed out" in text
        or "timeout" in text
        or "temporary failure in name resolution" in text
        or "name or service not known" in text
        or "nodename nor servname provided" in text
        or "connection reset" in text
        or "network is unreachable" in text
        or "failed to resolve" in text
    ):
        return "network"

    if "permission denied" in text or "read-only file system" in text:
        return "write_permission"

    if "no space left on device" in text:
        return "disk_full"

    if "video unavailable" in text or "has been removed" in text:
        return "unavailable"

    return "unknown"


def _reason_label(reason: str) -> str:
    labels = {
        "missing_ffmpeg": "ffmpeg/ffprobe not found",
        "login_required": "login required",
        "private_video": "private video",
        "geo_restricted": "region-restricted video",
        "format_unavailable": "selected format unavailable",
        "unsupported_url": "unsupported URL",
        "rate_limited": "rate limited",
        "access_denied": "access denied",
        "network": "network issue",
        "write_permission": "no write permission",
        "disk_full": "disk is full",
        "unavailable": "video unavailable",
        "unknown": "unknown error",
    }
    return labels.get(reason, "unknown error")


def download_failed_feedback(error_text: str) -> FailureFeedback:
    reason = _classify_reason(error_text)
    reason_label = _reason_label(reason)
    status = f"Download failed: {reason_label}"
    message_by_reason = {
        "missing_ffmpeg": "ffmpeg/ffprobe is required for some downloads. Install ffmpeg, restart the app, and retry.",
        "login_required": "This video needs sign-in or membership access. Try another URL or use content you can access publicly.",
        "private_video": "This video is private. Confirm you have access or try a different URL.",
        "geo_restricted": "This video is blocked in your region. Try a different video.",
        "format_unavailable": "The selected format is unavailable. Reload formats and choose another option.",
        "unsupported_url": "This URL is not supported by yt-dlp. Check the link and try again.",
        "rate_limited": "The site is rate limiting requests. Wait a bit, then retry.",
        "access_denied": "Access was denied by the source site. Check the URL and permissions, then retry.",
        "network": "Network request failed. Check your connection and retry.",
        "write_permission": "Cannot write to the output folder. Choose a writable folder and retry.",
        "disk_full": "Your disk is full. Free up space and retry.",
        "unavailable": "This video is unavailable or removed. Try a different URL.",
        "unknown": "Download failed. Open Logs for details and retry.",
    }
    return FailureFeedback(
        status=status,
        message=message_by_reason.get(reason, message_by_reason["unknown"]),
        reason=reason_label,
    )


def formats_fetch_failed_feedback(error_text: str) -> FailureFeedback:
    reason = _classify_reason(error_text)
    reason_label = _reason_label(reason)
    status = f"Could not fetch formats: {reason_label}"
    message_by_reason = {
        "network": "Could not load formats due to a network issue. Check your connection and retry.",
        "rate_limited": "Format fetch is rate limited right now. Wait a bit, then retry.",
        "access_denied": "Access was denied while loading formats. Check the URL and try again.",
        "unsupported_url": "This URL is not supported by yt-dlp. Paste a supported video URL.",
        "private_video": "This video is private. Use a URL you can access.",
        "login_required": "This video needs sign-in access. Try a public URL.",
        "unavailable": "This video is unavailable or removed. Try a different URL.",
        "unknown": "Could not load formats. Check the URL or network and try again.",
    }
    return FailureFeedback(
        status=status,
        message=message_by_reason.get(reason, message_by_reason["unknown"]),
        reason=reason_label,
    )
