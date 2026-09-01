import pytest
from app.services.knowledge.claim_validation import ClaimValidationService


def test_extract_claims():
    service = ClaimValidationService()
    claims = service._extract_claims("This is claim one. This is claim two. This is claim three.")
    assert len(claims) == 3


def test_needs_source_backing():
    service = ClaimValidationService()
    assert service._needs_source_backing("This product is clinically proven") is True
    assert service._needs_source_backing("Buy now for great results") is False
    assert service._needs_source_backing("Doctor recommended formula") is True
    assert service._needs_source_backing("Fast free shipping") is False


def test_validate_claim_supported():
    service = ClaimValidationService()
    source_texts = [
        {"title": "Reviews", "type": "REVIEWS", "text": "great product fast shipping excellent quality"}
    ]
    result = service._validate_claim("great product fast shipping", source_texts)
    assert result.supported is True
    assert result.source_title == "Reviews"


def test_validate_claim_unsupported():
    service = ClaimValidationService()
    source_texts = [
        {"title": "Reviews", "type": "REVIEWS", "text": "great product fast shipping excellent quality"}
    ]
    result = service._validate_claim("completely unrelated claim about something else", source_texts)
    assert result.supported is False


@pytest.mark.asyncio
async def test_validate_pass_status():
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    service = ClaimValidationService()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    report = await service.validate(
        content_text="Buy now for great results. Fast free shipping.",
        db=mock_db,
        product_id=uuid4(),
        workspace_id=uuid4(),
    )
    assert report.overall_status == "PASS"
    assert len(report.results) > 0
