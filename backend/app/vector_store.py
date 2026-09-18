"""
Qdrant-backed vector store, wired through LangChain's own integration
(`langchain_qdrant.QdrantVectorStore`) rather than the raw qdrant-client API.

Uses Qdrant's embedded local mode (`:memory:` or an on-disk path) so the
whole pipeline runs with no external Qdrant server required. Point
`location` at a real Qdrant server URL (e.g. "http://localhost:6333") in
production — nothing else in this class changes.
"""
from typing import List
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore


class QdrantStore:
    def __init__(self, embedding: Embeddings, collection_name: str = "rag_chunks", location: str = ":memory:"):
        self.embedding = embedding
        self.collection_name = collection_name
        self.location = location
        self.vectorstore: QdrantVectorStore | None = None

    def build(self, documents: List[Document]) -> None:
        """(Re)create the collection and index all chunks via LangChain's QdrantVectorStore."""
        kwargs = {"location": self.location} if not self.location.startswith("http") else {"url": self.location}
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