from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.pipeline import Pipeline
from app.rag.chunker import CHUNKING_STRATEGIES
from app.rag.embeddings import list_embedders
from app.services.llm import AVAILABLE_LLMS

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

RETRIEVER_TYPES = ["bm25", "dense", "hybrid"]
RERANKER_TYPES = ["none", "cross_encoder"]


class PipelineIn(BaseModel):
    name: str
    chunking_strategy: str = "recursive"
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0, le=1024)
    embedding_model: str = "local-tfidf-384"
    retriever_type: str = "hybrid"
    reranker_type: str = "none"
    llm_model: str = "claude-sonnet-4-6"
    top_k: int = Field(default=5, ge=1, le=50)


def _serialize(p: Pipeline) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "chunking_strategy": p.chunking_strategy,
        "chunk_size": p.chunk_size,
        "chunk_overlap": p.chunk_overlap,
        "embedding_model": p.embedding_model,
        "retriever_type": p.retriever_type,
        "reranker_type": p.reranker_type,
        "llm_model": p.llm_model,
        "top_k": p.top_k,
        "created_at": p.created_at,
    }


@router.get("/options")
def get_options():
    """Valid values for each dropdown in the Pipeline Builder."""
    return {
        "chunking_strategy": list(CHUNKING_STRATEGIES.keys()),
        "embedding_model": list_embedders(),
        "retriever_type": RETRIEVER_TYPES,
        "reranker_type": RERANKER_TYPES,
        "llm_model": AVAILABLE_LLMS,
    }


@router.get("")
def list_pipelines(db: Session = Depends(get_db)):
    pipelines = db.query(Pipeline).order_by(Pipeline.created_at.desc()).all()
    return [_serialize(p) for p in pipelines]


@router.post("")
def create_pipeline(payload: PipelineIn, db: Session = Depends(get_db)):
    if payload.chunking_strategy not in CHUNKING_STRATEGIES:
        raise HTTPException(400, f"Unknown chunking_strategy: {payload.chunking_strategy}")
    if payload.embedding_model not in list_embedders():
        raise HTTPException(400, f"Unknown embedding_model: {payload.embedding_model}")
    if payload.retriever_type not in RETRIEVER_TYPES:
        raise HTTPException(400, f"Unknown retriever_type: {payload.retriever_type}")
    if payload.reranker_type not in RERANKER_TYPES:
        raise HTTPException(400, f"Unknown reranker_type: {payload.reranker_type}")

    pipeline = Pipeline(**payload.model_dump())
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return _serialize(pipeline)


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).get(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    db.delete(pipeline)
    db.commit()
    return {"deleted": pipeline_id}
