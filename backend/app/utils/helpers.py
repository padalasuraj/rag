"""Small, dependency-light helpers used across services."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

# --------------------------------------------------------------------------- #
# YouTube
# --------------------------------------------------------------------------- #

_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


def extract_youtube_id(url: str) -> str | None:
    """Return the 11-char video id from any common YouTube URL form, else None."""
    url = (url or "").strip()
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except ValueError:
        return None

    host = (parsed.netloc or "").lower()
    if host not in _YT_HOSTS:
        # Also accept a bare 11-char id.
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
            return url
        return None

    if host in {"youtu.be", "www.youtu.be"}:
        vid = parsed.path.lstrip("/").split("/")[0]
        return vid if _valid_id(vid) else None

    # youtube.com/watch?v=..., /embed/..., /shorts/..., /live/...
    if parsed.path == "/watch":
        vid = parse_qs(parsed.query).get("v", [None])[0]
        return vid if vid and _valid_id(vid) else None

    for prefix in ("/embed/", "/shorts/", "/live/", "/v/"):
        if parsed.path.startswith(prefix):
            vid = parsed.path[len(prefix):].split("/")[0]
            return vid if _valid_id(vid) else None

    return None


def _valid_id(vid: str) -> bool:
    return bool(vid) and bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", vid))


def youtube_watch_url(video_id: str, start_seconds: float | None = None) -> str:
    base = f"https://www.youtube.com/watch?v={video_id}"
    if start_seconds is not None:
        base += f"&t={int(start_seconds)}"
    return base


def format_timestamp(seconds: float | None) -> str:
    """Seconds -> H:MM:SS or M:SS for display."""
    if seconds is None:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #

_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{2,}")


def clean_text(text: str) -> str:
    """Normalize whitespace and strip common extraction artifacts."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\ufeff", "")
    # Fix hyphenation at line breaks: "regres-\nsion" -> "regression".
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = [_WS.sub(" ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTI_NL.sub("\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — good enough for budgeting."""
    return max(1, len(text) // 4)
