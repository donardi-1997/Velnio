from fastapi import APIRouter

from app.modules.analytics.router import router as analytics_router
from app.modules.billing.router import router as billing_router
from app.modules.campaigns.router import router as campaigns_router
from app.modules.catalog.router import router as catalog_router
from app.modules.commerce.router import router as commerce_router
from app.modules.identity.router import router as identity_router
from app.modules.integrations.router import router as integrations_router
from app.modules.knowledge.router import router as knowledge_router

api_router = APIRouter()
api_router.include_router(identity_router)
api_router.include_router(catalog_router)
api_router.include_router(campaigns_router)
api_router.include_router(commerce_router)
api_router.include_router(knowledge_router)
api_router.include_router(integrations_router)
api_router.include_router(billing_router)
api_router.include_router(analytics_router)
