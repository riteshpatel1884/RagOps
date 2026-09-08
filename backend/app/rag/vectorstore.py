"""Vector store via LangChain's QdrantVectorStore, still backed by
qdrant-client in the same local-embedded/Qdrant-Cloud dual mode as before
(QDRANT_URL set -> cloud; unset -> local file-backed, no server needed).

One collection per embedding model (dimensions can differ per model), named
"{qdrant_collection}__{embedder_name}". Metadata is filterable via
"metadata.<key>" field paths (that's where langchain_qdrant stores it).
"""
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings
from app.rag.embeddings import get_dimensions, get_langchain_embeddings

settings = get_settings()

_client: QdrantClient | None = None
_stores: dict[str, QdrantVectorStore] = {}


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        if settings.qdrant_url:
            _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        else:
            _client = QdrantClient(path=settings.qdrant_path)
    return _client


def collection_name(embedder_name: str) -> str:
    return f"{settings.qdrant_collection}__{embedder_name}"


def _ensure_collection(client: QdrantClient, name: str, dimensions: int) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=dimensions, distance=qm.Distance.COSINE),
        )


def get_store(embedder_name: str) -> QdrantVectorStore:
    if embedder_name not in _stores:
        client = get_client()
        name = collection_name(embedder_name)
        _ensure_collection(client, name, get_dimensions(embedder_name))
        _stores[embedder_name] = QdrantVectorStore(
            client=client,
            collection_name=name,
            embedding=get_langchain_embeddings(embedder_name),
        )
    return _stores[embedder_name]


def add_documents(embedder_name: str, documents: list[Document], ids: list[str]) -> None:
    if not documents:
        return
    get_store(embedder_name).add_documents(documents, ids=ids)


def document_id_filter(document_id: str) -> qm.Filter:
    return qm.Filter(
        must=[qm.FieldCondition(key="metadata.document_id", match=qm.MatchValue(value=document_id))]
    )
