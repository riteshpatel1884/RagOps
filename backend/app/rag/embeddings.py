"""Embedding provider registry.

Phase 2 requires "at least 2 embedding models" so pipelines have something
real to choose between. Both shipped here are zero-API-key, zero-download
local embedders — deliberately different algorithms so they actually behave
differently (one is word-level TF-IDF, the other is character-n-gram
hashing, which is more typo/morphology-robust and worse at synonyms).

Neither is a strong semantic embedding model. They exist so the full
pipeline (chunk -> embed -> index -> retrieve -> generate) runs end-to-end
with no external dependency. Swap in a real provider (OpenAI
`text-embedding-3-small`, Voyage, Cohere, or a downloaded
sentence-transformers model) by adding a class to EMBEDDERS below — the
rest of the app (vectorstore, retriever, pipeline builder) already treats
the embedding model as a named, swappable choice.
"""
from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer


class Embedder(ABC):
    name: str
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _normalize(dense: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return dense / norms


class LocalTfidfEmbedder(Embedder):
    """Word-level hashing + TF-IDF re-weighting. Good at exact terminology
    overlap (product names, numbers, proper nouns) — the kind of thing
    finance/legal QA leans on."""

    name = "local-tfidf-384"
    dimensions = 384

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions
        self._hasher = HashingVectorizer(n_features=dimensions, alternate_sign=False, norm=None)
        self._tfidf = TfidfTransformer()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        counts = self._hasher.transform(texts)
        weighted = self._tfidf.fit_transform(counts)
        dense = _normalize(weighted.toarray().astype(np.float32))
        return dense.tolist()


class LocalCharNgramEmbedder(Embedder):
    """Character n-gram (3-5) hashing. More robust to typos, plurals, and
    morphological variation than the word-level embedder; weaker on
    synonyms. Included specifically so Phase 2's retriever/reranker code
    has to deal with genuinely different embedding spaces, not two
    thin wrappers around the same vectors."""

    name = "local-charngram-384"
    dimensions = 384

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions
        self._hasher = HashingVectorizer(
            n_features=dimensions,
            alternate_sign=False,
            norm=None,
            analyzer="char_wb",
            ngram_range=(3, 5),
        )
        self._tfidf = TfidfTransformer()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        counts = self._hasher.transform(texts)
        weighted = self._tfidf.fit_transform(counts)
        dense = _normalize(weighted.toarray().astype(np.float32))
        return dense.tolist()


EMBEDDERS: dict[str, Embedder] = {
    "local-tfidf-384": LocalTfidfEmbedder(),
    "local-charngram-384": LocalCharNgramEmbedder(),
}

DEFAULT_EMBEDDER = "local-tfidf-384"


def get_embedder(name: str | None = None) -> Embedder:
    name = name or DEFAULT_EMBEDDER
    embedder = EMBEDDERS.get(name)
    if embedder is None:
        raise ValueError(f"Unknown embedding model: {name!r}")
    return embedder


def list_embedders() -> list[str]:
    return list(EMBEDDERS.keys())
