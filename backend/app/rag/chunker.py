"""Phase 2: four chunking strategies behind one dispatcher.

fixed         - naive character-width cuts, cheapest, worst boundaries.
recursive     - split on paragraph -> sentence -> word until pieces fit
                chunk_size (Phase 1's original strategy).
semantic      - group consecutive sentences while they stay semantically
                similar (cosine similarity over sentence embeddings);
                breaks when topic drifts or the size cap is hit.
parent_child  - small "child" chunks are what gets embedded/retrieved for
                precision, but each child carries a larger "parent" chunk
                of surrounding text that's what actually gets sent to the
                LLM as context, for recall.
"""
import re
from dataclasses import dataclass

from app.rag.parser import ParsedPage

_SEPARATORS = ["\n\n", "\n", ". ", " "]
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    text: str
    page_number: int
    chunk_index: int
    parent_text: str | None = None  # set only by parent_child strategy


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    if not separators:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep, rest = separators[0], separators[1:]
    parts = text.split(sep)
    pieces: list[str] = []
    buffer = ""
    for part in parts:
        candidate = (buffer + sep + part) if buffer else part
        if len(candidate) <= chunk_size:
            buffer = candidate
        else:
            if buffer:
                pieces.append(buffer)
            if len(part) > chunk_size:
                pieces.extend(_split(part, rest, chunk_size))
                buffer = ""
            else:
                buffer = part
    if buffer:
        pieces.append(buffer)
    return pieces


def _with_overlap(pieces: list[str], chunk_overlap: int) -> list[str]:
    if chunk_overlap <= 0:
        return pieces
    out = []
    for i, piece in enumerate(pieces):
        if i > 0:
            prev_tail = pieces[i - 1][-chunk_overlap:]
            piece = prev_tail + " " + piece
        out.append(piece.strip())
    return out


# ---------------------------------------------------------------- fixed ----


def fixed_chunk(pages: list[ParsedPage], chunk_size: int = 512, chunk_overlap: int = 64) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for page in pages:
        text = _clean(page.text)
        raw = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]
        for piece in _with_overlap(raw, chunk_overlap):
            chunks.append(Chunk(text=piece, page_number=page.page_number, chunk_index=idx))
            idx += 1
    return chunks


# -------------------------------------------------------------- recursive --


def recursive_chunk(
    pages: list[ParsedPage], chunk_size: int = 512, chunk_overlap: int = 64
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for page in pages:
        raw_pieces = _split(_clean(page.text), _SEPARATORS, chunk_size)
        for piece in _with_overlap(raw_pieces, chunk_overlap):
            chunks.append(Chunk(text=piece, page_number=page.page_number, chunk_index=idx))
            idx += 1
    return chunks


# --------------------------------------------------------------- semantic --


def semantic_chunk(
    pages: list[ParsedPage],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    similarity_threshold: float = 0.15,
) -> list[Chunk]:
    # Local import avoids a hard circular dependency at module load time.
    from app.rag.embeddings import get_embedder
    import numpy as np

    embedder = get_embedder("local-tfidf-384")
    chunks: list[Chunk] = []
    idx = 0

    for page in pages:
        sentences = [s for s in _SENTENCE_SPLIT.split(_clean(page.text)) if s]
        if not sentences:
            continue
        if len(sentences) == 1:
            chunks.append(Chunk(text=sentences[0], page_number=page.page_number, chunk_index=idx))
            idx += 1
            continue

        vectors = np.array(embedder.embed(sentences))
        groups: list[list[str]] = [[sentences[0]]]
        group_len = len(sentences[0])

        for i in range(1, len(sentences)):
            sim = float(vectors[i] @ vectors[i - 1])  # already L2-normalized
            candidate_len = group_len + 1 + len(sentences[i])
            if sim < similarity_threshold or candidate_len > chunk_size:
                groups.append([sentences[i]])
                group_len = len(sentences[i])
            else:
                groups[-1].append(sentences[i])
                group_len = candidate_len

        raw_pieces = [" ".join(g) for g in groups]
        for piece in _with_overlap(raw_pieces, chunk_overlap):
            chunks.append(Chunk(text=piece, page_number=page.page_number, chunk_index=idx))
            idx += 1

    return chunks


# ----------------------------------------------------------- parent_child --


def parent_child_chunk(
    pages: list[ParsedPage], chunk_size: int = 512, chunk_overlap: int = 64
) -> list[Chunk]:
    parent_size = chunk_size * 4
    chunks: list[Chunk] = []
    idx = 0
    for page in pages:
        text = _clean(page.text)
        parents = _split(text, _SEPARATORS, parent_size)
        for parent in parents:
            children = _with_overlap(_split(parent, _SEPARATORS, chunk_size), chunk_overlap)
            for child in children:
                chunks.append(
                    Chunk(
                        text=child,
                        page_number=page.page_number,
                        chunk_index=idx,
                        parent_text=parent.strip(),
                    )
                )
                idx += 1
    return chunks


CHUNKING_STRATEGIES = {
    "fixed": fixed_chunk,
    "recursive": recursive_chunk,
    "semantic": semantic_chunk,
    "parent_child": parent_child_chunk,
}


def chunk_document(
    strategy: str, pages: list[ParsedPage], chunk_size: int = 512, chunk_overlap: int = 64
) -> list[Chunk]:
    fn = CHUNKING_STRATEGIES.get(strategy)
    if fn is None:
        raise ValueError(f"Unknown chunking strategy: {strategy!r}")
    return fn(pages, chunk_size, chunk_overlap)
