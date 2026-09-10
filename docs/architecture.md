# Backend Architecture

Velnio is organized as a **modular monolith**. The application is deployed as one FastAPI service and one database, while business capabilities are composed through explicit module boundaries.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | Authentication, users, workspace membership and tenant context |
| `catalog` | Products, product analysis, imports and enrichment |
| `campaigns` | Campaigns, selling angles, offers, landings, visual assets, publishing, variants, briefs and experiments |
| `commerce` | Stores and Shopify-facing commerce capabilities |
| `knowledge` | Knowledge sources and campaign context |
| `integrations` | External non-commerce connectors such as Google Drive |
| `billing` | Plans, subscriptions, credits and credit ledger |
| `analytics` | Dashboard, event tracking and campaign performance |

## Composition rule

`app.main` is the composition root. It configures FastAPI and mounts only `app.modules.router.api_router`. The module router composes the business modules; each module owns its URL composition and tags.

The migration is incremental. Legacy route modules may temporarily remain as compatibility shims, but business logic must move into the owning module. Public API contracts stay stable during extraction.

## Dependency rules

1. A module may depend on `app.core` and `app.db` infrastructure.
2. HTTP composition belongs to the owning module.
3. New business logic should live inside the owning module, not in a global service bucket.
4. Cross-module calls should use explicit service interfaces/application services, not import another module's route handlers.
5. Database migrations remain centralized under Alembic because Velnio is still one deployable and one database.
6. Public endpoint paths must remain backward compatible unless a versioned API change is intentional.
7. `app.main` must not import individual feature route files.
8. FastAPI handlers should be thin adapters; orchestration belongs in application services.
9. SQLAlchemy access should be encapsulated behind module repositories where practical instead of repeated across HTTP handlers.

## Campaigns module

Campaigns is the first vertically extracted module and currently owns:

```text
app/modules/campaigns/
  api/
    campaigns.py
    angles.py
    offers.py
    landings.py
    publishing.py
    briefs.py
    visual_assets.py
    variants.py
    demo.py
    router.py
  application/
    service.py
    angles.py
    offers.py
    landings.py
  domain/
    models.py
  infrastructure/
    repository.py
  tests/
    test_api_contract.py
```

The legacy `app.api.routes.campaigns`, `publish`, `visual_assets`, `variants` and `demo` modules are compatibility shims. The Campaigns module mounts the real implementations directly.

Campaign CRUD, angle generation/selection, offer generation/update and landing generation are now orchestrated through application services. Publishing, briefs, visual assets, variants and demo flows remain candidates for further service extraction.

## Target internal shape

```text
app/
  modules/
    catalog/
      api/
      application/
      domain/
      infrastructure/
      router.py
    campaigns/
      api/
      application/
      domain/
      infrastructure/
      router.py
    ...
  core/
  db/
  main.py
```

Modules should be extracted vertically and incrementally, retaining compatibility imports only while consumers migrate. Once no callers depend on a legacy shim, it can be removed in a dedicated cleanup change.
