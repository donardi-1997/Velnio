from app.api.routes import dashboard as legacy_dashboard
from app.api.routes import performance as legacy_performance
from app.api.routes import tracking as legacy_tracking
from app.modules.analytics.api import dashboard, performance, tracking


def _contract(router):
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    return entries


def test_dashboard_routes_preserved():
    assert set(_contract(dashboard.router)) == {("GET", "/summary")}


def test_performance_routes_preserved():
    assert set(_contract(performance.router)) == {
        ("GET", "/{campaign_id}/performance"),
        ("GET", "/{campaign_id}/performance/timeline"),
        ("GET", "/{campaign_id}/performance/winner"),
        ("GET", "/{campaign_id}/variants/performance"),
        ("GET", "/{campaign_id}/angles/performance"),
        ("POST", "/{campaign_id}/performance/analyze"),
    }


def test_tracking_routes_preserved():
    assert set(_contract(tracking.router)) == {
        ("POST", "/events/{tracking_key}"),
        ("POST", "/batch/{tracking_key}"),
        ("POST", "/beacon/{tracking_key}"),
    }


def test_legacy_routes_are_modular_shims():
    assert legacy_dashboard.router is dashboard.router
    assert legacy_performance.router is performance.router
    assert legacy_tracking.router is tracking.router


def test_no_duplicate_analytics_routes():
    entries = _contract(dashboard.router) + _contract(performance.router) + _contract(tracking.router)
    assert len(entries) == len(set(entries))
