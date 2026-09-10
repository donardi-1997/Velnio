from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.catalog.application.products import ProductService
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter()


def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


@router.get("", response_model=List[ProductResponse])
async def list_products(
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductService = Depends(get_product_service),
):
    return await service.list(workspace.id)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductService = Depends(get_product_service),
):
    return await service.create(data, workspace.id)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductService = Depends(get_product_service),
):
    return await service.get(product_id, workspace.id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductService = Depends(get_product_service),
):
    return await service.update(product_id, data, workspace.id)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductService = Depends(get_product_service),
):
    await service.delete(product_id, workspace.id)
    return None
