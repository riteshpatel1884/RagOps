"""Phase 2: pipeline configs are now real inputs, not hardcoded constants.

Document -> Parser -> Chunking(config) -> Embedding(config, all models) -> Qdrant
Question -> Retriever(config) -> Reranker(config) -> LLM(config) -> Answer + Sources

Ingestion embeds every document into every registered embedding model's
collection, so a saved pipeline can pick any embedding model without
re-uploading documents. Chunking, on the other hand, physically changes chunk
boundaries — so it's fixed at upload time by whichever pipeline you pick in
the Datasets upload dialog. Phase 5's Experiment Engine is what runs the
same document through every chunking strategy automatically for comparison.
"""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Chunk as ChunkModel
from app.models.document import Document
from app.models.pipeline import Pipeline
from app.rag import retriever, vectorstore
from app.rag.chunker import chunk_document
from app.rag.embeddings import EMBEDDERS
from app.rag.reranker import rerank
from app.services.llm import generate_answer

settings = get_settings()


def ingest_document(db: Session, document: Document, file_path: str, pipeline: Pipeline) -> None:
    """Parse -> chunk (per pipeline config) -> embed (all models) -> index."""
    from app.rag.parser import parse_pdf

    try:
        pages = parse_pdf(file_path)
        chunks = chunk_document(
            pipeline.chunking_strategy, pages, pipeline.chunk_size, pipeline.chunk_overlap
        )

        if not chunks:
            document.status = "failed"
            db.commit()
            return

        db_chunks = [
            ChunkModel(
                document_id=document.id,
                text=c.text,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                parent_text=c.parent_text,
            )
            for c in chunks
        ]
        db.add_all(db_chunks)
        db.flush()  # assigns ids without committing yet

        texts = [c.text for c in db_chunks]
        payloads = [
            {
                "text": c.text,
                "document_id": document.id,
                "filename": document.filename,
                "page_number": c.page_number,
                "parent_text": c.parent_text,
            }
            for c in db_chunks
        ]
        chunk_ids = [c.id for c in db_chunks]

        # Index into every embedding model's collection so any saved
        # pipeline can query with any embedding model against this document.
        for embedder_name, embedder in EMBEDDERS.items():
            vectors = embedder.embed(texts)
            vectorstore.ensure_collection(embedder_name, embedder.dimensions)
            vectorstore.upsert_chunks(embedder_name, chunk_ids, vectors, payloads)

        document.status = "ready"
        document.page_count = len(pages)
        db.commit()
    except Exception:
        document.status = "failed"
        db.commit()
        raise


def ask(db: Session, question: str, pipeline: Pipeline) -> dict:
    """Retriever(config) -> Reranker(config) -> LLM(config) -> Answer + Sources."""
    hits = retriever.retrieve(
        pipeline.retriever_type,
        db,
        question,
        pipeline.embedding_model,
        top_k=pipeline.top_k * 2 if pipeline.reranker_type != "none" else pipeline.top_k,
    )
    hits = rerank(pipeline.reranker_type, question, hits, top_k=pipeline.top_k)
    answer = generate_answer(question, hits, model=pipeline.llm_model)
    return {
        "answer": answer,
        "pipeline": pipeline.name,
        "sources": [
            {
                "filename": h["filename"],
                "page_number": h["page_number"],
                "score": round(h["score"], 4),
                "text": h["text"],
            }
            for h in hits
        ],
    }
