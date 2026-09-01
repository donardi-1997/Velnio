import pytest
from app.services.knowledge.context_builder import KnowledgeContextBuilder


def test_empty_context():
    builder = KnowledgeContextBuilder()
    assert builder is not None


@pytest.mark.asyncio
async def test_build_empty_sources():
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    builder = KnowledgeContextBuilder()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    result = await builder.build(
        db=mock_db,
        product_id=uuid4(),
        workspace_id=uuid4(),
    )
    assert result == ""


@pytest.mark.asyncio
async def test_build_with_sources():
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    builder = KnowledgeContextBuilder()

    mock_source = MagicMock()
    mock_source.is_primary = True
    mock_source.source_type = "REVIEWS"
    mock_source.title = "Customer Reviews"
    mock_source.content_text = "Great product, fast shipping!"
    mock_source.status = "ACTIVE"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_source]
    mock_db.execute.return_value = mock_result

    result = await builder.build(
        db=mock_db,
        product_id=uuid4(),
        workspace_id=uuid4(),
    )
    assert "REVIEWS" in result
    assert "Customer Reviews" in result
    assert "Great product" in result


@pytest.mark.asyncio
async def test_build_respects_char_limit():
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4

    builder = KnowledgeContextBuilder()

    mock_source = MagicMock()
    mock_source.is_primary = False
    mock_source.source_type = "MANUAL"
    mock_source.title = "Long Document"
    mock_source.content_text = "x" * 100000
    mock_source.status = "ACTIVE"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_source]
    mock_db.execute.return_value = mock_result

    result = await builder.build(
        db=mock_db,
        product_id=uuid4(),
        workspace_id=uuid4(),
        max_chars=5000,
    )
    assert len(result) <= 5000
