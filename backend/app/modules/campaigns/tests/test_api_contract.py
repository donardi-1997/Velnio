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
        ("GET", ""),
        ("POST", ""),
        ("GET", "/by-product/{product_id}"),
        ("POST", "/by-product/{product_id}"),
        ("GET", "/{campaign_id}"),
        ("PATCH", "/{campaign_id}"),
        ("DELETE", "/{campaign_id}"),
        ("GET", "/{campaign_id}/angles"),
        ("POST", "/{campaign_id}/angles/generate"),
        ("POST", "/{campaign_id}/angles/{angle_id}/select"),
        ("GET", "/{campaign_id}/offer"),
        ("POST", "/{campaign_id}/offer/generate"),
        ("PATCH", "/offers/{offer_id}"),
        ("GET", "/{campaign_id}/landing"),
        ("POST", "/{campaign_id}/landing/generate"),
        ("GET", "/{campaign_id}/publish-readiness"),
        ("POST", "/{campaign_id}/publish"),
        ("POST", "/{campaign_id}/generate-brief"),
        ("GET", "/{campaign_id}/visual-direction"),
        ("POST", "/{campaign_id}/visual-direction/generate"),
        ("PATCH", "/visual-directions/{vd_id}"),
        ("POST", "/{campaign_id}/assets/generate"),
        ("POST", "/{campaign_id}/assets/{image_id}/select"),
        ("GET", "/{campaign_id}/variants"),
        ("POST", "/{campaign_id}/variants"),
        ("PATCH", "/{campaign_id}/variants/traffic"),
        ("PATCH", "/{campaign_id}/variants/{variant_id}"),
        ("DELETE", "/{campaign_id}/variants/{variant_id}"),
        ("POST", "/{campaign_id}/demo/events"),
        ("DELETE", "/{campaign_id}/demo/events"),
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
