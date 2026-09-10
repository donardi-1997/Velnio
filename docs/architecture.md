# Backend Architecture

Velnio is organized as a **modular monolith**. The application is deployed as one FastAPI service and one database, while business capabilities are composed through explicit module boundaries.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | Authentication, users, workspace membership and tenant context |
| `catalog` | Products, product analysis, imports and enrichment |
| `campaigns` | Campaigns, selling angles, landings, visual assets, publishing and experiments |
| `commerce` | Stores and Shopify-facing commerce capabilities |
| `knowledge` | Knowledge sources and campaign briefs |
| `integrations` | External non-commerce connectors such as Google Drive |
| `billing` | Plans, subscriptions, credits and credit ledger |
| `analytics` | Dashboard, event tracking and campaign performance |

## Composition rule

`app.main` is the composition root. It configures FastAPI and mounts only `app.modules.router.api_router`. The module router composes the business modules; each module owns its URL composition and tags.

The existing route handlers remain behind the module boundaries during the migration so public API contracts stay stable. Domain internals should be moved incrementally from the legacy layer into their owning module rather than performing a risky big-bang rewrite.

## Dependency rules

1. A module may depend on `app.core` and `app.db` infrastructure.
2. HTTP composition belongs to the owning module.
3. New business logic should live inside the owning module, not in a global service bucket.
4. Cross-module calls should use explicit service interfaces/application services, not import another module's route handlers.
5. Database migrations remain centralized under Alembic because Velnio is still one deployable and one database.
6. Public endpoint paths must remain backward compatible unless a versioned API change is intentional.
7. `app.main` must not import individual feature route files.

## Target internal shape

```text
app/
  modules/
    catalog/
      router.py
      application/
      domain/
      infrastructure/
    campaigns/
      router.py
      application/
      domain/
      infrastructure/
    ...
  core/
  db/
  main.py
```

This extraction establishes the module boundaries and composition root. Subsequent refactors can move models, schemas, repositories and services module by module while retaining compatibility imports until consumers have migrated.
