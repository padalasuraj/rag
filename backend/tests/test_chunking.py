from app.services.chunking_service import (
    chunk_pages,
    chunk_text,
    chunk_transcript,
)


def test_chunk_text_respects_size():
    text = "word " * 1000  # ~5000 chars
    chunks = chunk_text(text, size=500, overlap=50)
    assert len(chunks) > 1
    # Allow a margin for the prepended overlap tail.
    assert all(len(c.text) <= 500 + 60 for c in chunks)
    # Indices are sequential.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_text_overlap_carries_context():
    text = "Alpha beta gamma. " * 100
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) >= 2
    # The second chunk should begin with tail text from the first.
    assert len(chunks[1].text) > 0


def test_chunk_pages_preserves_page_numbers():
    pages = [(1, "content one " * 100), (2, "content two " * 100)]
    chunks = chunk_pages(pages)
    page_numbers = {c.page for c in chunks}
    assert page_numbers == {1, 2}
    # Global chunk indices remain unique and sequential across pages.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_transcript_attaches_timestamps():
    segments = [
        {"text": f"segment number {i}", "start": float(i * 5), "duration": 5.0}
        for i in range(200)
    ]
    chunks = chunk_transcript(segments)
    assert len(chunks) >= 2
    assert chunks[0].start_seconds == 0.0
    # Later chunks start later in the video.
    assert chunks[-1].start_seconds > chunks[0].start_seconds
