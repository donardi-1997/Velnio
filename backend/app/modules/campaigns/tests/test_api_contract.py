from app.api.routes import campaigns as legacy_campaigns
from app.api.routes import demo as legacy_demo
from app.api.routes import variants as legacy_variants
from app.api.routes import visual_assets as legacy_visual_assets
from app.modules.campaigns.api.router import router


def _route_contract(api_router):
    contract = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                contract.add((method, route.path))
    return contract


def test_campaign_api_preserves_expected_routes():
    contract = _route_contract(router)
    expected = {
        ("GET", "/campaigns"),
        ("POST", "/campaigns"),
        ("GET", "/campaigns/by-product/{product_id}"),
        ("POST", "/campaigns/by-product/{product_id}"),
        ("GET", "/campaigns/{campaign_id}"),
        ("PATCH", "/campaigns/{campaign_id}"),
        ("DELETE", "/campaigns/{campaign_id}"),
        ("GET", "/campaigns/{campaign_id}/angles"),
        ("POST", "/campaigns/{campaign_id}/angles/generate"),
        ("POST", "/campaigns/{campaign_id}/angles/{angle_id}/select"),
        ("GET", "/campaigns/{campaign_id}/offer"),
        ("POST", "/campaigns/{campaign_id}/offer/generate"),
        ("PATCH", "/campaigns/offers/{offer_id}"),
        ("GET", "/campaigns/{campaign_id}/landing"),
        ("POST", "/campaigns/{campaign_id}/landing/generate"),
        ("GET", "/campaigns/{campaign_id}/publish-readiness"),
        ("POST", "/campaigns/{campaign_id}/publish"),
        ("POST", "/campaigns/{campaign_id}/generate-brief"),
        ("GET", "/campaigns/{campaign_id}/visual-direction"),
        ("POST", "/campaigns/{campaign_id}/visual-direction/generate"),
        ("PATCH", "/campaigns/visual-directions/{vd_id}"),
        ("POST", "/campaigns/{campaign_id}/assets/generate"),
        ("POST", "/campaigns/{campaign_id}/assets/{image_id}/select"),
        ("GET", "/campaigns/{campaign_id}/variants"),
        ("POST", "/campaigns/{campaign_id}/variants"),
        ("PATCH", "/campaigns/{campaign_id}/variants/traffic"),
        ("PATCH", "/campaigns/{campaign_id}/variants/{variant_id}"),
        ("DELETE", "/campaigns/{campaign_id}/variants/{variant_id}"),
        ("POST", "/campaigns/{campaign_id}/demo/events"),
        ("DELETE", "/campaigns/{campaign_id}/demo/events"),
        ("GET", "/campaigns/{campaign_id}/meta-ads/publications"),
        ("POST", "/campaigns/{campaign_id}/meta-ads/publish"),
        ("PATCH", "/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/delivery-config"),
        ("GET", "/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/ad-set"),
        ("POST", "/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/ad-set"),
    }
    assert expected <= contract


def test_legacy_campaign_router_is_modular_router():
    assert legacy_campaigns.router is router


def test_legacy_feature_shims_point_to_modular_routers():
    modular_routers = {id(route) for route in [
        legacy_demo.router,
        legacy_variants.router,
        legacy_visual_assets.router,
    ]}
    assert len(modular_routers) == 3


def test_campaign_routes_are_unique():
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))
