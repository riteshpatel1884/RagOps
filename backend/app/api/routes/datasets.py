import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.document import Document
from app.models.pipeline import Pipeline
from app.rag.pipeline import ingest_document

router = APIRouter(prefix="/datasets", tags=["datasets"])
settings = get_settings()


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "page_count": d.page_count,
            "pipeline_id": d.pipeline_id,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.post("/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    pipeline_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Phase 1 supports PDF uploads only.")

    pipeline = _resolve_pipeline(db, pipeline_id)

    os.makedirs(settings.upload_dir, exist_ok=True)
    document = Document(filename=file.filename, status="processing", pipeline_id=pipeline.id)
    db.add(document)
    db.commit()
    db.refresh(document)

    dest_path = os.path.join(settings.upload_dir, f"{document.id}_{uuid.uuid4().hex}.pdf")
    with open(dest_path, "wb") as f:
        f.write(file.file.read())

    background_tasks.add_task(_ingest_in_background, document.id, dest_path, pipeline.id)

    return {"id": document.id, "filename": document.filename, "status": document.status}


def _resolve_pipeline(db: Session, pipeline_id: str | None) -> Pipeline:
    if pipeline_id:
        pipeline = db.query(Pipeline).get(pipeline_id)
        if pipeline:
            return pipeline
    # fall back to the oldest saved pipeline (the seeded "Default Pipeline")
    pipeline = db.query(Pipeline).order_by(Pipeline.created_at.asc()).first()
    if not pipeline:
        raise HTTPException(400, "No pipelines exist yet — create one under Pipelines first.")
    return pipeline


def _ingest_in_background(document_id: str, file_path: str, pipeline_id: str):
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        document = db.query(Document).get(document_id)
        pipeline = db.query(Pipeline).get(pipeline_id)
        if document and pipeline:
            ingest_document(db, document, file_path, pipeline)
    finally:
        db.close()


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).get(document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    db.delete(document)
    db.commit()
    return {"deleted": document_id}
