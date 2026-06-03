"""Paper Agent — academic paper analysis using Claude."""

from .agent import PaperAgent
from .pdf_reader import PdfReader

__all__ = ["PaperAgent", "PdfReader"]
__version__ = "0.1.0"
