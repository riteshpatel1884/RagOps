"""
Retrieval evaluation metrics, implemented from first principles (no eval
library) so you can explain exactly how each number is computed.

All functions take:
  retrieved_ids: List[str]   -- chunk ids returned by the retriever, ranked best-first
  relevant_ids:  Set[str]    -- chunk ids that are actually relevant (ground truth)
"""
import math
from typing import List, Sequence, Set


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Of all relevant chunks, what fraction did we retrieve in the top K?"""
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k & relevant_ids)
    return hits / len(relevant_ids)


def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Of the K chunks we retrieved, what fraction were actually relevant?"""
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return hits / len(top_k)


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Set[str]) -> float:
    """1 / rank of the first relevant chunk found (0 if none found)."""
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain with binary relevance.
    Rewards relevant chunks appearing earlier in the ranking.
    """
    top_k = retrieved_ids[:k]

    dcg = 0.0
    for i, cid in enumerate(top_k, start=1):
        rel = 1.0 if cid in relevant_ids else 0.0
        dcg += rel / math.log2(i + 1)

    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

    return dcg / idcg if idcg > 0 else 0.0


def first_relevant_rank(retrieved_ids: Sequence[str], relevant_ids: Set[str]) -> int:
    """Rank (1-indexed) of the first relevant chunk, or -1 if not found in the list."""
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in relevant_ids:
            return rank
    return -1


def aggregate_metrics(per_query_results: List[dict]) -> dict:
    """Average a list of per-query metric dicts into overall pipeline metrics."""
    keys = per_query_results[0].keys()
    return {k: sum(r[k] for r in per_query_results) / len(per_query_results) for k in keys}