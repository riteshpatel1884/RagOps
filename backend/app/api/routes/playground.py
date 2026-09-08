from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.pipeline import Pipeline
from app.rag.pipeline import ask

router = APIRouter(prefix="/playground", tags=["playground"])


class AskRequest(BaseModel):
    question: str
    pipeline_id: str | None = None


@router.post("/ask")
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    pipeline = None
    if payload.pipeline_id:
        pipeline = db.query(Pipeline).get(payload.pipeline_id)
    if not pipeline:
        pipeline = db.query(Pipeline).order_by(Pipeline.created_at.asc()).first()
    if not pipeline:
        raise HTTPException(400, "No pipelines exist yet — create one under Pipelines first.")

    return ask(db, payload.question, pipeline)
