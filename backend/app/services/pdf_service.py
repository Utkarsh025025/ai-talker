"""
PDF text extraction service using PyMuPDF (fitz).
Falls back to pdfplumber for scanned/encrypted PDFs.
"""

import io
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
from app.config import get_settings

settings = get_settings()


class PDFService:
    """Extracts plain text from PDF files."""

    @staticmethod
    def extract_text(file_path: str | Path) -> str:
        """
        Extract all text from a PDF.

        Tries PyMuPDF first (fast, handles most PDFs).
        Falls back to pdfplumber for complex layouts.

        Returns the extracted text or raises RuntimeError.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        # Primary: PyMuPDF
        try:
            text = PDFService._extract_with_pymupdf(file_path)
            if text.strip():
                return text
        except Exception as exc:
            pass  # Fall through to pdfplumber

        # Fallback: pdfplumber
        try:
            text = PDFService._extract_with_pdfplumber(file_path)
            if text.strip():
                return text
        except Exception as exc:
            raise RuntimeError(f"Failed to extract text from PDF: {exc}") from exc

        return ""

    @staticmethod
    def _extract_with_pymupdf(file_path: Path) -> str:
        """Use PyMuPDF to extract text page by page."""
        doc = fitz.open(str(file_path))
        pages: list[str] = []
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if page_text.strip():
                pages.append(f"[Page {page_num}]\n{page_text}")
        doc.close()
        return "\n\n".join(pages)

    @staticmethod
    def _extract_with_pdfplumber(file_path: Path) -> str:
        """Use pdfplumber (slower, but better for complex layouts)."""
        pages: list[str] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[Page {page_num}]\n{text}")
        return "\n\n".join(pages)

    @staticmethod
    def get_page_count(file_path: str | Path) -> int:
        """Return the number of pages in a PDF."""
        with fitz.open(str(file_path)) as doc:
            return doc.page_count
