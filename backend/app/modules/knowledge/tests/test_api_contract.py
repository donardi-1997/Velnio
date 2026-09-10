from app.api.routes import knowledge as legacy_knowledge
from app.modules.knowledge.api.sources import router as source_router
from app.modules.knowledge.router import router


def _route_contract(api_router):
    contract = set()
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                contract.add((method, route.path))
    return contract


def test_knowledge_api_preserves_expected_routes():
    assert _route_contract(router) == {
        ("GET", "/knowledge/"),
        ("POST", "/knowledge/"),
        ("GET", "/knowledge/{source_id}"),
        ("PATCH", "/knowledge/{source_id}"),
        ("DELETE", "/knowledge/{source_id}"),
    }


def test_legacy_knowledge_router_is_modular_source_router():
    assert legacy_knowledge.router is source_router


def test_knowledge_routes_are_unique():
    entries = []
    for route in router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))
    assert len(entries) == len(set(entries))
