from app.api.routes import auth as legacy_auth
from app.api.routes import workspace as legacy_workspace
from app.modules.identity.api import auth, workspace


def _contract(router):
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    return entries


def test_auth_routes_preserved():
    assert set(_contract(auth.router)) == {
        ("POST", "/register"),
        ("POST", "/login"),
        ("POST", "/refresh"),
        ("GET", "/me"),
    }


def test_workspace_routes_preserved():
    assert set(_contract(workspace.router)) == {("GET", "")}


def test_legacy_routes_are_modular_shims():
    assert legacy_auth.router is auth.router
    assert legacy_workspace.router is workspace.router


def test_no_duplicate_identity_routes():
    entries = _contract(auth.router) + _contract(workspace.router)
    assert len(entries) == len(set(entries))
