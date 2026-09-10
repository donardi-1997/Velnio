# Backend Architecture

Velnio is organized as a **modular monolith**. The application is deployed as one FastAPI service and one database, while business capabilities are composed through explicit module boundaries.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | Authentication, users, workspace membership and tenant context |
| `catalog` | Products, product analysis, imports and enrichment |
| `campaigns` | Campaigns, selling angles, offers, landings, visual assets, publishing, variants and experiments |
| `commerce` | Stores and Shopify-facing commerce capabilities |
| `knowledge` | Knowledge sources and campaign briefs/context |
| `integrations` | External non-commerce connectors such as Google Drive |
| `billing` | Plans, subscriptions, credits and credit ledger |
| `analytics` | Dashboard, event tracking and campaign performance |

## Composition rule

`app.main` is the composition root. It configures FastAPI and mounts only `app.modules.router.api_router`. The module router composes the business modules; each module owns its URL composition and tags.

Legacy route modules are retained only as compatibility shims while callers migrate. New implementation code must live inside the owning module.

## Dependency rules

1. A module may depend on `app.core` and `app.db` infrastructure.
2. HTTP composition belongs to the owning module.
3. New business logic lives inside the owning module, not in a global service bucket.
4. Cross-module calls use explicit application services/interfaces, never another module's HTTP handlers.
5. Database migrations remain centralized under Alembic because Velnio is still one deployable and one database.
6. Public endpoint paths remain backward compatible unless a versioned API change is intentional.
7. `app.main` must not import individual feature route files.
8. Routers are adapters: orchestration, credit accounting, persistence workflows and provider calls belong in application/infrastructure layers.

## Target internal shape

```text
app/
  modules/
    catalog/
      router.py
      api/
      application/
      domain/
      infrastructure/
    campaigns/
      router.py
      api/
      application/
      domain/
      infrastructure/
      tests/
    ...
  core/
  db/
  main.py
```

## Campaigns extraction status

Campaigns is the first vertically extracted module.

HTTP ownership is now under `app.modules.campaigns.api` for:

- campaign CRUD and product-scoped campaign creation/listing
- selling angles
- offers
- campaign landings
- publishing and publish readiness
- campaign brief generation
- visual direction and launch-pack assets
- A/B landing variants
- demo event endpoints

Application orchestration now lives under `app.modules.campaigns.application` for:

- campaign lifecycle (`CampaignService`)
- angles (`CampaignAngleService`)
- offers (`CampaignOfferService`)
- landings (`CampaignLandingService`)
- publishing (`CampaignPublishingService`)
- briefs (`CampaignBriefService`)
- variants (`CampaignVariantService`)
- visual assets (`CampaignVisualAssetService`)

`app/api/routes/campaigns.py`, `publish.py`, `visual_assets.py`, `variants.py`, and `demo.py` are compatibility shims rather than implementation owners.

Campaign route-contract tests protect the public surface against missing or duplicated routes during subsequent modular extraction.

## Next module

The next vertical extraction is `catalog`, beginning with products, product analysis, import and enrichment. Existing public API paths remain unchanged throughout the migration.
