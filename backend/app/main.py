from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import datasets, health, pipelines, playground
from app.db.session import Base, SessionLocal, engine
from app.models import document, pipeline as pipeline_model  # noqa: F401 (registers models on Base)

Base.metadata.create_all(bind=engine)


def _seed_default_pipeline():
    from app.models.pipeline import Pipeline

    db = SessionLocal()
    try:
        if db.query(Pipeline).count() == 0:
            db.add(
                Pipeline(
                    name="Default Pipeline",
                    chunking_strategy="recursive",
                    chunk_size=512,
                    chunk_overlap=64,
                    embedding_model="local-tfidf-384",
                    retriever_type="hybrid",
                    reranker_type="none",
                    llm_model="claude-sonnet-4-6",
                    top_k=5,
                )
            )
            db.commit()
    finally:
        db.close()


_seed_default_pipeline()

app = FastAPI(title="RAGOps API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(playground.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
