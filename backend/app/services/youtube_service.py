"""YouTube ingestion.

Two pieces of data are fetched:
1. Lightweight metadata (title, channel/author) via YouTube's public oEmbed
   endpoint — no API key required.
2. The transcript via `youtube-transcript-api` (v1.x instance API). Transcript
   segments carry start-time offsets, which we keep so citations can deep-link
   to the exact moment in the video (?t=SECONDS).

Failure modes (no captions, private/unavailable video, region blocks) are
translated into a single clean domain error the API can surface to the user.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from app.utils.helpers import extract_youtube_id

logger = logging.getLogger(__name__)


class YouTubeError(Exception):
    """Any recoverable problem while processing a YouTube URL."""


def fetch_metadata(video_id: str) -> dict:
    """Fetch title/author via oEmbed. Best-effort: never fatal on its own."""
    url = (
        "https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NexusRAG/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "title": data.get("title", f"YouTube video {video_id}"),
            "channel": data.get("author_name", ""),
            "thumbnail": data.get("thumbnail_url", ""),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("event=yt_oembed_failed video=%s err=%s", video_id, exc)
        return {
            "title": f"YouTube video {video_id}",
            "channel": "",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> list[dict]:
    """Return transcript segments: [{'text','start','duration'}, ...].

    Uses the v1.x instance API: YouTubeTranscriptApi().fetch(...).
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    languages = languages or ["en", "en-US", "en-GB"]
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        return fetched.to_raw_data()
    except (TranscriptsDisabled, NoTranscriptFound):
        raise YouTubeError(
            "This video has no available transcript/captions to extract."
        )
    except VideoUnavailable:
        raise YouTubeError("This video is unavailable or private.")
    except Exception as exc:  # noqa: BLE001
        # Newer library versions raise several specific subclasses; treat any
        # remaining failure as an unavailable transcript rather than a 500.
        logger.warning("event=yt_transcript_failed video=%s err=%s", video_id, exc)
        raise YouTubeError(
            "Could not retrieve the transcript. The video may be private, "
            "region-locked, or have captions disabled."
        )


def process_youtube_url(url: str) -> tuple[str, list[dict], dict]:
    """Validate the URL and return (video_id, transcript_segments, metadata)."""
    video_id = extract_youtube_id(url)
    if not video_id:
        raise YouTubeError("That does not look like a valid YouTube URL.")

    metadata = fetch_metadata(video_id)
    segments = fetch_transcript(video_id)
    metadata["video_id"] = video_id
    metadata["url"] = f"https://www.youtube.com/watch?v={video_id}"
    duration = 0.0
    if segments:
        last = segments[-1]
        duration = float(last.get("start", 0)) + float(last.get("duration", 0))
    metadata["duration_seconds"] = round(duration, 1)
    return video_id, segments, metadata
