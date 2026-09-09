import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.evaluation import EvalDataset, EvalQuestion

router = APIRouter(prefix="/evaluations/datasets", tags=["evaluations"])


# ---------------------------------------------------------------- schemas --


class DatasetIn(BaseModel):
    name: str


class QuestionIn(BaseModel):
    question: str
    ground_truth_answer: str = ""
    relevant_document_ids: list[str] = Field(default_factory=list)
    relevant_chunk_ids: list[str] = Field(default_factory=list)


# ------------------------------------------------------------- serializers --


def _serialize_dataset(ds: EvalDataset, question_count: int | None = None) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "created_at": ds.created_at,
        "question_count": question_count if question_count is not None else len(ds.questions),
    }


def _serialize_question(q: EvalQuestion, filenames_by_id: dict[str, str]) -> dict:
    return {
        "id": q.id,
        "dataset_id": q.dataset_id,
        "question": q.question,
        "ground_truth_answer": q.ground_truth_answer,
        "relevant_document_ids": q.relevant_document_ids or [],
        "relevant_documents": [
            filenames_by_id.get(d, d) for d in (q.relevant_document_ids or [])
        ],
        "relevant_chunk_ids": q.relevant_chunk_ids or [],
        "created_at": q.created_at,
    }


def _filenames_by_id(db: Session) -> dict[str, str]:
    return {d.id: d.filename for d in db.query(Document).all()}


def _resolve_document_refs(db: Session, refs: list[str]) -> tuple[list[str], int]:
    """Accepts a list of Document ids OR filenames (as typed by a human in a
    CSV/JSON import) and resolves them to real Document ids. Returns
    (resolved_ids, unresolved_count)."""
    if not refs:
        return [], 0
    by_id = {d.id: d.id for d in db.query(Document).all()}
    by_filename = {d.filename.lower(): d.id for d in db.query(Document).all()}

    resolved, unresolved = [], 0
    for ref in refs:
        ref = ref.strip()
        if not ref:
            continue
        if ref in by_id:
            resolved.append(ref)
        elif ref.lower() in by_filename:
            resolved.append(by_filename[ref.lower()])
        else:
            unresolved += 1
    return resolved, unresolved


# ---------------------------------------------------------------- datasets --


@router.get("")
def list_datasets(db: Session = Depends(get_db)):
    from sqlalchemy import func

    datasets = db.query(EvalDataset).order_by(EvalDataset.created_at.desc()).all()
    count_rows = (
        db.query(EvalQuestion.dataset_id, func.count(EvalQuestion.id))
        .group_by(EvalQuestion.dataset_id)
        .all()
    )
    count_by_dataset = dict(count_rows)
    return [_serialize_dataset(ds, count_by_dataset.get(ds.id, 0)) for ds in datasets]


@router.post("")
def create_dataset(payload: DatasetIn, db: Session = Depends(get_db)):
    ds = EvalDataset(name=payload.name)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _serialize_dataset(ds, 0)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(EvalDataset).get(dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    db.delete(ds)
    db.commit()
    return {"deleted": dataset_id}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(EvalDataset).get(dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    filenames = _filenames_by_id(db)
    questions = (
        db.query(EvalQuestion)
        .filter(EvalQuestion.dataset_id == dataset_id)
        .order_by(EvalQuestion.created_at.asc())
        .all()
    )
    return {
        **_serialize_dataset(ds, len(questions)),
        "questions": [_serialize_question(q, filenames) for q in questions],
    }


# --------------------------------------------------------------- questions --


@router.post("/{dataset_id}/questions")
def add_question(dataset_id: str, payload: QuestionIn, db: Session = Depends(get_db)):
    ds = db.query(EvalDataset).get(dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")

    resolved_docs, _ = _resolve_document_refs(db, payload.relevant_document_ids)
    q = EvalQuestion(
        dataset_id=dataset_id,
        question=payload.question,
        ground_truth_answer=payload.ground_truth_answer,
        relevant_document_ids=resolved_docs,
        relevant_chunk_ids=payload.relevant_chunk_ids,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return _serialize_question(q, _filenames_by_id(db))


@router.put("/{dataset_id}/questions/{question_id}")
def update_question(
    dataset_id: str, question_id: str, payload: QuestionIn, db: Session = Depends(get_db)
):
    q = (
        db.query(EvalQuestion)
        .filter(EvalQuestion.id == question_id, EvalQuestion.dataset_id == dataset_id)
        .first()
    )
    if not q:
        raise HTTPException(404, "Question not found")

    resolved_docs, _ = _resolve_document_refs(db, payload.relevant_document_ids)
    q.question = payload.question
    q.ground_truth_answer = payload.ground_truth_answer
    q.relevant_document_ids = resolved_docs
    q.relevant_chunk_ids = payload.relevant_chunk_ids
    db.commit()
    db.refresh(q)
    return _serialize_question(q, _filenames_by_id(db))


@router.delete("/{dataset_id}/questions/{question_id}")
def delete_question(dataset_id: str, question_id: str, db: Session = Depends(get_db)):
    q = (
        db.query(EvalQuestion)
        .filter(EvalQuestion.id == question_id, EvalQuestion.dataset_id == dataset_id)
        .first()
    )
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()
    return {"deleted": question_id}


# --------------------------------------------------------- bulk CSV/JSON ---


@router.post("/{dataset_id}/upload")
async def upload_questions(dataset_id: str, file: UploadFile, db: Session = Depends(get_db)):
    """CSV columns: question, ground_truth_answer, relevant_documents
    (semicolon-separated filenames or document ids), relevant_chunks
    (semicolon-separated chunk ids, optional).

    JSON: a list of objects with the same fields as columns above, but
    relevant_documents / relevant_chunks as arrays instead of
    semicolon-separated strings — matching the roadmap's example schema.
    """
    ds = db.query(EvalDataset).get(dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")

    raw = (await file.read()).decode("utf-8-sig")
    filename = (file.filename or "").lower()

    rows: list[dict] = []
    if filename.endswith(".json"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise HTTPException(400, f"Invalid JSON: {e}")
        if not isinstance(parsed, list):
            raise HTTPException(400, "JSON file must be a list of question objects")
        for item in parsed:
            rows.append(
                {
                    "question": item.get("question", ""),
                    "ground_truth_answer": item.get("ground_truth_answer", ""),
                    "relevant_documents": item.get("relevant_documents", []) or [],
                    "relevant_chunks": item.get("relevant_chunks", []) or [],
                }
            )
    elif filename.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(raw))
        for row in reader:
            rows.append(
                {
                    "question": (row.get("question") or "").strip(),
                    "ground_truth_answer": (row.get("ground_truth_answer") or "").strip(),
                    "relevant_documents": [
                        s.strip() for s in (row.get("relevant_documents") or "").split(";") if s.strip()
                    ],
                    "relevant_chunks": [
                        s.strip() for s in (row.get("relevant_chunks") or "").split(";") if s.strip()
                    ],
                }
            )
    else:
        raise HTTPException(400, "Only .csv or .json files are supported")

    created, skipped, unresolved_doc_refs = 0, 0, 0
    for row in rows:
        if not row["question"]:
            skipped += 1
            continue
        resolved_docs, unresolved = _resolve_document_refs(db, row["relevant_documents"])
        unresolved_doc_refs += unresolved
        db.add(
            EvalQuestion(
                dataset_id=dataset_id,
                question=row["question"],
                ground_truth_answer=row["ground_truth_answer"],
                relevant_document_ids=resolved_docs,
                relevant_chunk_ids=row["relevant_chunks"],
            )
        )
        created += 1
    db.commit()

    return {
        "created": created,
        "skipped_empty_rows": skipped,
        "unresolved_document_refs": unresolved_doc_refs,
    }
