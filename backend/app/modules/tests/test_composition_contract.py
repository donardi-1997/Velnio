from app.modules.router import api_router


def test_composed_api_has_no_duplicate_method_paths():
    entries = []
    for route in api_router.routes:
        methods = getattr(route, "methods", None) or set()
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                entries.append((method, route.path))

    duplicates = sorted({entry for entry in entries if entries.count(entry) > 1})
    assert duplicates == [], f"Duplicate API routes found: {duplicates}"


def test_composed_api_contains_all_primary_module_prefixes():
    paths = {route.path for route in api_router.routes}
    expected_prefixes = {
        "/auth",
        "/workspace",
        "/products",
        "/campaigns",
        "/stores",
        "/knowledge",
        "/google-drive",
        "/credits",
        "/billing",
        "/dashboard",
        "/tracking",
    }

    for prefix in expected_prefixes:
        assert any(path == prefix or path.startswith(f"{prefix}/") for path in paths), prefix
