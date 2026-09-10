from app.api.routes import ai as legacy_analysis
from app.api.routes import enrichment as legacy_enrichment
from app.api.routes import product_import as legacy_imports
from app.api.routes import products as legacy_products
from app.modules.catalog.api import analysis, enrichment, imports, products
from app.modules.catalog.router import router


def _contract(api_router):
    entries = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.add((method, route.path))
    return entries


def test_catalog_preserves_expected_routes():
    contract = _contract(router)
    expected = {
        ("GET", "/products"),
        ("POST", "/products"),
        ("GET", "/products/{product_id}"),
        ("PATCH", "/products/{product_id}"),
        ("DELETE", "/products/{product_id}"),
        ("POST", "/products/{product_id}/analyze"),
        ("POST", "/products/import/preview"),
        ("POST", "/products/import/create"),
        ("POST", "/products/{product_id}/images/upload"),
        ("POST", "/products/{product_id}/enrich"),
        ("GET", "/products/{product_id}/enrichment"),
    }
    assert expected <= contract


def test_catalog_routes_are_unique():
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))


def test_legacy_catalog_routers_are_modular_routers():
    assert legacy_products.router is products.router
    assert legacy_analysis.router is analysis.router
    assert legacy_imports.router is imports.router
    assert legacy_enrichment.router is enrichment.router
