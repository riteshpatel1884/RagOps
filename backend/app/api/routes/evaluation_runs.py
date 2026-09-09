from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.eval.engine import run_evaluation
from app.models.evaluation import EvalDataset, EvaluationResult, EvaluationRun
from app.models.pipeline import Pipeline

router = APIRouter(prefix="/evaluations/runs", tags=["evaluations"])


class RunIn(BaseModel):
    pipeline_id: str
    dataset_id: str


def _serialize_run(run: EvaluationRun, pipeline_name: str | None, dataset_name: str | None) -> dict:
    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "pipeline_name": pipeline_name,
        "dataset_id": run.dataset_id,
        "dataset_name": dataset_name,
        "status": run.status,
        "question_count": run.question_count,
        "summary_metrics": run.summary_metrics or {},
        "created_at": run.created_at,
    }


@router.get("")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()
    pipelines = {p.id: p.name for p in db.query(Pipeline).all()}
    datasets = {d.id: d.name for d in db.query(EvalDataset).all()}
    return [_serialize_run(r, pipelines.get(r.pipeline_id), datasets.get(r.dataset_id)) for r in runs]


@router.post("")
def create_run(payload: RunIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).get(payload.pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    dataset = db.query(EvalDataset).get(payload.dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    if not dataset.questions:
        raise HTTPException(400, "This dataset has no questions yet.")

    run = EvaluationRun(
        pipeline_id=pipeline.id,
        dataset_id=dataset.id,
        status="running",
        question_count=len(dataset.questions),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(_run_in_background, run.id, pipeline.id, dataset.id)

    return _serialize_run(run, pipeline.name, dataset.name)


def _run_in_background(run_id: str, pipeline_id: str, dataset_id: str):
    db = SessionLocal()
    try:
        pipeline = db.query(Pipeline).get(pipeline_id)
        dataset = db.query(EvalDataset).get(dataset_id)
        run = db.query(EvaluationRun).get(run_id)
        if pipeline and dataset and run:
            run_evaluation(db, pipeline, dataset, existing_run=run)
    finally:
        db.close()


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    pipeline = db.query(Pipeline).get(run.pipeline_id)
    dataset = db.query(EvalDataset).get(run.dataset_id)
    questions_by_id = {q.id: q for q in dataset.questions} if dataset else {}

    results = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.run_id == run_id)
        .order_by(EvaluationResult.created_at.asc())
        .all()
    )

    return {
        **_serialize_run(run, pipeline.name if pipeline else None, dataset.name if dataset else None),
        "results": [
            {
                "id": res.id,
                "question": questions_by_id[res.question_id].question
                if res.question_id in questions_by_id
                else None,
                "ground_truth_answer": questions_by_id[res.question_id].ground_truth_answer
                if res.question_id in questions_by_id
                else None,
                "answer": res.answer,
                "retrieval_metrics": res.retrieval_metrics,
                "generation_metrics": res.generation_metrics,
            }
            for res in results
        ],
    }


@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}