import pytest
from app.services.knowledge.extraction import DocumentExtractionService, ExtractionResult


class MockDocument:
    def __init__(self, file_type: str, content_text: str = None, storage_key: str = None):
        self.file_type = file_type
        self.content_text = content_text
        self.storage_key = storage_key


class MockStorageProvider:
    def __init__(self, content: bytes):
        self._content = content

    async def read_bytes(self, key: str) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_extract_text_plain():
    service = DocumentExtractionService()
    doc = MockDocument("text/plain", content_text="Hello world. This is test content.")
    result = await service.extract(doc)
    assert result.status == "READY"
    assert "Hello world" in result.text
    assert result.character_count > 0
    assert result.page_count is None


@pytest.mark.asyncio
async def test_extract_text_normalization():
    service = DocumentExtractionService()
    doc = MockDocument("text/plain", content_text="Line one\n\n\n\n\nLine two")
    result = await service.extract(doc)
    assert result.status == "READY"
    assert "\n\n\n" not in result.text


@pytest.mark.asyncio
async def test_extract_text_empty():
    service = DocumentExtractionService()
    doc = MockDocument("text/plain", content_text="")
    result = await service.extract(doc)
    assert result.status == "FAILED"
    assert result.error == "No extractable text"


@pytest.mark.asyncio
async def test_extract_google_docs():
    service = DocumentExtractionService()
    doc = MockDocument("application/vnd.google-apps.document", content_text="Google Docs content")
    result = await service.extract(doc)
    assert result.status == "READY"
    assert "Google Docs content" in result.text


@pytest.mark.asyncio
async def test_extract_unsupported_type():
    service = DocumentExtractionService()
    doc = MockDocument("application/unknown")
    result = await service.extract(doc)
    assert result.status == "FAILED"
    assert "Unsupported file type" in result.error


@pytest.mark.asyncio
async def test_extract_pdf_no_storage_key():
    service = DocumentExtractionService()
    doc = MockDocument("application/pdf", storage_key=None)
    result = await service.extract(doc)
    assert result.status == "FAILED"
    assert "no storage key" in result.error.lower()


@pytest.mark.asyncio
async def test_extract_pdf_no_provider():
    service = DocumentExtractionService()
    doc = MockDocument("application/pdf", storage_key="some/key.pdf")
    result = await service.extract(doc, storage_provider=None)
    assert result.status == "NEEDS_OCR"
    assert "storage provider" in result.error.lower()
