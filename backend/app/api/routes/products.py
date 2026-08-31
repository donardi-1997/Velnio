from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from typing import List
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[ProductResponse])
async def list_products(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.workspace_id == workspace.id).order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    return products


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    product = Product(
        workspace_id=workspace.id,
        name=data.name,
        source_type=data.source_type,
        source_url=data.source_url,
        supplier_price=data.supplier_price,
        selling_price=data.selling_price,
        currency=data.currency,
        description=data.description,
        target_country=data.target_country,
        target_language=data.target_language,
        store_id=data.store_id,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")
    await db.delete(product)
    await db.flush()
    return None
