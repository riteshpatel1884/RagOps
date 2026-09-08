from app.rag.chunker import recursive_chunk
from app.rag.parser import ParsedPage


def test_recursive_chunk_respects_chunk_size():
    long_text = "Sentence one. " * 200  # ~2800 chars
    pages = [ParsedPage(page_number=1, text=long_text)]

    chunks = recursive_chunk(pages, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(c.text) <= 260 for c in chunks)  # size + overlap slack
    assert all(c.page_number == 1 for c in chunks)


def test_recursive_chunk_short_text_single_chunk():
    pages = [ParsedPage(page_number=1, text="Short text.")]
    chunks = recursive_chunk(pages, chunk_size=512, chunk_overlap=64)
    assert len(chunks) == 1
    assert chunks[0].text == "Short text."
