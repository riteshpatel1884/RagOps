"""Phase 2 retrieval strategies via LangChain retrievers: bm25, dense, hybrid.

BM25Retriever's in-memory index is rebuilt from Postgres on every query —
fine at demo/portfolio scale (hundreds to low-thousands of chunks). At real
scale you'd persist an inverted index instead of rebuilding it per request.
"""
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.models.document import Chunk
from app.models.document import Document as DocumentModel
from app.rag import vectorstore


def _chunk_documents(db: Session, document_id: str | None = None) -> list[Document]:
    q = db.query(Chunk, DocumentModel).join(DocumentModel, Chunk.document_id == DocumentModel.id)
    if document_id:
        q = q.filter(Chunk.document_id == document_id)
    rows = q.all()
    return [
        Document(
            page_content=chunk.text,
            metadata={
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "filename": doc.filename,
                "page_number": chunk.page_number,
                "parent_text": chunk.parent_text,
            },
        )
        for chunk, doc in rows
    ]


def bm25_search(db: Session, query: str, top_k: int = 5, document_id: str | None = None) -> list[Document]:
    docs = _chunk_documents(db, document_id)
    if not docs:
        return []
    retriever = BM25Retriever.from_documents(docs)
    retriever.k = top_k
    return retriever.invoke(query)


def dense_search(
    query: str, embedding_model: str, top_k: int = 5, document_id: str | None = None
) -> list[Document]:
    search_kwargs = {"k": top_k}
    if document_id:
        search_kwargs["filter"] = vectorstore.document_id_filter(document_id)
    retriever = vectorstore.get_store(embedding_model).as_retriever(search_kwargs=search_kwargs)
    return retriever.invoke(query)


def hybrid_search(
    db: Session,
    query: str,
    embedding_model: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[Document]:
    """LangChain's EnsembleRetriever combines rankers via Reciprocal Rank
    Fusion — a standard way to merge differently-scaled rankers (lexical
    BM25 vs. dense cosine similarity) without normalizing raw scores."""
    bm25_docs = _chunk_documents(db, document_id)
    if not bm25_docs:
        return dense_search(query, embedding_model, top_k, document_id)

    bm25_retriever = BM25Retriever.from_documents(bm25_docs)
    bm25_retriever.k = top_k

    search_kwargs = {"k": top_k}
    if document_id:
        search_kwargs["filter"] = vectorstore.document_id_filter(document_id)
    dense_retriever = vectorstore.get_store(embedding_model).as_retriever(search_kwargs=search_kwargs)

    ensemble = EnsembleRetriever(retrievers=[bm25_retriever, dense_retriever], weights=[0.5, 0.5])
    return ensemble.invoke(query)[:top_k]


def retrieve(
    strategy: str,
    db: Session,
    query: str,
    embedding_model: str,
    top_k: int = 5,
    document_id: str | None = None,
) -> list[Document]:
    if strategy == "bm25":
        return bm25_search(db, query, top_k=top_k, document_id=document_id)
    if strategy == "dense":
        return dense_search(query, embedding_model, top_k=top_k, document_id=document_id)
    if strategy == "hybrid":
        return hybrid_search(db, query, embedding_model, top_k=top_k, document_id=document_id)
    raise ValueError(f"Unknown retriever type: {strategy!r}")
