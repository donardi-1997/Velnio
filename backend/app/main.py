from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.session import engine
from app.api.routes import auth, workspace, stores, products, ai, angles, landings, credits, billing, dashboard, shopify, campaigns, product_import, enrichment, visual_assets, publish, tracking, variants, performance, demo, google_drive, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Velnio API",
    description="Turn products into winning campaigns.",
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
app.include_router(stores.router, prefix="/api/stores", tags=["stores"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(ai.router, prefix="/api/products", tags=["ai"])
app.include_router(angles.router, prefix="/api/products", tags=["angles"])
app.include_router(landings.router, prefix="/api/products", tags=["landings"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(credits.router, prefix="/api/credits", tags=["credits"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(shopify.router, prefix="/api/products", tags=["shopify"])
app.include_router(product_import.router, prefix="/api/products", tags=["import"])
app.include_router(enrichment.router, prefix="/api/products", tags=["enrichment"])
app.include_router(visual_assets.router, prefix="/api/campaigns", tags=["visual-assets"])
app.include_router(publish.router, prefix="/api/campaigns", tags=["publish"])
app.include_router(variants.router, prefix="/api/campaigns", tags=["variants"])
app.include_router(performance.router, prefix="/api/campaigns", tags=["performance"])
app.include_router(demo.router, prefix="/api/campaigns", tags=["demo"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["tracking"])
app.include_router(google_drive.router, prefix="/api/google-drive", tags=["google-drive"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Velnio", "version": "0.5.0"}
