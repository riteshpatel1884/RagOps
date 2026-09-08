"""Phase 2 retrieval strategies: bm25, dense, hybrid.

BM25 index is rebuilt from Postgres on every query — fine at demo/portfolio
scale (hundreds to low-thousands of chunks). At real scale you'd persist an
inverted index (e.g. via Qdrant's sparse vectors, or Elasticsearch)
alongside the dense one instead of rebuilding it per request.
"""
import re

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.models.document import Chunk, Document
from app.rag import vectorstore
from app.rag.embeddings import get_embedder

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _chunk_rows(db: Session, document_id: str | None = None) -> list[tuple[Chunk, Document]]:
    q = db.query(Chunk, Document).join(Document, Chunk.document_id == Document.id)
    if document_id:
        q = q.filter(Chunk.document_id == document_id)
    return q.all()


def _to_hit(chunk: Chunk, document: Document, score: float) -> dict:
    return {
        "chunk_id": chunk.id,
        "score": score,
        "text": chunk.text,
        "document_id": document.id,
        "filename": document.filename,
        "page_number": chunk.page_number,
        "parent_text": chunk.parent_text,
    }


def bm25_search(
    db: Session, query: str, top_k: int = 5, document_id: str | None = None
) -> list[dict]:
    rows = _chunk_rows(db, document_id)
    if not rows:
        return []

    corpus_tokens = [_tokenize(chunk.text) for chunk, _ in rows]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip(rows, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [_to_hit(chunk, doc, float(score)) for (chunk, doc), score in ranked if score > 0]


def dense_search(
    query: str,
    embedding_model: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    embedder = get_embedder(embedding_model)
    query_vector = embedder.embed([query])[0]
    return vectorstore.search(embedding_model, query_vector, top_k=top_k, document_id=document_id)


def hybrid_search(
    db: Session,
    query: str,
    embedding_model: str,
    top_k: int = 5,
    document_id: str | None = None,
    rrf_k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion of BM25 (lexical) + dense (semantic) results.
    RRF score = sum(1 / (rrf_k + rank)) across the lists a chunk appears in
    — a standard way to combine differently-scaled rankers without needing
    to normalize raw scores against each other."""
    bm25_hits = bm25_search(db, query, top_k=top_k * 2, document_id=document_id)
    dense_hits = dense_search(query, embedding_model, top_k=top_k * 2, document_id=document_id)

    fused: dict[str, dict] = {}
    fused_scores: dict[str, float] = {}

    for rank, hit in enumerate(bm25_hits):
        fused[hit["chunk_id"]] = hit
        fused_scores[hit["chunk_id"]] = fused_scores.get(hit["chunk_id"], 0) + 1 / (rrf_k + rank + 1)

    for rank, hit in enumerate(dense_hits):
        fused[hit["chunk_id"]] = hit
        fused_scores[hit["chunk_id"]] = fused_scores.get(hit["chunk_id"], 0) + 1 / (rrf_k + rank + 1)

    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]
    results = []
    for cid in ranked_ids:
        hit = dict(fused[cid])
        hit["score"] = fused_scores[cid]
        results.append(hit)
    return results


def retrieve(
    strategy: str,
    db: Session,
    query: str,
    embedding_model: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[dict]:
    if strategy == "bm25":
        return bm25_search(db, query, top_k=top_k, document_id=document_id)
    if strategy == "dense":
        return dense_search(query, embedding_model, top_k=top_k, document_id=document_id)
    if strategy == "hybrid":
        return hybrid_search(db, query, embedding_model, top_k=top_k, document_id=document_id)
    raise ValueError(f"Unknown retriever type: {strategy!r}")
