from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document

client = TestClient(app)


def _make_dataset(name="Test-QA"):
    r = client.post("/api/evaluations/datasets", json={"name": name})
    assert r.status_code == 200
    return r.json()["id"]


def test_create_and_list_dataset():
    ds_id = _make_dataset("List-Test-QA")
    r = client.get("/api/evaluations/datasets")
    assert r.status_code == 200
    assert any(d["id"] == ds_id for d in r.json())


def test_add_question_and_fetch_detail():
    ds_id = _make_dataset("Detail-Test-QA")
    r = client.post(
        f"/api/evaluations/datasets/{ds_id}/questions",
        json={
            "question": "What is RAG?",
            "ground_truth_answer": "Retrieval-Augmented Generation",
            "relevant_document_ids": [],
            "relevant_chunk_ids": [],
        },
    )
    assert r.status_code == 200

    detail = client.get(f"/api/evaluations/datasets/{ds_id}").json()
    assert detail["question_count"] == 1
    assert detail["questions"][0]["question"] == "What is RAG?"


def test_update_and_delete_question():
    ds_id = _make_dataset("Edit-Test-QA")
    q = client.post(
        f"/api/evaluations/datasets/{ds_id}/questions",
        json={"question": "Original?", "ground_truth_answer": "A"},
    ).json()

    r = client.put(
        f"/api/evaluations/datasets/{ds_id}/questions/{q['id']}",
        json={"question": "Edited?", "ground_truth_answer": "B"},
    )
    assert r.status_code == 200
    assert r.json()["question"] == "Edited?"

    r = client.delete(f"/api/evaluations/datasets/{ds_id}/questions/{q['id']}")
    assert r.status_code == 200
    detail = client.get(f"/api/evaluations/datasets/{ds_id}").json()
    assert detail["question_count"] == 0


def test_csv_upload_resolves_filenames_and_skips_empty_rows():
    ds_id = _make_dataset("CSV-Test-QA")
    csv_content = (
        "question,ground_truth_answer,relevant_documents,relevant_chunks\n"
        '"Real question","real answer","",""\n'
        '"","should be skipped","",""\n'
    )
    r = client.post(
        f"/api/evaluations/datasets/{ds_id}/upload",
        files={"file": ("questions.csv", csv_content, "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 1
    assert body["skipped_empty_rows"] == 1


def test_json_upload_matches_roadmap_schema():
    ds_id = _make_dataset("JSON-Test-QA")
    payload = [
        {
            "question": "What was revenue in 2024?",
            "ground_truth_answer": "42 million",
            "relevant_documents": ["doc_17"],
            "relevant_chunks": ["chunk_183"],
        }
    ]
    import json

    r = client.post(
        f"/api/evaluations/datasets/{ds_id}/upload",
        files={"file": ("questions.json", json.dumps(payload), "application/json")},
    )
    assert r.status_code == 200
    assert r.json()["created"] == 1


def test_delete_dataset_cascades_questions():
    ds_id = _make_dataset("Cascade-Test-QA")
    client.post(
        f"/api/evaluations/datasets/{ds_id}/questions",
        json={"question": "Q?", "ground_truth_answer": "A"},
    )
    r = client.delete(f"/api/evaluations/datasets/{ds_id}")
    assert r.status_code == 200
    assert client.get(f"/api/evaluations/datasets/{ds_id}").status_code == 404
