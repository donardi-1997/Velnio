import pytest

from app.modules.integrations.infrastructure.meta_ads import (
    MetaAdsProviderError,
    RealMetaAdsProvider,
)


@pytest.mark.asyncio
async def test_real_provider_delivery_resources_use_expected_read_only_edges(monkeypatch):
    provider = RealMetaAdsProvider()
    monkeypatch.setattr(provider, "_require_config", lambda: None)
    calls: list[tuple[str, str, int]] = []

    async def fake_list_edge(url: str, access_token: str, *, fields: str, max_pages: int):
        calls.append((url, fields, max_pages))
        if url.endswith("/adspixels"):
            return [
                {"id": "101", "name": "Checkout Pixel", "last_fired_time": "2026-09-10T18:00:00+0000"},
                {"id": "101", "name": "Duplicate Pixel", "last_fired_time": None},
            ]
        if url.endswith("/promote_pages"):
            return [{"id": "201", "name": "Store Page"}]
        if url.endswith("/connected_instagram_accounts"):
            return [{"id": "301", "name": "Store Instagram", "username": "store"}]
        raise AssertionError(f"Unexpected Meta edge: {url}")

    monkeypatch.setattr(provider, "_list_edge", fake_list_edge)

    resources = await provider.get_delivery_resources("secret-token", "act_123456")

    assert resources["ad_account_id"] == "act_123456"
    assert resources["pixels"] == [
        {"id": "101", "name": "Checkout Pixel", "last_fired_time": "2026-09-10T18:00:00+0000"}
    ]
    assert resources["pages"] == [{"id": "201", "name": "Store Page"}]
    assert resources["instagram_accounts"] == [
        {"id": "301", "name": "Store Instagram", "username": "store"}
    ]

    assert len(calls) == 3
    assert calls[0][0].endswith("/act_123456/adspixels")
    assert calls[0][1] == "id,name,last_fired_time"
    assert "code" not in calls[0][1]
    assert calls[1][0].endswith("/act_123456/promote_pages")
    assert calls[1][1] == "id,name"
    assert calls[2][0].endswith("/act_123456/connected_instagram_accounts")
    assert calls[2][1] == "id,name,username"
    assert all(max_pages == 10 for _, _, max_pages in calls)


@pytest.mark.asyncio
async def test_real_provider_delivery_resources_reject_malformed_account_before_network(monkeypatch):
    provider = RealMetaAdsProvider()
    monkeypatch.setattr(provider, "_require_config", lambda: None)

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Network boundary must not be reached for malformed account IDs")

    monkeypatch.setattr(provider, "_list_edge", fail_if_called)

    with pytest.raises(MetaAdsProviderError, match="Invalid Meta ad account id"):
        await provider.get_delivery_resources("secret-token", "../../me")


def test_real_provider_normalize_resources_deduplicates_and_ignores_invalid_ids():
    normalized = RealMetaAdsProvider._normalize_resources(
        [
            {"id": "1", "name": "First"},
            {"id": "1", "name": "Duplicate"},
            {"id": "", "name": "Empty"},
            {"name": "Missing"},
            {"id": "2", "name": 123},
        ],
        optional_fields=("name",),
    )

    assert normalized == [
        {"id": "1", "name": "First"},
        {"id": "2", "name": None},
    ]
