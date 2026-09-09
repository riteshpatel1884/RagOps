import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
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


class EvaluationRun(Base):
    """One execution of a Pipeline against an EvalDataset: Phase 4's actual
    deliverable — "run a RAG pipeline against a benchmark and receive real
    evaluation metrics." Runs go through the same background-task + polling
    pattern as document ingestion, since scoring N questions (each a real
    retrieval + generation call) isn't instant."""

    __tablename__ = "evaluation_runs"

    id = Column(String, primary_key=True, default=_uuid)
    pipeline_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    dataset_id = Column(String, ForeignKey("eval_datasets.id"), nullable=False)
    status = Column(String, default="running")  # running | completed | failed
    question_count = Column(Integer, default=0)
    summary_metrics = Column(JSON, default=dict)  # dataset-level metric averages
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    results = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(Base):
    """Per-question scoring detail within one EvaluationRun."""

    __tablename__ = "evaluation_results"

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("evaluation_runs.id"), nullable=False)
    question_id = Column(String, ForeignKey("eval_questions.id"), nullable=False)

    answer = Column(Text, default="")
    retrieval_metrics = Column(JSON, default=dict)
    generation_metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("EvaluationRun", back_populates="results")