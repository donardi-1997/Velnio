import pytest
import asyncio


@pytest.mark.asyncio
async def test_local_storage_save_delete():
    from app.services.storage.local_provider import LocalStorageProvider
    provider = LocalStorageProvider()

    key = await provider.save_bytes(b"test data", "image/png", "test")
    assert key.startswith("test/")

    url = provider.get_public_url(key)
    assert url.startswith("/storage/test/")

    await provider.delete(key)


@pytest.mark.asyncio
async def test_reject_unsafe_content_type():
    from app.services.import_engine.ssrf import validate_url

    assert not validate_url("ftp://example.com")
    assert not validate_url("")
    assert not validate_url("not-a-url")
    assert validate_url("https://example.com") is not None
