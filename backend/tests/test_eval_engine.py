from fastapi.testclient import TestClient

from app.eval.metrics import retrieval_metrics, token_f1
from app.main import app
from app.models.document import Document

client = TestClient(app)


class _FakeDoc:
    def __init__(self, metadata):
        self.metadata = metadata


class _FakeQuestion:
    def __init__(self, relevant_document_ids=None, relevant_chunk_ids=None):
        self.relevant_document_ids = relevant_document_ids or []
        self.relevant_chunk_ids = relevant_chunk_ids or []


# --------------------------------------------------------- metrics: math ---


def test_retrieval_metrics_match_hand_computed_values():
    hits = [_FakeDoc({"document_id": f"doc{i}"}) for i in [1, 2, 3, 4, 5]]
    q = _FakeQuestion(relevant_document_ids=["doc2", "doc4"])
    r = retrieval_metrics(q, hits, k=5)

    assert abs(r["precision_at_k"] - 0.4) < 1e-6
    assert abs(r["recall_at_k"] - 1.0) < 1e-6
    assert r["hit_rate"] == 1.0
    assert abs(r["mrr"] - 0.5) < 1e-6
    assert abs(r["ndcg_at_k"] - 0.6509) < 1e-3


def test_retrieval_metrics_none_without_ground_truth():
    hits = [_FakeDoc({"document_id": "doc1"})]
    q = _FakeQuestion()  # no relevant_document_ids, no relevant_chunk_ids
    r = retrieval_metrics(q, hits, k=1)
    assert all(v is None for key, v in r.items() if key != "level")


def test_retrieval_metrics_dedupes_same_document_across_chunks():
    """Regression test: multiple retrieved CHUNKS from the same relevant
    DOCUMENT must not push recall/precision above 1.0 — caught in manual
    integration testing before this test existed."""
    hits = [_FakeDoc({"document_id": "doc1"}) for _ in range(3)]
    q = _FakeQuestion(relevant_document_ids=["doc1"])
    r = retrieval_metrics(q, hits, k=3)

    assert r["recall_at_k"] == 1.0
    assert r["precision_at_k"] == 1 / 3
    assert r["hit_rate"] == 1.0
    for key, val in r.items():
        if key != "level" and val is not None:
            assert 0.0 <= val, f"{key}={val} should never be negative"
    assert r["recall_at_k"] <= 1.0
    assert r["precision_at_k"] <= 1.0


def test_token_f1_identical_and_disjoint():
    assert token_f1("the cat sat", "the cat sat") == 1.0
    assert token_f1("completely different words", "nothing overlaps at all") == 0.0
    assert token_f1("", "something") == 0.0


# ------------------------------------------------------------ engine: API --


def _make_pipeline():
    r = client.post(
        "/api/pipelines",
        json={
            "name": "Eval Engine Test Pipeline",
            "chunking_strategy": "recursive",
            "chunk_size": 150,
            "chunk_overlap": 20,
            "embedding_model": "local-tfidf-384",
            "retriever_type": "hybrid",
            "reranker_type": "none",
            "llm_model": "openai/gpt-oss-120b",
            "top_k": 3,
        },
    )
    assert r.status_code == 200
    return r.json()["id"]


def _make_dataset_with_question(db_session, document_id):
    ds = client.post("/api/evaluations/datasets", json={"name": "Engine-Test-QA"}).json()
    client.post(
        f"/api/evaluations/datasets/{ds['id']}/questions",
        json={
            "question": "What is this document about?",
            "ground_truth_answer": "test content",
            "relevant_document_ids": [document_id] if document_id else [],
            "relevant_chunk_ids": [],
        },
    )
    return ds["id"]


def test_create_run_rejects_missing_pipeline_or_dataset():
    ds_id = _make_dataset_with_question(None, None)
    r = client.post("/api/evaluations/runs", json={"pipeline_id": "does-not-exist", "dataset_id": ds_id})
    assert r.status_code == 404

    pipeline_id = _make_pipeline()
    r = client.post("/api/evaluations/runs", json={"pipeline_id": pipeline_id, "dataset_id": "does-not-exist"})
    assert r.status_code == 404


def test_create_run_rejects_empty_dataset():
    pipeline_id = _make_pipeline()
    ds = client.post("/api/evaluations/datasets", json={"name": "Empty-QA"}).json()
    r = client.post("/api/evaluations/runs", json={"pipeline_id": pipeline_id, "dataset_id": ds["id"]})
    assert r.status_code == 400


def test_run_completes_and_all_summary_metrics_are_valid_range():
    pipeline_id = _make_pipeline()
    ds_id = _make_dataset_with_question(None, None)  # no relevant docs -- fine, tests generation-only metrics

    r = client.post("/api/evaluations/runs", json={"pipeline_id": pipeline_id, "dataset_id": ds_id})
    assert r.status_code == 200
    run_id = r.json()["id"]

    detail = client.get(f"/api/evaluations/runs/{run_id}").json()
    assert detail["status"] == "completed"
    assert len(detail["results"]) == 1

    for key, val in detail["summary_metrics"].items():
        if val is not None:
            assert 0.0 <= val <= 1.0, f"{key}={val} outside [0,1]"