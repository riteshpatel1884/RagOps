from app.rag.chunker import CHUNKING_STRATEGIES, chunk_document
from app.rag.embeddings import get_embedder, list_embedders
from app.rag.parser import ParsedPage
from app.rag.reranker import rerank


def _sample_pages():
    text = (
        "Revenue grew significantly in 2024. The company expanded into new markets. "
        "Profit margins improved due to cost cutting. However, headcount also grew. "
    ) * 3
    return [ParsedPage(page_number=1, text=text)]


def test_all_chunking_strategies_registered_and_runnable():
    pages = _sample_pages()
    for strategy in CHUNKING_STRATEGIES:
        chunks = chunk_document(strategy, pages, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 0
        assert all(c.text for c in chunks)


def test_parent_child_sets_parent_text_others_dont():
    pages = _sample_pages()
    pc_chunks = chunk_document("parent_child", pages, chunk_size=100, chunk_overlap=10)
    assert any(c.parent_text for c in pc_chunks)

    recursive_chunks = chunk_document("recursive", pages, chunk_size=100, chunk_overlap=10)
    assert all(c.parent_text is None for c in recursive_chunks)


def test_chunk_document_rejects_unknown_strategy():
    pages = _sample_pages()
    try:
        chunk_document("not_a_real_strategy", pages, 200, 20)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_two_embedding_models_registered_with_matching_dimensions():
    names = list_embedders()
    assert len(names) >= 2
    for name in names:
        embedder = get_embedder(name)
        vec = embedder.embed(["revenue grew 12% in 2024"])[0]
        assert len(vec) == embedder.dimensions


def test_reranker_none_is_passthrough():
    hits = [{"chunk_id": "1", "score": 0.1, "text": "a"}, {"chunk_id": "2", "score": 0.2, "text": "b"}]
    assert rerank("none", "query", hits) == hits


def test_reranker_cross_encoder_reorders_by_lexical_overlap():
    hits = [
        {"chunk_id": "1", "score": 0.5, "text": "the weather was nice today"},
        {"chunk_id": "2", "score": 0.4, "text": "revenue increased due to strong sales growth"},
    ]
    out = rerank("cross_encoder", "what caused revenue growth", hits)
    assert out[0]["chunk_id"] == "2"
