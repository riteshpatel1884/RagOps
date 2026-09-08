"""Phase 2 chunking strategies, built on LangChain's text splitters.

fixed         - langchain_text_splitters.CharacterTextSplitter with an empty
                separator: naive character-width cuts, cheapest, worst
                boundaries.
recursive     - RecursiveCharacterTextSplitter: splits on paragraph -> line
                -> sentence -> word until pieces fit chunk_size.
semantic      - langchain_experimental's SemanticChunker: groups sentences
                while consecutive-sentence embedding similarity stays high,
                breaking at topic shifts. Uses whichever embedding model is
                registered as the default in app/rag/embeddings.py.
parent_child  - small "child" chunks (RecursiveCharacterTextSplitter at
                chunk_size) are what gets embedded/retrieved for precision;
                each child's metadata carries the larger "parent" chunk
                (chunk_size * 4) it came from, which is what actually gets
                sent to the LLM as context, for recall.
"""
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


def _pieces_to_chunks(pages: list[Document], pieces_per_page: list[list[str]]) -> list[Document]:
    chunks: list[Document] = []
    idx = 0
    for page, pieces in zip(pages, pieces_per_page):
        for piece in pieces:
            if not piece.strip():
                continue  # some splitters (e.g. SemanticChunker) can emit trailing empty pieces
            chunks.append(
                Document(
                    page_content=piece,
                    metadata={"page_number": page.metadata["page_number"], "chunk_index": idx},
                )
            )
            idx += 1
    return chunks


def fixed_chunk(pages: list[Document], chunk_size: int = 512, chunk_overlap: int = 64) -> list[Document]:
    splitter = CharacterTextSplitter(separator="", chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pieces_per_page = [splitter.split_text(p.page_content) for p in pages]
    return _pieces_to_chunks(pages, pieces_per_page)


def recursive_chunk(pages: list[Document], chunk_size: int = 512, chunk_overlap: int = 64) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pieces_per_page = [splitter.split_text(p.page_content) for p in pages]
    return _pieces_to_chunks(pages, pieces_per_page)


def semantic_chunk(pages: list[Document], chunk_size: int = 512, chunk_overlap: int = 64) -> list[Document]:
    # Local import avoids a hard circular dependency at module load time.
    from langchain_experimental.text_splitter import SemanticChunker

    from app.rag.embeddings import get_langchain_embeddings

    splitter = SemanticChunker(get_langchain_embeddings())
    pieces_per_page = [splitter.split_text(p.page_content) for p in pages]
    return _pieces_to_chunks(pages, pieces_per_page)


def parent_child_chunk(pages: list[Document], chunk_size: int = 512, chunk_overlap: int = 64) -> list[Document]:
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size * 4, chunk_overlap=chunk_overlap)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks: list[Document] = []
    idx = 0
    for page in pages:
        for parent_text in parent_splitter.split_text(page.page_content):
            for child_text in child_splitter.split_text(parent_text):
                if not child_text.strip():
                    continue
                chunks.append(
                    Document(
                        page_content=child_text,
                        metadata={
                            "page_number": page.metadata["page_number"],
                            "chunk_index": idx,
                            "parent_text": parent_text,
                        },
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
    strategy: str, pages: list[Document], chunk_size: int = 512, chunk_overlap: int = 64
) -> list[Document]:
    fn = CHUNKING_STRATEGIES.get(strategy)
    if fn is None:
        raise ValueError(f"Unknown chunking strategy: {strategy!r}")
    return fn(pages, chunk_size, chunk_overlap)
