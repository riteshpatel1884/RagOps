"""Deterministic, reference-based metrics for Phase 4.

Retrieval metrics are graded against an EvalQuestion's ground truth: chunk
ids if the question specifies relevant_chunk_ids, else document ids from
relevant_document_ids. Generation metrics compare the generated answer
against ground_truth_answer, the question, and the retrieved context —
no LLM call required. See app/eval/judge.py for the one metric
(faithfulness) that optionally upgrades to an LLM-as-judge score.
"""
import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def token_f1(prediction: str, reference: str) -> float:
    """SQuAD-style token-overlap F1 between a generated answer and the
    ground-truth answer. 0 if either is empty or they share no tokens."""
    pred_tokens = _tokens(prediction)
    ref_tokens = _tokens(reference)
    if not pred_tokens or not ref_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(ref_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def _relevant_set(question) -> tuple[str, set[str]]:
    """('chunk', ids) if the question specifies relevant_chunk_ids, else
    ('document', ids) from relevant_document_ids."""
    if question.relevant_chunk_ids:
        return "chunk", set(question.relevant_chunk_ids)
    return "document", set(question.relevant_document_ids or [])


def _retrieved_ids(hits, level: str) -> list[str]:
    key = "chunk_id" if level == "chunk" else "document_id"
    return [h.metadata.get(key) for h in hits]


def retrieval_metrics(question, hits: list, k: int) -> dict:
    """Recall@K, Precision@K, Hit Rate, MRR, nDCG@K against ground truth.
    All are None (not 0) when the question has no labeled ground truth —
    that's "not evaluable", which is different from "scored zero"."""
    level, relevant = _relevant_set(question)
    raw_retrieved = _retrieved_ids(hits, level)[:k]

    # Multiple retrieved chunks often share the same parent document at the
    # "document" level (chunk-level ids are already unique). Precision/recall
    # count *distinct relevant items found*, not *matching chunks* — without
    # deduping, a document that dominates the top-k could push recall or
    # precision above 1.0, which isn't a meaningful IR score.
    seen = set()
    retrieved = []
    for rid in raw_retrieved:
        if rid not in seen:
            seen.add(rid)
            retrieved.append(rid)

    if not relevant:
        return {
            "level": level,
            "recall_at_k": None,
            "precision_at_k": None,
            "hit_rate": None,
            "mrr": None,
            "ndcg_at_k": None,
        }

    hit_flags = [1 if rid in relevant else 0 for rid in retrieved]
    num_relevant_retrieved = sum(hit_flags)

    precision = num_relevant_retrieved / k if k else 0.0
    recall = num_relevant_retrieved / len(relevant)
    hit_rate = 1.0 if num_relevant_retrieved > 0 else 0.0

    rr = 0.0
    for i, flag in enumerate(hit_flags, start=1):
        if flag:
            rr = 1.0 / i
            break

    dcg = sum(flag / math.log2(i + 1) for i, flag in enumerate(hit_flags, start=1))
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return {
        "level": level,
        "recall_at_k": recall,
        "precision_at_k": precision,
        "hit_rate": hit_rate,
        "mrr": rr,
        "ndcg_at_k": ndcg,
    }