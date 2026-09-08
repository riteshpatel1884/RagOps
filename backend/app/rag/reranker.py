"""Phase 2 reranking strategies: none, cross_encoder.

A real cross-encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2` via
sentence-transformers) scores each (query, chunk) pair jointly through a
transformer, which is much stronger than the lexical overlap heuristic
below — but it requires downloading model weights. `LexicalReranker` is a
zero-download stand-in with the same interface (rescore + reorder the top
candidates) so the pipeline builder has something real to switch between.
Swap `_lexical_score` for an actual CrossEncoder(...).predict() call when
you have model access.
"""
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _lexical_score(query: str, text: str) -> float:
    q_tokens, t_tokens = _tokens(query), _tokens(text)
    if not q_tokens or not t_tokens:
        return 0.0
    overlap = len(q_tokens & t_tokens)
    return overlap / len(q_tokens)  # fraction of query terms present in the chunk


def rerank(strategy: str, query: str, hits: list[dict], top_k: int | None = None) -> list[dict]:
    if strategy == "none" or not hits:
        return hits[:top_k] if top_k else hits

    if strategy == "cross_encoder":
        rescored = [
            {**hit, "rerank_score": _lexical_score(query, hit["text"])} for hit in hits
        ]
        rescored.sort(key=lambda h: h["rerank_score"], reverse=True)
        return rescored[:top_k] if top_k else rescored

    raise ValueError(f"Unknown reranker type: {strategy!r}")
