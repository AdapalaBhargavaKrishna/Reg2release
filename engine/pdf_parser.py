import pymupdf
import io

class RegulatoryPDFParser:
    """Extracts text and metadata from regulatory PDF bulletins and circulars."""

    @staticmethod
    def extract_from_bytes(file_bytes: bytes) -> dict:
        """Extracts text, page count, and metadata from uploaded PDF bytes."""
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        metadata = doc.metadata or {}
        page_count = len(doc)
        doc.close()

        return {
            "full_text": full_text,
            "page_count": page_count,
            "metadata": metadata,
            "pages": pages_text
        }

    @staticmethod
    def extract_from_path(file_path: str) -> dict:
        """Extracts text, page count, and metadata from a local PDF file path."""
        with open(file_path, "rb") as f:
            return RegulatoryPDFParser.extract_from_bytes(f.read())
