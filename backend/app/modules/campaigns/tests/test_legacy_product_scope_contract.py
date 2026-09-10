from app.api.routes import angles as legacy_angles
from app.api.routes import landings as legacy_landings
from app.modules.campaigns.api import product_scope


def _route_contract(api_router):
    contract = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                contract.add((method, route.path))
    return contract


def test_legacy_product_scope_shims_are_separated():
    assert legacy_angles.router is product_scope.angles_router
    assert legacy_landings.router is product_scope.landings_router
    assert legacy_angles.router is not legacy_landings.router

    assert _route_contract(legacy_angles.router) == {
        ("GET", "/{product_id}/angles"),
        ("POST", "/{product_id}/angles/generate"),
        ("POST", "/{product_id}/angles/{angle_id}/select"),
    }
    assert _route_contract(legacy_landings.router) == {
        ("GET", "/{product_id}/landing"),
        ("POST", "/{product_id}/landing/generate"),
        ("GET", "/landing-sections/{section_id}"),
        ("PATCH", "/landing-sections/{section_id}"),
        ("PATCH", "/landings/{landing_id}"),
    }
