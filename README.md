# RAGOps

**A production-style platform for building, evaluating, and benchmarking Retrieval-Augmented Generation (RAG) pipelines.**

RAGOps lets you configure RAG pipelines (chunking, embeddings, retrieval, reranking), run them against ground-truth evaluation datasets, and get back objective retrieval and generation metrics — instead of eyeballing whether an answer "looks right."


---

## Why this project exists

Most RAG demos stop at "upload a PDF, ask a question, get an answer." That tells you nothing about *how good* the system actually is, or *which configuration* (chunking strategy, embedding model, retriever, reranker) performs best for a given use case.

RAGOps treats RAG as an engineering problem with measurable inputs and outputs:

```
BUILD → EVALUATE → OBSERVE → DEBUG → SECURE → OPTIMIZE → RECOMMEND
```

This repo currently covers the **BUILD** and **EVALUATE** stages end-to-end.

---

## Tech Stack

**Frontend**
- Next.js (JavaScript)
- Tailwind CSS
- shadcn/ui
- Recharts

**Backend**
- Python, FastAPI
- PostgreSQL (metadata, datasets, evaluation runs)
- Qdrant (vector store)
- Redis (caching layer, planned for optimization phase)

---

## Features Built So Far

### Phase 0 — Architecture & Project Setup
Full-stack scaffold with a clean separation of concerns:

```
frontend/
├── app/
│   ├── dashboard/  datasets/  pipelines/
│   ├── experiments/  evaluations/  traces/
│   └── security/  optimization/  settings/
├── components/  hooks/  lib/  services/

backend/
├── app/
│   ├── api/  core/  models/  services/
│   ├── rag/  evaluation/  experiments/
│   └── observability/  security/
└── tests/
```

A working application shell (sidebar navigation, dashboard layout) ties both together, running Next.js against a FastAPI server with live Postgres/Qdrant connections.

### Phase 1 — Basic RAG Pipeline
A single, reliable end-to-end RAG flow:

```
Document → Parser → Chunking → Embedding → Qdrant → Retriever → LLM → Answer + Sources
```

- PDF upload and parsing (`/datasets`)
- Chunking, embedding, and vector indexing on ingest
- A **RAG Playground** (`/playground`) to ask questions against indexed documents and inspect the answer alongside its retrieved sources, page references, and similarity scores

### Phase 2 — Configurable RAG Pipelines
Turned the hardcoded pipeline into a real experimentation surface. Every stage of retrieval is swappable and versioned:

| Stage | Options implemented |
|---|---|
| Chunking | Fixed, Recursive, Semantic, Parent-Child |
| Embeddings | Multiple models (e.g. `local-charngram-384`) |
| Retrieval | BM25, Dense, Hybrid |
| Reranking | None, Cross-Encoder |

Pipelines are configured and saved from `/pipelines` (chunk size, top-K, model selection) and can be selected per-dataset ingestion or per-query in the Playground — e.g. `v1 · bm25/cross_encoder/openai/gpt-oss-20b`.

### Phase 3 — Evaluation Datasets
Ground-truth QA datasets are the backbone of objective evaluation. Each dataset entry stores:

```json
{
  "question": "What was revenue in 2024?",
  "ground_truth_answer": "...",
  "relevant_documents": ["doc_17"],
  "relevant_chunks": ["chunk_183"]
}
```

Built at `/evaluations/datasets` — create, edit, and manage question sets (e.g. a 12-question `Ritesh-AI-QA` set built against the ingested document) that later phases score pipelines against.

### Phase 4 — Evaluation Engine 🔥
The core intelligence layer. Runs a saved pipeline against a saved evaluation dataset and produces real, reproducible metrics — not vibes.

**Retrieval metrics:** Recall@K, Precision@K, Hit Rate, MRR, nDCG
**Generation metrics:** Correctness, Answer Relevance, Context Relevance, Faithfulness, Hallucination, Citation Precision, Citation Recall

Implemented as a mix of deterministic, reference-based scoring and LLM-as-a-judge scoring where deterministic methods fall short — with the explicit design principle that an LLM judge is a signal, not ground truth.

Live at `/evaluations`:
- Select a **pipeline** + **dataset**, run the evaluation, and get an aggregate scorecard (Correctness, Faithfulness, Recall@K, MRR, Hallucination) plus a full bar chart across all 11 metrics
- Drill into every individual question in the run — the model's answer, and a per-question breakdown of correctness, faithfulness, and citation scores — to see *exactly* where a pipeline is weak, not just its average

---

## What This Demonstrates

- Designing a RAG system as a **configurable, swappable pipeline** rather than a single hardcoded path
- Building **ground-truth evaluation infrastructure** before optimizing anything
- Implementing both **deterministic IR metrics** (Recall@K, MRR, nDCG) and **LLM-as-a-judge metrics** (faithfulness, hallucination, citation correctness), and understanding the tradeoffs between them
- Full-stack ownership: schema design, API design, ingestion pipeline, retrieval logic, evaluation scoring, and a dashboard that surfaces results at both the aggregate and per-question level

---

## Roadmap

Planned next, in priority order:

**🟧 Production differentiators**
- Phase 5 — Automated multi-configuration experiment engine
- Phase 6 — Side-by-side experiment comparison
- Phase 7–8 — Full request tracing & observability UI
- Phase 9 — Per-request RAG trace debugger
- Phase 10 — Automated failure classification (retrieval failure, hallucination, wrong answer, citation failure)
- Phase 11 — RAG/LLM-specific security testing (prompt injection, jailbreaks, PII/prompt leakage, RAG poisoning)
- Phase 12–13 — Cost tracking, exact/semantic caching, model routing

**🟨 Advanced**
- Phase 14 — RAG vs. long-context comparison
- Phase 15 — Automated Pareto-optimal pipeline recommendation

**🟩 Productization**
- Auth & RBAC, production hardening, test coverage, a published RAGOps benchmark (500 QA pairs across multiple configurations), and final UI polish

---

## Getting Started

```bash
# Backend
cd backend
uv sync
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Requires PostgreSQL, Qdrant, and Redis running locally (see `docker-compose.yml`).

---

## License

MIT
