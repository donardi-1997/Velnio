# Backend Architecture

Velnio is organized as a **modular monolith**. The application is deployed as one FastAPI service and one database, while business capabilities are composed through explicit module boundaries.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | Authentication, users, workspace membership and tenant context |
| `catalog` | Products, product analysis, imports and enrichment |
| `campaigns` | Campaign lifecycle, selling angles, offers, landings, visual assets, publishing, variants and briefs |
| `commerce` | Stores and Shopify-facing commerce capabilities |
| `knowledge` | Knowledge sources and campaign context |
| `integrations` | External non-commerce connectors such as Google Drive |
| `billing` | Plans, subscriptions, credits and credit ledger |
| `analytics` | Dashboard, event tracking and campaign performance |

## Composition rule

`app.main` is the composition root. It configures FastAPI and mounts only `app.modules.router.api_router`. The module router composes the business modules; each module owns its URL composition and tags.

A module may temporarily expose a compatibility shim while code is migrated, but new business logic must be implemented inside the owning module rather than under `app/api/routes`.

## Campaigns vertical slice

Campaigns is the first module being physically extracted:

```text
app/modules/campaigns/
├── api/
│   ├── campaigns.py
│   ├── angles.py
│   ├── offers.py
│   ├── landings.py
│   ├── publishing.py
│   ├── briefs.py
│   ├── deps.py
│   └── router.py
├── application/
│   └── service.py
├── domain/
│   └── models.py
├── infrastructure/
│   └── repository.py
├── tests/
│   └── test_api_contract.py
└── router.py
```

`app/api/routes/campaigns.py` and `app/api/routes/publish.py` are now compatibility shims only. They must not receive new business logic.

The next Campaigns extraction targets are the remaining legacy campaign-owned handlers for visual assets, variants and demo flows, followed by moving angle/offer/landing orchestration out of HTTP handlers and into application services.

## Dependency rules

1. A module may depend on `app.core` and `app.db` infrastructure.
2. HTTP composition belongs to the owning module.
3. New business logic should live inside the owning module, not in a global service bucket.
4. Cross-module calls should use explicit service interfaces/application services, not import another module's route handlers.
5. Domain code must not depend on FastAPI or infrastructure concerns.
6. Database migrations remain centralized under Alembic because Velnio is still one deployable and one database.
7. Public endpoint paths must remain backward compatible unless a versioned API change is intentional.
8. `app.main` must not import individual feature route files.
9. Compatibility shims may re-export moved symbols temporarily, but new code must import the owning module directly.

## Migration strategy

Use incremental vertical extraction rather than a big-bang rewrite:

1. Characterize existing route and behavior contracts.
2. Introduce the target module boundary.
3. Move persistence and orchestration behind module interfaces.
4. Move handlers physically into the module.
5. Leave compatibility shims for legacy imports.
6. Run targeted and full tests.
7. Remove shims only when no internal imports depend on them.

This keeps Velnio deployable while the architecture evolves and prevents new product work from rebuilding the previous global-layer coupling.
