"""PDF text extraction utilities."""

from __future__ import annotations

import re
from pathlib import Path


class PdfReader:
    """Extract and clean text from PDF files using pypdf."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"PDF not found: {self.path}")
        if self.path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {self.path.suffix}")

    def extract_text(self) -> str:
        """Extract all text from the PDF and return cleaned content."""
        try:
            from pypdf import PdfReader as _PdfReader
        except ImportError as exc:
            raise ImportError(
                "pypdf is required: pip install pypdf"
            ) from exc

        reader = _PdfReader(str(self.path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        raw = "\n\n".join(pages)
        return self._clean(raw)

    @staticmethod
    def _clean(text: str) -> str:
        """Remove common PDF artifacts and normalise whitespace."""
        lines = text.splitlines()
        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()
            if re.fullmatch(r"\d{1,4}", stripped):
                continue
            if re.fullmatch(r"[-=_.]{3,}", stripped):
                continue
            cleaned.append(line)

        joined = "\n".join(cleaned)
        joined = re.sub(r"\n{3,}", "\n\n", joined)

        normalised_lines: list[str] = []
        for line in joined.splitlines():
            line = re.sub(r"[ \t]{2,}", " ", line)
            normalised_lines.append(line)

        return "\n".join(normalised_lines).strip()

    def __repr__(self) -> str:
        return f"PdfReader({self.path!r})"
