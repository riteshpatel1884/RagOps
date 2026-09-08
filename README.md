# RAGOps — Phase 0 & 1

Production RAG evaluation, observability & optimization platform.
This slice covers **Phase 0 (architecture + shell)** and **Phase 1 (one working
end-to-end RAG pipeline)** from the full roadmap.

```
Document → Parser → Chunking → Embedding → Qdrant → Retriever → LLM → Answer + Sources
```

## What actually works right now

- Upload a PDF in **Datasets** → it's parsed, chunked (recursive strategy),
  embedded, and indexed automatically in the background.
- Ask a question in **Playground** → real retrieval against the index, real
  citations, and a generated answer (via the Anthropic API).
- Everything else in the sidebar (Pipelines, Experiments, Evaluation, Traces,
  Security, Optimization, Settings) is a labeled placeholder — those are
  later phases, not missing features of this phase.

## Two things worth knowing before you run it

1. **Embeddings are a placeholder.** `app/rag/embeddings.py` ships a
   deterministic hashing/TF-IDF embedder so the whole pipeline runs with zero
   API keys and zero model downloads. It is *not* a real semantic embedding
   model — swap in OpenAI/Voyage/sentence-transformers before you trust any
   retrieval numbers. The interface is already pluggable (`Embedder` ABC) so
   this is a one-file change when you get to Phase 2 ("at least 2 embedding
   models").
2. **Qdrant runs embedded** (file-backed, via `QDRANT_PATH`), not as a
   server — no Docker needed for Phase 0/1. `docker-compose.yml` has a
   commented-out Qdrant service for when you move to Phase 17.

## Run it

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY

docker compose -f ../docker-compose.yml up -d postgres   # or point DATABASE_URL at your own Postgres

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — it proxies `/api/*` to the backend on `:8000`
(see `next.config.js`).

## Layout

```
backend/
  app/
    api/routes/      # health, datasets (upload/list), playground (ask)
    core/             # settings
    db/               # SQLAlchemy session
    models/            # Document, Chunk
    rag/               # parser, chunker, embeddings, vectorstore, pipeline
    services/          # LLM generation (Anthropic)
frontend/
  app/                 # one route per sidebar item; dashboard/datasets/playground are live
  components/          # Sidebar, PhasePlaceholder
  lib/api.js             # fetch wrapper around the backend
docker-compose.yml      # postgres + redis (qdrant commented out until Phase 17)
```

## Next up: Phase 2

Turn the hardcoded chunking/embedding/retriever choices in
`app/rag/pipeline.py` into saved, comparable `Pipeline` configs, and add a
second real embedding model.
