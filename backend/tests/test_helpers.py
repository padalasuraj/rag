from app.utils.helpers import (
    clean_text,
    extract_youtube_id,
    format_timestamp,
    youtube_watch_url,
)


def test_extract_youtube_id_variants():
    vid = "dQw4w9WgXcQ"
    assert extract_youtube_id(f"https://www.youtube.com/watch?v={vid}") == vid
    assert extract_youtube_id(f"https://youtu.be/{vid}") == vid
    assert extract_youtube_id(f"https://www.youtube.com/embed/{vid}") == vid
    assert extract_youtube_id(f"https://www.youtube.com/shorts/{vid}") == vid
    assert extract_youtube_id(f"youtube.com/watch?v={vid}&t=42") == vid
    assert extract_youtube_id(vid) == vid  # bare id


def test_extract_youtube_id_invalid():
    assert extract_youtube_id("https://example.com/watch?v=abc") is None
    assert extract_youtube_id("not a url") is None
    assert extract_youtube_id("") is None


def test_clean_text_fixes_hyphenation_and_whitespace():
    raw = "regres-\nsion   is    a\t\tmethod\n\n\n\nof   modeling"
    cleaned = clean_text(raw)
    assert "regression" in cleaned
    assert "  " not in cleaned.replace("\n", " ")
    assert "\n\n\n" not in cleaned


def test_format_timestamp():
    assert format_timestamp(65) == "1:05"
    assert format_timestamp(3661) == "1:01:01"
    assert format_timestamp(None) == ""


def test_youtube_watch_url_with_start():
    url = youtube_watch_url("abc12345678", 763.9)
    assert url.endswith("&t=763")
