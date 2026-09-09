import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class EvalDataset(Base):
    """A named, reusable set of ground-truth questions. Phase 4's evaluation
    engine runs a pipeline against one of these and scores it; Phase 5's
    experiment engine runs many pipelines against one automatically."""

    __tablename__ = "eval_datasets"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    questions = relationship(
        "EvalQuestion", back_populates="dataset", cascade="all, delete-orphan"
    )


class EvalQuestion(Base):
    """One ground-truth row: a question, its correct answer, and which
    already-uploaded documents/chunks are considered relevant — the basis
    for Recall@K, Precision@K, MRR, etc. in Phase 4."""

    __tablename__ = "eval_questions"

    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("eval_datasets.id"), nullable=False)

    question = Column(Text, nullable=False)
    ground_truth_answer = Column(Text, nullable=False, default="")
    relevant_document_ids = Column(JSON, default=list)  # list[str] -> Document.id
    relevant_chunk_ids = Column(JSON, default=list)  # list[str] -> Chunk.id, optional

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("EvalDataset", back_populates="questions")
