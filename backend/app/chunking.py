"""
Document chunking, built on LangChain's RecursiveCharacterTextSplitter.

chunk_size / chunk_overlap are now in CHARACTERS (LangChain's convention),
not words. This is still the #1 knob you'll sweep over in Phase 3 — only
the unit changed.
"""
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def chunk_documents(documents: Dict[str, str], chunk_size: int = 400, overlap: int = 80) -> List[Document]:
    """
    Split each {doc_id: text} entry into overlapping LangChain Documents.

    Each returned Document carries doc_id and a stable chunk_id in its
    metadata, e.g. "parental_leave_policy::chunk0", so ground-truth
    relevance (which is labeled at the doc level in the test dataset) can
    still be resolved down to specific chunks after splitting.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: List[Document] = []
    for doc_id, text in documents.items():
        pieces = splitter.split_text(text)
        for idx, piece in enumerate(pieces):
            all_chunks.append(
                Document(
                    page_content=piece,
                    metadata={"doc_id": doc_id, "chunk_id": f"{doc_id}::chunk{idx}"},
                )
            )
    return all_chunks