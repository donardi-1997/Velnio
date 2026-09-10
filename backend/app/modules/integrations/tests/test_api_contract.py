from app.api.routes import google_drive as legacy_google_drive
from app.modules.integrations.api.google_drive import router as google_drive_router
from app.modules.integrations.api.meta_ads import router as meta_ads_router


def _route_contract(api_router):
    contract = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                contract.add((method, route.path))
    return contract


def test_google_drive_api_preserves_expected_routes():
    assert {
        ("GET", "/status"),
        ("GET", "/connect"),
        ("GET", "/callback"),
        ("POST", "/connect-mock"),
        ("POST", "/disconnect"),
        ("GET", "/browse/{folder_id}"),
        ("GET", "/search"),
        ("POST", "/import-image"),
        ("POST", "/import-document"),
        ("POST", "/import-asset"),
        ("GET", "/documents/{product_id}"),
    } <= _route_contract(google_drive_router)


def test_legacy_google_drive_router_is_modular_router():
    assert legacy_google_drive.router is google_drive_router


def test_google_drive_routes_are_unique():
    entries = []
    for route in google_drive_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))


def test_meta_ads_api_exposes_connection_and_account_discovery_routes():
    assert {
        ("GET", "/status"),
        ("GET", "/connect"),
        ("GET", "/callback"),
        ("POST", "/connect-mock"),
        ("POST", "/disconnect"),
        ("GET", "/ad-accounts"),
    } <= _route_contract(meta_ads_router)


def test_meta_ads_routes_are_unique():
    entries = []
    for route in meta_ads_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))
