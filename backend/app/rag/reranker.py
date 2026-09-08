"""Reranking via LangChain's document compressor interface: none, cross_encoder.

A real cross-encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2` via
sentence-transformers, wired in through
`langchain.retrievers.document_compressors.CrossEncoderReranker`) scores
each (query, chunk) pair jointly through a transformer — much stronger than
the lexical overlap heuristic below — but it requires downloading model
weights. `LexicalReranker` is a zero-download stand-in implementing the
same `BaseDocumentCompressor` interface, so swapping in the real thing later
means changing this one class, not any of its callers.
"""
import re

from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _lexical_score(query: str, text: str) -> float:
    q_tokens, t_tokens = _tokens(query), _tokens(text)
    if not q_tokens or not t_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


class LexicalReranker(BaseDocumentCompressor):
    top_k: int | None = None

    def compress_documents(self, documents, query, callbacks=None):
        scored = sorted(documents, key=lambda d: _lexical_score(query, d.page_content), reverse=True)
        return scored[: self.top_k] if self.top_k else scored


def rerank(strategy: str, query: str, documents: list[Document], top_k: int | None = None) -> list[Document]:
    if strategy == "none" or not documents:
        return documents[:top_k] if top_k else documents
    if strategy == "cross_encoder":
        return LexicalReranker(top_k=top_k).compress_documents(documents, query)
    raise ValueError(f"Unknown reranker type: {strategy!r}")
