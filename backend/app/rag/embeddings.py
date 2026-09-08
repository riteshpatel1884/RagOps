"""Embedding provider registry, exposed through LangChain's `Embeddings`
interface so they plug directly into langchain_qdrant.QdrantVectorStore and
langchain_experimental's SemanticChunker.

Phase 2 requires "at least 2 embedding models". Both shipped here are
zero-API-key, zero-download local embedders — deliberately different
algorithms so they actually behave differently (one is word-level TF-IDF,
the other character-n-gram hashing, which is more typo/morphology-robust
and worse at synonyms). Neither is a strong semantic embedding model.

Swap in a real provider (OpenAIEmbeddings from langchain-openai,
VoyageAIEmbeddings, HuggingFaceEmbeddings, etc.) by registering an instance
in EMBEDDINGS below — every consumer (vectorstore, semantic chunker,
retriever) already treats the embedding model as a named, swappable
LangChain Embeddings object.
"""
import numpy as np
from langchain_core.embeddings import Embeddings
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer


def _normalize(dense: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return dense / norms


class _LocalVectorizerEmbeddings(Embeddings):
    """Base class for our zero-download local embedders."""

    name: str
    dimensions: int

    def __init__(self, dimensions: int = 384, analyzer: str = "word", ngram_range: tuple = (1, 1)):
        self.dimensions = dimensions
        self._hasher = HashingVectorizer(
            n_features=dimensions,
            alternate_sign=False,
            norm=None,
            analyzer=analyzer,
            ngram_range=ngram_range,
        )
        self._tfidf = TfidfTransformer()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        counts = self._hasher.transform(texts)
        weighted = self._tfidf.fit_transform(counts)
        dense = _normalize(weighted.toarray().astype(np.float32))
        return dense.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class LocalTfidfEmbeddings(_LocalVectorizerEmbeddings):
    """Word-level hashing + TF-IDF re-weighting. Good at exact terminology
    overlap (product names, numbers, proper nouns)."""

    name = "local-tfidf-384"

    def __init__(self, dimensions: int = 384):
        super().__init__(dimensions=dimensions, analyzer="word")


class LocalCharNgramEmbeddings(_LocalVectorizerEmbeddings):
    """Character n-gram (3-5) hashing. More robust to typos, plurals, and
    morphological variation than the word-level embedder; weaker on
    synonyms."""

    name = "local-charngram-384"

    def __init__(self, dimensions: int = 384):
        super().__init__(dimensions=dimensions, analyzer="char_wb", ngram_range=(3, 5))


EMBEDDINGS: dict[str, Embeddings] = {
    "local-tfidf-384": LocalTfidfEmbeddings(),
    "local-charngram-384": LocalCharNgramEmbeddings(),
}

DEFAULT_EMBEDDING_MODEL = "local-tfidf-384"


def get_langchain_embeddings(name: str | None = None) -> Embeddings:
    name = name or DEFAULT_EMBEDDING_MODEL
    embeddings = EMBEDDINGS.get(name)
    if embeddings is None:
        raise ValueError(f"Unknown embedding model: {name!r}")
    return embeddings


def list_embedders() -> list[str]:
    return list(EMBEDDINGS.keys())


def get_dimensions(name: str) -> int:
    return get_langchain_embeddings(name).dimensions
