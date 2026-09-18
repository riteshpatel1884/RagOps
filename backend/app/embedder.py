"""
Embedding layer, built entirely on LangChain's `Embeddings` interface
(langchain_core.embeddings.Embeddings) — no scikit-learn anywhere.

Two implementations:

1. HashingEmbeddings (default here) — a from-scratch, fully offline
   implementation of the "hashing trick" (feature hashing) over word
   n-grams: no library dependency at all, not even sklearn. Used as the
   default because this sandbox's network policy blocks the model
   downloads / API calls that real embedding models need.

2. Real production embedding models, wired through LangChain's own
   integration packages — pick whichever you have credentials/network
   for, via `get_embedder(name=...)`:
     - "openai"       -> langchain_openai.OpenAIEmbeddings
     - "huggingface"   -> langchain_huggingface.HuggingFaceEmbeddings
   The rest of the pipeline (chunking, Qdrant store, metrics) is
   unchanged either way — that's the point of coding to LangChain's
   Embeddings interface instead of any one provider's SDK.
"""
import hashlib
import re
from typing import List, Tuple
import numpy as np
from langchain_core.embeddings import Embeddings


class HashingEmbeddings(Embeddings):
    """
    Offline, dependency-free embedding using feature hashing over word
    1- and 2-grams, L2-normalized. This is a legitimate (if weaker than
    neural) sparse retrieval baseline — the hashing trick is a real
    technique used in large-scale search, not a toy.
    """

    name = "hashing (offline)"

    def __init__(self, n_features: int = 512, ngram_range: Tuple[int, int] = (1, 2)):
        self.n_features = n_features
        self.ngram_range = ngram_range

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"[a-z0-9]+", text.lower())
        tokens = []
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(words) - n + 1):
                tokens.append(" ".join(words[i : i + n]))
        return tokens

    def _hash_vector(self, text: str) -> List[float]:
        vec = np.zeros(self.n_features, dtype="float32")
        for tok in self._tokenize(text):
            digest = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = digest % self.n_features
            sign = 1.0 if (digest // self.n_features) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    # --- LangChain Embeddings interface ---
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_vector(text)


def get_embedder(name: str = "hashing", **kwargs) -> Embeddings:
    """Factory so pipeline configs can select an embedding model by name."""
    if name in ("hashing", "offline", "default"):
        return HashingEmbeddings(**kwargs)

    if name == "openai":
        from langchain_openai import OpenAIEmbeddings  # requires OPENAI_API_KEY + network
        return OpenAIEmbeddings(**kwargs)

    if name in ("huggingface", "hf", "sentence-transformers"):
        from langchain_huggingface import HuggingFaceEmbeddings  # requires network to download weights
        kwargs.setdefault("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(**kwargs)

    raise ValueError(f"Unknown embedder: {name}")