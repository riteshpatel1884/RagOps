"""Phase 4 evaluation engine.

Runs a saved Pipeline against every question in a saved EvalDataset, using
the exact same retriever/reranker/generation code path as the Playground
(app/rag/retriever.py, app/rag/reranker.py, app/services/llm.py) — an
evaluation run is not a separate simulation of the pipeline, it's the real
pipeline scored.

Metrics per question:
  Retrieval  (app/eval/metrics.py, deterministic): Recall@K, Precision@K,
             Hit Rate, MRR, nDCG@K — graded against the question's
             relevant_document_ids / relevant_chunk_ids.
  Generation (mixed):
    - answer_correctness  : token-F1 vs. ground_truth_answer (deterministic)
    - answer_relevance    : cosine(question, answer) via the pipeline's own
                             embedding model (deterministic)
    - context_relevance   : mean cosine(question, retrieved chunk) (deterministic)
    - faithfulness        : LLM-as-judge when GROQ_API_KEY is set, else a
                             cosine(answer, context) proxy (app/eval/judge.py)
    - hallucination_rate  : 1 - faithfulness
    - citation_correctness / citation_completeness : the "sources" returned
      to the user ARE the citations, so these reuse retrieval
      precision@k/recall@k rather than parsing citation markers out of
      free-text — parsing footnotes the model wasn't asked to produce would
      be a fake metric, not a real one.
"""
import numpy as np
from sqlalchemy.orm import Session

from app.eval import metrics as m
from app.eval.judge import llm_judge_faithfulness
from app.models.evaluation import EvalDataset, EvaluationResult, EvaluationRun
from app.models.pipeline import Pipeline
from app.rag import retriever
from app.rag.embeddings import get_langchain_embeddings
from app.rag.reranker import rerank
from app.services.llm import build_context_block, generate_answer

METRIC_KEYS = [
    "recall_at_k",
    "precision_at_k",
    "hit_rate",
    "mrr",
    "ndcg_at_k",
    "answer_correctness",
    "answer_relevance",
    "context_relevance",
    "faithfulness",
    "hallucination_rate",
    "citation_correctness",
    "citation_completeness",
]


def _cosine(a_vec: list[float], b_vec: list[float]) -> float:
    a, b = np.array(a_vec), np.array(b_vec)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(a @ b / denom)


def _evaluate_question(db: Session, pipeline: Pipeline, embedder, question) -> dict:
    fetch_k = pipeline.top_k * 2 if pipeline.reranker_type != "none" else pipeline.top_k
    hits = retriever.retrieve(
        pipeline.retriever_type, db, question.question, pipeline.embedding_model, top_k=fetch_k
    )
    hits = rerank(pipeline.reranker_type, question.question, hits, top_k=pipeline.top_k)
    answer = generate_answer(question.question, hits, model=pipeline.llm_model)

    r = m.retrieval_metrics(question, hits, pipeline.top_k)
    context = build_context_block(hits)

    correctness = (
        m.token_f1(answer, question.ground_truth_answer)
        if question.ground_truth_answer and answer.strip()
        else None
    )

    answer_relevance = None
    context_relevance = None
    if answer.strip() or hits:
        q_vec = embedder.embed_query(question.question)
        if answer.strip():
            answer_relevance = _cosine(q_vec, embedder.embed_query(answer))
        if hits:
            chunk_vecs = embedder.embed_documents([h.page_content for h in hits])
            context_relevance = sum(_cosine(q_vec, cv) for cv in chunk_vecs) / len(chunk_vecs)

    judge_score = llm_judge_faithfulness(answer, context, model=pipeline.llm_model)
    if judge_score is not None:
        faithfulness, faithfulness_source = judge_score, "llm_judge"
    elif context.strip() and answer.strip():
        faithfulness = _cosine(embedder.embed_query(answer), embedder.embed_query(context))
        faithfulness_source = "embedding_proxy"
    else:
        faithfulness, faithfulness_source = None, "none"
    hallucination_rate = (1 - faithfulness) if faithfulness is not None else None

    return {
        "answer": answer,
        "retrieval": {
            "recall_at_k": r["recall_at_k"],
            "precision_at_k": r["precision_at_k"],
            "hit_rate": r["hit_rate"],
            "mrr": r["mrr"],
            "ndcg_at_k": r["ndcg_at_k"],
            "level": r["level"],
        },
        "generation": {
            "answer_correctness": correctness,
            "answer_relevance": answer_relevance,
            "context_relevance": context_relevance,
            "faithfulness": faithfulness,
            "faithfulness_source": faithfulness_source,
            "hallucination_rate": hallucination_rate,
            "citation_correctness": r["precision_at_k"],
            "citation_completeness": r["recall_at_k"],
        },
    }


def run_evaluation(
    db: Session, pipeline: Pipeline, dataset: EvalDataset, existing_run: EvaluationRun | None = None
) -> EvaluationRun:
    run = existing_run
    if run is None:
        run = EvaluationRun(
            pipeline_id=pipeline.id,
            dataset_id=dataset.id,
            status="running",
            question_count=len(dataset.questions),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

    embedder = get_langchain_embeddings(pipeline.embedding_model)
    agg: dict[str, list[float]] = {k: [] for k in METRIC_KEYS}

    try:
        for question in dataset.questions:
            computed = _evaluate_question(db, pipeline, embedder, question)

            db.add(
                EvaluationResult(
                    run_id=run.id,
                    question_id=question.id,
                    answer=computed["answer"],
                    retrieval_metrics=computed["retrieval"],
                    generation_metrics=computed["generation"],
                )
            )

            for key in METRIC_KEYS:
                val = computed["retrieval"].get(key)
                if val is None:
                    val = computed["generation"].get(key)
                if isinstance(val, (int, float)):
                    agg[key].append(val)

        run.summary_metrics = {k: (sum(v) / len(v) if v else None) for k, v in agg.items()}
        run.status = "completed"
        db.commit()
        db.refresh(run)
    except Exception:
        run.status = "failed"
        db.commit()
        raise

    return run