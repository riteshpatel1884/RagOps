from langchain_core.documents import Document

from app.rag.chunker import recursive_chunk


def test_recursive_chunk_respects_chunk_size():
    long_text = "Sentence one. " * 200  # ~2800 chars
    pages = [Document(page_content=long_text, metadata={"page_number": 1})]

    chunks = recursive_chunk(pages, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(c.page_content) <= 220 for c in chunks)  # size + overlap slack
    assert all(c.metadata["page_number"] == 1 for c in chunks)


def test_recursive_chunk_short_text_single_chunk():
    pages = [Document(page_content="Short text.", metadata={"page_number": 1})]
    chunks = recursive_chunk(pages, chunk_size=512, chunk_overlap=64)
    assert len(chunks) == 1
    assert chunks[0].page_content == "Short text."
