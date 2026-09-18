"""
Generation evaluation: given (question, retrieved context, generated answer),
score whether the LLM actually used the context correctly.

Two metrics, each with an offline default and an LLM-as-judge production
option — same pattern as the rest of this project:

1. Faithfulness — does the answer only contain claims supported by the
   retrieved context? Offline default: lexical overlap between the answer's
   content words and the context (a real, if crude, attribution proxy).
   Production option: prompt an LLM judge with a strict rubric.

2. Answer relevance — does the answer actually address the question?
   Offline default: embedding cosine similarity between question and
   answer (reuses whatever Embeddings instance the retrieval pipeline is
   already using — no extra dependency). Production option: LLM judge.

IMPORTANT: LLM-as-judge metrics are known to be noisy and biased toward
whatever model is judging. Before trusting one in a real project, validate
it against a small hand-labeled set (see evaluate_generation.py) and be
ready to talk about where it disagrees with humans.
"""
import re
from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate

# True function/discourse words (don't carry factual claims) plus common
# "talking about the context" meta-words the LLM adds when hedging or
# refusing to answer (e.g. "the provided context does not specify...").
# These were previously miscounted as "unsupported facts" when they're
# really just connective or self-referential language, not hallucinated
# content.
STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "of", "to", "in", "for", "on", "and", "or",
    "what", "how", "can", "many", "much", "i", "my", "will", "be", "am", "not", "this", "that",
    "yes", "no", "you", "your", "they", "their", "but", "only", "may", "might", "provided",
    "context", "specify", "specified", "states", "stated", "mentioned", "document", "text",
    "according", "based",
}


def _stem(word: str) -> str:
    """
    Very small rule-based stemmer (not a real Porter stemmer) so morphological
    variants match across answer and context — e.g. "incurring" vs "incurred",
    "receives" vs "receive", "events" vs "event". Good enough for this
    lexical-overlap proxy without adding an NLP dependency.
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) > 2:
            return word[: -len(suffix)]
    return word


def _content_words(text: str) -> dict:
    """Returns {stem: original_word} for content words, so callers can match
    on stems (robust to morphology) while still reporting the original word."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    result = {}
    for w in words:
        if w in STOPWORDS or len(w) <= 2:
            continue
        result[_stem(w)] = w
    return result


# ---------------------------------------------------------------------------
# Faithfulness
# ---------------------------------------------------------------------------

class BaseFaithfulnessEvaluator(ABC):
    name: str = "base"

    @abstractmethod
    def score(self, answer: str, context: List[str]) -> dict:
        """Return {"faithfulness": float in [0,1], "explanation": str}."""


class LexicalOverlapFaithfulness(BaseFaithfulnessEvaluator):
    """
    Offline proxy: fraction of the answer's content words that also appear
    somewhere in the retrieved context. Doesn't catch subtle contradictions
    or numeric errors, but catches the common failure mode of an LLM adding
    facts that aren't in the context at all.
    """

    name = "lexical-overlap (offline)"

    def score(self, answer: str, context: List[str]) -> dict:
        answer_words = _content_words(answer)      # {stem: original_word}
        context_words = _content_words(" ".join(context))

        if not answer_words:
            return {"faithfulness": 0.0, "explanation": "Answer had no scorable content words."}

        answer_stems = set(answer_words.keys())
        context_stems = set(context_words.keys())

        supported_stems = answer_stems & context_stems
        unsupported_stems = answer_stems - context_stems
        faithfulness = len(supported_stems) / len(answer_stems)

        # Report the original (unstemmed) words for readability.
        unsupported_words = sorted(answer_words[s] for s in unsupported_stems)

        explanation = f"{len(supported_stems)}/{len(answer_stems)} content words found in context."
        if unsupported_words:
            explanation += f" Unsupported terms: {', '.join(unsupported_words[:6])}"

        return {"faithfulness": faithfulness, "explanation": explanation}


class LLMJudgeFaithfulness(BaseFaithfulnessEvaluator):
    """Production option: ask an LLM to judge faithfulness against a strict rubric."""

    name = "llm-judge"

    PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict fact-checker. Given a CONTEXT and an ANSWER, determine "
                "whether every claim in the ANSWER is directly supported by the CONTEXT. "
                "Respond with exactly two lines:\n"
                "SCORE: <a number between 0.0 and 1.0>\n"
                "REASON: <one sentence explanation>",
            ),
            ("human", "CONTEXT:\n{context}\n\nANSWER:\n{answer}"),
        ]
    )

    def __init__(self, chat_model):
        self.chain = self.PROMPT | chat_model

    def score(self, answer: str, context: List[str]) -> dict:
        response = self.chain.invoke({"context": "\n\n".join(context), "answer": answer}).content
        score_match = re.search(r"SCORE:\s*([0-9.]+)", response)
        reason_match = re.search(r"REASON:\s*(.+)", response)
        return {
            "faithfulness": float(score_match.group(1)) if score_match else 0.0,
            "explanation": reason_match.group(1).strip() if reason_match else response.strip(),
        }


# ---------------------------------------------------------------------------
# Answer relevance
# ---------------------------------------------------------------------------

class BaseRelevanceEvaluator(ABC):
    name: str = "base"

    @abstractmethod
    def score(self, question: str, answer: str) -> dict:
        """Return {"relevance": float in [0,1], "explanation": str}."""


class EmbeddingSimilarityRelevance(BaseRelevanceEvaluator):
    """
    Offline default: cosine similarity between the question's and answer's
    embeddings, using whatever Embeddings instance the pipeline already has
    (e.g. the same HashingEmbeddings from Phase 1 — no new dependency).
    """

    name = "embedding-similarity (offline)"

    def __init__(self, embedding: Embeddings):
        self.embedding = embedding

    def score(self, question: str, answer: str) -> dict:
        q_vec = np.array(self.embedding.embed_query(question))
        a_vec = np.array(self.embedding.embed_query(answer))

        q_norm, a_norm = np.linalg.norm(q_vec), np.linalg.norm(a_vec)
        if q_norm == 0 or a_norm == 0:
            return {"relevance": 0.0, "explanation": "Empty embedding for question or answer."}

        cosine = float(np.dot(q_vec, a_vec) / (q_norm * a_norm))
        relevance = max(0.0, cosine)  # clip negative cosine to 0 for readability
        return {"relevance": relevance, "explanation": f"Cosine similarity: {cosine:.3f}"}


class LLMJudgeRelevance(BaseRelevanceEvaluator):
    """Production option: ask an LLM to judge whether the answer addresses the question."""

    name = "llm-judge"

    PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You judge whether an ANSWER actually addresses the QUESTION asked "
                "(regardless of whether it's factually correct). Respond with exactly "
                "two lines:\nSCORE: <a number between 0.0 and 1.0>\nREASON: <one sentence>",
            ),
            ("human", "QUESTION: {question}\n\nANSWER: {answer}"),
        ]
    )

    def __init__(self, chat_model):
        self.chain = self.PROMPT | chat_model

    def score(self, question: str, answer: str) -> dict:
        response = self.chain.invoke({"question": question, "answer": answer}).content
        score_match = re.search(r"SCORE:\s*([0-9.]+)", response)
        reason_match = re.search(r"REASON:\s*(.+)", response)
        return {
            "relevance": float(score_match.group(1)) if score_match else 0.0,
            "explanation": reason_match.group(1).strip() if reason_match else response.strip(),
        }