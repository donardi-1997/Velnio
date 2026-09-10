from app.api.routes import billing as legacy_billing
from app.api.routes import credits as legacy_credits
from app.modules.billing.api import credits, subscriptions


def _contract(router):
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    return entries


def test_credit_routes_preserved():
    assert set(_contract(credits.router)) == {
        ("GET", ""),
        ("GET", "/transactions"),
    }


def test_billing_routes_preserved_and_extended():
    assert set(_contract(subscriptions.router)) == {
        ("GET", "/plans"),
        ("GET", "/subscription"),
        ("GET", "/entitlements"),
        ("POST", "/checkout"),
        ("POST", "/portal"),
        ("POST", "/webhook"),
    }


def test_legacy_routes_are_modular_shims():
    assert legacy_credits.router is credits.router
    assert legacy_billing.router is subscriptions.router


def test_no_duplicate_billing_routes():
    entries = _contract(credits.router) + _contract(subscriptions.router)
    assert len(entries) == len(set(entries))
