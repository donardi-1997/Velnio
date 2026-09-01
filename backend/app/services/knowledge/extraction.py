"""Document text extraction service using pypdf for PDFs and safe decoding for TXT."""

import io
from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

from app.services.knowledge.normalization import normalize_extracted_text


class ExtractionResult:
    """Result of document text extraction."""
    def __init__(
        self,
        text: str,
        character_count: int,
        page_count: Optional[int] = None,
        status: str = "READY",
        error: Optional[str] = None,
    ):
        self.text = text
        self.character_count = character_count
        self.page_count = page_count
        self.status = status
        self.error = error


class DocumentExtractionService:
    """Extracts text from imported documents (TXT, PDF, Google Docs)."""

    SUPPORTED_TEXT_TYPES = {"text/plain", "text/html", "text/markdown", "text/csv"}
    MAX_DOCUMENT_PROCESSING_MB = 25

    async def extract(
        self,
        document: Any,
        storage_provider: Any = None,
    ) -> ExtractionResult:
        """Extract text from a document.

        For text/plain, Google Docs, and similar text types the content is already
        available in ``document.content_text`` so no storage read is needed.
        For PDFs the bytes are read from storage and parsed with pypdf.
        """
        from app.core.config import settings

        file_type = (getattr(document, "file_type", "") or "").lower()
        content_text = getattr(document, "content_text", None)

        if file_type in self.SUPPORTED_TEXT_TYPES:
            return self._extract_from_text_content(content_text or "")

        if file_type == "application/pdf":
            storage_key = getattr(document, "storage_key", None)
            if not storage_key:
                return ExtractionResult(
                    text="",
                    character_count=0,
                    status="FAILED",
                    error="PDF has no storage key",
                )
            if not storage_provider:
                return ExtractionResult(
                    text="",
                    character_count=0,
                    status="NEEDS_OCR",
                    error="PDF extraction requires storage provider",
                )
            try:
                content = await storage_provider.read_bytes(storage_key)
            except Exception as exc:
                logger.warning("Failed to read PDF from storage: %s", exc)
                return ExtractionResult(
                    text="",
                    character_count=0,
                    status="FAILED",
                    error=f"Could not read file from storage: {exc}",
                )

            file_size = len(content)
            if file_size > settings.MAX_DOCUMENT_PROCESSING_MB * 1024 * 1024:
                return ExtractionResult(
                    text="",
                    character_count=0,
                    status="FAILED",
                    error=f"File exceeds {settings.MAX_DOCUMENT_PROCESSING_MB}MB limit",
                )

            return self._extract_pdf(content)

        if file_type in ("application/vnd.google-apps.document",):
            if content_text:
                normalized = normalize_extracted_text(content_text)
                return ExtractionResult(
                    text=normalized,
                    character_count=len(normalized),
                    page_count=None,
                    status="READY",
                )
            return ExtractionResult(
                text="",
                character_count=0,
                status="FAILED",
                error="Google Doc has no extracted content",
            )

        return ExtractionResult(
            text="",
            character_count=0,
            status="FAILED",
            error=f"Unsupported file type: {file_type}",
        )

    @staticmethod
    def _extract_from_text_content(content_text: str) -> ExtractionResult:
        """Normalize and return already-decoded text content."""
        normalized = normalize_extracted_text(content_text)
        return ExtractionResult(
            text=normalized,
            character_count=len(normalized),
            page_count=None,
            status="READY" if normalized else "FAILED",
            error=None if normalized else "No extractable text",
        )

    @staticmethod
    def _extract_pdf(content: bytes) -> ExtractionResult:
        """Extract text from PDF using pypdf."""
        if not HAS_PYPDF:
            return ExtractionResult(
                text="",
                character_count=0,
                status="FAILED",
                error="pypdf not installed",
            )

        try:
            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            page_count = len(reader.pages)

            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception:
                    continue

            text = "\n".join(text_parts)

            if not text.strip():
                return ExtractionResult(
                    text="",
                    character_count=0,
                    page_count=page_count,
                    status="NEEDS_OCR",
                    error="PDF appears to contain no extractable text",
                )

            text = normalize_extracted_text(text)

            return ExtractionResult(
                text=text,
                character_count=len(text),
                page_count=page_count,
                status="READY",
            )
        except Exception as exc:
            return ExtractionResult(
                text="",
                character_count=0,
                page_count=0,
                status="FAILED",
                error=str(exc),
            )
