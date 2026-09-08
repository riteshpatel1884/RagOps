"""Phase 2 (LangChain-backed) pipeline orchestration.

Document -> PyPDFLoader -> TextSplitter(config) -> Embeddings(config, all models) -> QdrantVectorStore
Question -> Retriever(config) -> DocumentCompressor(config) -> ChatGroq(config) -> Answer + Sources

Ingestion embeds every document into every registered embedding model's
collection, so a saved pipeline can pick any embedding model without
re-uploading documents. Chunking, on the other hand, physically changes chunk
boundaries — so it's fixed at upload time by whichever pipeline you pick in
the Datasets upload dialog. Phase 5's Experiment Engine is what runs the
same document through every chunking strategy automatically for comparison.
"""
from langchain_core.documents import Document as LCDocument
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Chunk as ChunkModel
from app.models.document import Document as DocumentModel
from app.models.pipeline import Pipeline
from app.rag import retriever, vectorstore
from app.rag.chunker import chunk_document
from app.rag.embeddings import EMBEDDINGS
from app.rag.reranker import rerank
from app.services.llm import generate_answer

settings = get_settings()


def ingest_document(
    db: Session, document: DocumentModel, file_path: str, pipeline: Pipeline
) -> None:
    """Parse -> chunk (per pipeline config) -> embed (all models) -> index."""
    from app.rag.parser import parse_pdf

    try:
        pages = parse_pdf(file_path)
        lc_chunks = chunk_document(
            pipeline.chunking_strategy, pages, pipeline.chunk_size, pipeline.chunk_overlap
        )

        if not lc_chunks:
            document.status = "failed"
            db.commit()
            return

        db_chunks = [
            ChunkModel(
                document_id=document.id,
                text=c.page_content,
                page_number=c.metadata.get("page_number", 0),
                chunk_index=c.metadata.get("chunk_index", i),
                parent_text=c.metadata.get("parent_text"),
            )
            for i, c in enumerate(lc_chunks)
        ]
        db.add_all(db_chunks)
        db.flush()  # assigns ids without committing yet

        index_docs = [
            LCDocument(
                page_content=c.text,
                metadata={
                    "document_id": document.id,
                    "filename": document.filename,
                    "page_number": c.page_number,
                    "parent_text": c.parent_text,
                    "chunk_id": c.id,
                },
            )
            for c in db_chunks
        ]
        chunk_ids = [c.id for c in db_chunks]

        # Index into every embedding model's collection so any saved
        # pipeline can query with any embedding model against this document.
        for embedder_name in EMBEDDINGS:
            vectorstore.add_documents(embedder_name, index_docs, chunk_ids)

        document.status = "ready"
        document.page_count = len(pages)
        db.commit()
    except Exception:
        document.status = "failed"
        db.commit()
        raise


def ask(db: Session, question: str, pipeline: Pipeline) -> dict:
    """Retriever(config) -> Reranker(config) -> ChatGroq(config) -> Answer + Sources."""
    fetch_k = pipeline.top_k * 2 if pipeline.reranker_type != "none" else pipeline.top_k
    hits = retriever.retrieve(
        pipeline.retriever_type, db, question, pipeline.embedding_model, top_k=fetch_k
    )
    hits = rerank(pipeline.reranker_type, question, hits, top_k=pipeline.top_k)
    answer = generate_answer(question, hits, model=pipeline.llm_model)

    return {
        "answer": answer,
        "pipeline": pipeline.name,
        "sources": [
            {
                "filename": h.metadata.get("filename"),
                "page_number": h.metadata.get("page_number"),
                # Rank-based, not a raw similarity number: BM25, cosine, and
                # RRF-fused scores live on different scales, so a comparable
                # display value is each hit's position in the final ranking.
                "score": round(1 / (i + 1), 4),
                "text": h.page_content,
            }
            for i, h in enumerate(hits)
        ],
    }
