import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Integer

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Pipeline(Base):
    """A saved, named RAG configuration. Phase 2 lets you create and save
    these; Phase 5 (Experiment Engine) is what sweeps many of them
    automatically and compares results."""

    __tablename__ = "pipelines"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)

    chunking_strategy = Column(String, default="recursive")  # fixed | recursive | semantic | parent_child
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=64)

    embedding_model = Column(String, default="local-tfidf-384")  # see app/rag/embeddings.py
    retriever_type = Column(String, default="hybrid")  # bm25 | dense | hybrid
    reranker_type = Column(String, default="none")  # none | cross_encoder
    llm_model = Column(String, default="claude-sonnet-4-6")

    top_k = Column(Integer, default=5)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
