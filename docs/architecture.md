# Backend Architecture

Velnio is organized as a **modular monolith**. The application is deployed as one FastAPI service and one database, while business capabilities are composed through explicit module boundaries.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | Authentication, users, workspace membership and tenant context |
| `catalog` | Products, product analysis, imports and enrichment |
| `campaigns` | Campaigns, selling angles, offers, landings, visual assets, publishing, variants and experiments |
| `commerce` | Stores and Shopify-facing commerce capabilities |
| `knowledge` | Knowledge sources and campaign context |
| `integrations` | External non-commerce connectors such as Google Drive |
| `billing` | Plans, subscriptions, credits and credit ledger |
| `analytics` | Dashboard, event tracking and campaign performance |

## Composition rule

`app.main` is the composition root. It configures FastAPI and mounts only `app.modules.router.api_router`. The module router composes the business modules; each module owns its URL composition and tags.

Legacy route modules are retained only as compatibility shims while callers migrate. New implementation code must live inside the owning module.

## Dependency rules

1. A module may depend on `app.core` and `app.db` infrastructure.
2. HTTP composition belongs to the owning module.
3. New business logic lives inside the owning module, not in a global route/service bucket.
4. Cross-module calls use explicit application services/interfaces, never another module's HTTP handlers.
5. Database migrations remain centralized under Alembic because Velnio is still one deployable and one database.
6. Public endpoint paths remain backward compatible unless a versioned API change is intentional.
7. `app.main` must not import individual feature route files.
8. Routers are adapters: orchestration, credit accounting, persistence workflows and provider calls belong in application/infrastructure layers.

## Internal shape

```text
app/
  modules/
    <capability>/
      router.py
      api/
      application/
      infrastructure/
      domain/          # when a dedicated domain boundary is useful
      tests/
  core/
  db/
  main.py
```

## Extraction status

All initially defined capabilities now own their HTTP composition under `app.modules`:

- `identity` — register/login/refresh, current user and workspace context
- `catalog` — product CRUD, analysis, import/create/upload and enrichment
- `campaigns` — CRUD, product-scoped compatibility routes, angles, offers, landings, publishing/readiness, briefs, visual assets, variants and demo flows
- `commerce` — stores and Shopify product publishing
- `knowledge` — knowledge-source CRUD, tenant/entity validation, limits and content hashing
- `billing` — wallet, transactions, plans and subscription lookup
- `analytics` — dashboard, performance analysis and tracking ingestion
- `integrations` — Google Drive connection/token lifecycle, browse/search and image/document/asset imports

The historical `app/api/routes/*` files for extracted capabilities are compatibility shims only.

## Google Drive integration boundary

Google Drive is split into three application services:

- `GoogleDriveConnectionService` — status, connect/disconnect, token exchange and refresh lifecycle
- `GoogleDriveBrowserService` — browse and search
- `GoogleDriveImportService` — image, document and campaign-asset imports plus product-document listing

The FastAPI adapter contains only request/response wiring and redirect behavior.

## Verification strategy

Each extracted module has route-contract coverage where applicable. A global composition contract verifies that the composed API does not contain duplicate method/path pairs and that all primary module prefixes are mounted.

GitHub Actions runs the backend suite with Python 3.12 and mock providers using:

```bash
pytest app/tests app/modules -q
```

No schema or Alembic migration change is part of this refactor.
