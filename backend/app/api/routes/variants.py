from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.campaign import Campaign
from app.models.landing import LandingPage, LandingSection
from app.models.tracking import LandingVariant
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, BadRequestException
from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID

router = APIRouter()


class VariantCreateRequest(BaseModel):
    name: str
    clone_from_variant_id: Optional[UUID] = None


class VariantUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    traffic_weight: Optional[float] = None
    selling_angle_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None


class TrafficWeightsRequest(BaseModel):
    weights: Dict[str, float]


async def _get_campaign(db: AsyncSession, campaign_id: UUID, workspace_id: UUID) -> Campaign:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")
    return campaign


@router.get("/{campaign_id}/variants")
async def list_variants(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(db, campaign_id, workspace.id)
    result = await db.execute(
        select(LandingVariant).where(LandingVariant.campaign_id == campaign_id).order_by(LandingVariant.variant_key)
    )
    variants = result.scalars().all()
    return [
        {
            "id": str(v.id),
            "campaign_id": str(v.campaign_id),
            "name": v.name,
            "variant_key": v.variant_key,
            "status": v.status,
            "traffic_weight": v.traffic_weight,
            "selling_angle_id": str(v.selling_angle_id) if v.selling_angle_id else None,
            "offer_id": str(v.offer_id) if v.offer_id else None,
            "landing_page_id": str(v.landing_page_id) if v.landing_page_id else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }
        for v in variants
    ]


@router.post("/{campaign_id}/variants", status_code=201)
async def create_variant(
    campaign_id: UUID,
    data: VariantCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(db, campaign_id, workspace.id)

    # Check max active variants
    active_result = await db.execute(
        select(LandingVariant).where(
            LandingVariant.campaign_id == campaign_id,
            LandingVariant.status == "ACTIVE",
        )
    )
    active_count = len(active_result.scalars().all())
    if active_count >= 4:
        raise BadRequestException("Maximum 4 active variants allowed")

    # Generate variant key
    existing_result = await db.execute(
        select(LandingVariant).where(LandingVariant.campaign_id == campaign_id)
    )
    existing_keys = {v.variant_key for v in existing_result.scalars().all()}
    variant_key = None
    for key in ["B", "C", "D", "E"]:
        if key not in existing_keys:
            variant_key = key
            break
    if not variant_key:
        raise BadRequestException("No more variant keys available")

    # Clone from source if specified
    source_variant = None
    landing_page = None
    if data.clone_from_variant_id:
        source_result = await db.execute(
            select(LandingVariant).where(LandingVariant.id == data.clone_from_variant_id)
        )
        source_variant = source_result.scalar_one_or_none()
        if not source_variant:
            raise NotFoundException("Source variant")

        # Clone landing page
        if source_variant.landing_page_id:
            source_lp_result = await db.execute(
                select(LandingPage).where(LandingPage.id == source_variant.landing_page_id)
            )
            source_lp = source_lp_result.scalar_one_or_none()
            if source_lp:
                landing_page = LandingPage(
                    campaign_id=campaign_id,
                    product_id=source_lp.product_id,
                    selling_angle_id=source_lp.selling_angle_id,
                    title=f"{source_lp.title} ({variant_key})",
                    slug=f"{source_lp.slug}-{variant_key.lower()}",
                    status=source_lp.status,
                    version=1,
                )
                db.add(landing_page)
                await db.flush()

                # Clone sections
                sections_result = await db.execute(
                    select(LandingSection).where(LandingSection.landing_page_id == source_lp.id)
                )
                for section in sections_result.scalars().all():
                    new_section = LandingSection(
                        landing_page_id=landing_page.id,
                        section_type=section.section_type,
                        position=section.position,
                        content=section.content.copy() if section.content else {},
                    )
                    db.add(new_section)
                await db.flush()

    variant = LandingVariant(
        campaign_id=campaign_id,
        name=data.name,
        variant_key=variant_key,
        status="DRAFT",
        traffic_weight=0,
        source_variant_id=source_variant.id if source_variant else None,
        selling_angle_id=source_variant.selling_angle_id if source_variant else None,
        offer_id=source_variant.offer_id if source_variant else None,
        landing_page_id=landing_page.id if landing_page else source_variant.landing_page_id if source_variant else None,
    )
    db.add(variant)
    await db.flush()
    await db.refresh(variant)

    return {
        "id": str(variant.id),
        "campaign_id": str(variant.campaign_id),
        "name": variant.name,
        "variant_key": variant.variant_key,
        "status": variant.status,
        "traffic_weight": variant.traffic_weight,
        "selling_angle_id": str(variant.selling_angle_id) if variant.selling_angle_id else None,
        "offer_id": str(variant.offer_id) if variant.offer_id else None,
        "landing_page_id": str(variant.landing_page_id) if variant.landing_page_id else None,
        "created_at": variant.created_at.isoformat() if variant.created_at else None,
        "updated_at": variant.updated_at.isoformat() if variant.updated_at else None,
    }


@router.patch("/{campaign_id}/variants/traffic")
async def update_traffic_weights(
    campaign_id: UUID,
    data: TrafficWeightsRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(db, campaign_id, workspace.id)

    # Validate total weight
    total = sum(data.weights.values())
    if abs(total - 100) > 0.01:
        raise BadRequestException(f"Traffic weights must sum to 100, got {total}")

    # Get all variants
    result = await db.execute(
        select(LandingVariant).where(LandingVariant.campaign_id == campaign_id)
    )
    variants = {str(v.id): v for v in result.scalars().all()}

    # Validate all variant IDs exist
    for vid in data.weights:
        if vid not in variants:
            raise NotFoundException(f"Variant {vid}")

    # Validate non-negative weights
    for vid, weight in data.weights.items():
        if weight < 0:
            raise BadRequestException(f"Weight for {vid} must be >= 0")

    # Update weights
    for vid, weight in data.weights.items():
        variants[vid].traffic_weight = weight
        if weight > 0 and variants[vid].status == "DRAFT":
            variants[vid].status = "ACTIVE"
        elif weight == 0 and variants[vid].status == "ACTIVE":
            variants[vid].status = "PAUSED"

    await db.flush()

    return {"status": "ok", "weights": data.weights}


@router.patch("/{campaign_id}/variants/{variant_id}")
async def update_variant(
    campaign_id: UUID,
    variant_id: UUID,
    data: VariantUpdateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(db, campaign_id, workspace.id)

    result = await db.execute(
        select(LandingVariant).where(
            LandingVariant.id == variant_id,
            LandingVariant.campaign_id == campaign_id,
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundException("Variant")

    if data.name is not None:
        variant.name = data.name
    if data.status is not None:
        if data.status not in ["DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"]:
            raise BadRequestException("Invalid status")
        variant.status = data.status
    if data.traffic_weight is not None:
        variant.traffic_weight = data.traffic_weight
    if data.selling_angle_id is not None:
        variant.selling_angle_id = data.selling_angle_id
    if data.offer_id is not None:
        variant.offer_id = data.offer_id

    await db.flush()
    await db.refresh(variant)

    return {
        "id": str(variant.id),
        "campaign_id": str(variant.campaign_id),
        "name": variant.name,
        "variant_key": variant.variant_key,
        "status": variant.status,
        "traffic_weight": variant.traffic_weight,
        "selling_angle_id": str(variant.selling_angle_id) if variant.selling_angle_id else None,
        "offer_id": str(variant.offer_id) if variant.offer_id else None,
        "landing_page_id": str(variant.landing_page_id) if variant.landing_page_id else None,
        "created_at": variant.created_at.isoformat() if variant.created_at else None,
        "updated_at": variant.updated_at.isoformat() if variant.updated_at else None,
    }


@router.delete("/{campaign_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    campaign_id: UUID,
    variant_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign(db, campaign_id, workspace.id)

    result = await db.execute(
        select(LandingVariant).where(
            LandingVariant.id == variant_id,
            LandingVariant.campaign_id == campaign_id,
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundException("Variant")

    await db.delete(variant)
    await db.flush()
    return None
