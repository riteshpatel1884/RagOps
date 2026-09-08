"""Document parsing via LangChain's PyPDFLoader — one Document per PDF page."""
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def parse_pdf(file_path: str) -> list[Document]:
    loader = PyPDFLoader(file_path)
    pages = loader.load()  # PyPDFLoader's "page" metadata is 0-indexed
    for doc in pages:
        doc.metadata["page_number"] = doc.metadata.get("page", 0) + 1
    return [d for d in pages if d.page_content.strip()]
