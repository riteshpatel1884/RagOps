"""Thin wrapper around Qdrant, running in local (embedded, file-backed) mode
so no Docker/Qdrant server is required. Point QDRANT_PATH at a real Qdrant
server URL later (Phase 17) without changing calling code.

Phase 2: one collection per embedding model (dimensions differ per model,
and a single collection can only hold one vector size), named
"{qdrant_collection}__{embedder_name}".
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings

settings = get_settings()

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(path=settings.qdrant_path)
    return _client


def collection_name(embedder_name: str) -> str:
    return f"{settings.qdrant_collection}__{embedder_name}"


def ensure_collection(embedder_name: str, dimensions: int) -> str:
    client = get_client()
    name = collection_name(embedder_name)
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dimensions, distance=qm.Distance.COSINE),
        )
    return name


def upsert_chunks(
    embedder_name: str, chunk_ids: list[str], vectors: list[list[float]], payloads: list[dict]
) -> None:
    client = get_client()
    client.upsert(
        collection_name=collection_name(embedder_name),
        points=qm.Batch(ids=chunk_ids, vectors=vectors, payloads=payloads),
    )


def search(
    embedder_name: str, vector: list[float], top_k: int = 5, document_id: str | None = None
) -> list[dict]:
    client = get_client()
    query_filter = None
    if document_id:
        query_filter = qm.Filter(
            must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
        )
    try:
        results = client.search(
            collection_name=collection_name(embedder_name),
            query_vector=vector,
            limit=top_k,
            query_filter=query_filter,
        )
    except Exception:
        return []  # collection doesn't exist yet — nothing indexed for this embedder
    return [
        {
            "chunk_id": r.id,
            "score": r.score,
            "text": r.payload.get("text"),
            "document_id": r.payload.get("document_id"),
            "filename": r.payload.get("filename"),
            "page_number": r.payload.get("page_number"),
            "parent_text": r.payload.get("parent_text"),
        }
        for r in results
    ]
