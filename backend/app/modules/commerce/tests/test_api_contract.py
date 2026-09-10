from app.api.routes import shopify as legacy_shopify
from app.api.routes import stores as legacy_stores
from app.modules.commerce.router import router


def _route_contract(api_router):
    contract = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                contract.add((method, route.path))
    return contract


def test_commerce_api_preserves_expected_routes():
    contract = _route_contract(router)
    expected = {
        ("GET", "/stores"),
        ("POST", "/stores/mock-connect"),
        ("POST", "/stores/{store_id}/disconnect"),
        ("POST", "/products/{product_id}/publish"),
    }
    assert expected <= contract


def test_legacy_commerce_routers_are_modular_routers():
    modular_by_path = {route.path: route for route in router.routes}
    assert legacy_stores.router.routes[0].path == ""
    assert legacy_shopify.router.routes[0].path == "/{product_id}/publish"
    assert "/stores" in modular_by_path
    assert "/products/{product_id}/publish" in modular_by_path


def test_commerce_routes_are_unique():
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))
