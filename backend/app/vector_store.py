"""
Qdrant-backed vector store, wired through LangChain's own integration
(`langchain_qdrant.QdrantVectorStore`) rather than the raw qdrant-client API.

Defaults to Qdrant Cloud if QDRANT_URL (and QDRANT_API_KEY) are set in the
environment (e.g. via .env) — otherwise falls back to Qdrant's embedded
`:memory:` mode so the pipeline still runs with zero external setup.
"""
import os
from typing import List
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore


class QdrantStore:
    def __init__(
        self,
        embedding: Embeddings,
        collection_name: str = "rag_chunks",
        location: str = None,
        api_key: str = None,
    ):
        self.embedding = embedding
        self.collection_name = collection_name
        # Precedence: explicit args > QDRANT_URL/QDRANT_API_KEY env vars > in-memory fallback.
        self.location = location or os.environ.get("QDRANT_URL") or ":memory:"
        self.api_key = api_key or os.environ.get("QDRANT_API_KEY")
        self.vectorstore: QdrantVectorStore | None = None

    def build(self, documents: List[Document]) -> None:
        """(Re)create the collection and index all chunks via LangChain's QdrantVectorStore."""
        if self.location.startswith("http"):
            kwargs = {"url": self.location}
            if self.api_key:
                kwargs["api_key"] = self.api_key
        else:
            kwargs = {"location": self.location}

        self.vectorstore = QdrantVectorStore.from_documents(
            documents,
            embedding=self.embedding,
            collection_name=self.collection_name,
            force_recreate=True,
            **kwargs,
        )

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Return top_k hits as [{chunk_id, doc_id, text, score}, ...], best first."""
        results = self.vectorstore.similarity_search_with_score(query, k=top_k)
        return [
            {
                "chunk_id": doc.metadata["chunk_id"],
                "doc_id": doc.metadata["doc_id"],
                "text": doc.page_content,
                "score": score,
            }
            for doc, score in results
        ]