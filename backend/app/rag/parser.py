"""Document parsing: turns an uploaded PDF into per-page plain text."""
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass
class ParsedPage:
    page_number: int
    text: str


def parse_pdf(file_path: str) -> list[ParsedPage]:
    reader = PdfReader(file_path)
    pages: list[ParsedPage] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(ParsedPage(page_number=i + 1, text=text))
    return pages
