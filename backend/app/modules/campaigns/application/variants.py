from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.landing import LandingPage, LandingSection
from app.models.tracking import LandingVariant


class CampaignVariantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundException("Campaign")
        return campaign

    @staticmethod
    def serialize(variant: LandingVariant) -> dict:
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

    async def list(self, campaign_id: UUID, workspace_id: UUID) -> list[dict]:
        await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
            select(LandingVariant)
            .where(LandingVariant.campaign_id == campaign_id)
            .order_by(LandingVariant.variant_key)
        )
        return [self.serialize(item) for item in result.scalars().all()]

    async def create(self, campaign_id: UUID, workspace_id: UUID, name: str, clone_from_variant_id: UUID | None) -> dict:
        await self._get_campaign(campaign_id, workspace_id)

        result = await self.db.execute(
            select(LandingVariant).where(
                LandingVariant.campaign_id == campaign_id,
                LandingVariant.status == "ACTIVE",
            )
        )
        if len(result.scalars().all()) >= 4:
            raise BadRequestException("Maximum 4 active variants allowed")

        result = await self.db.execute(select(LandingVariant).where(LandingVariant.campaign_id == campaign_id))
        existing_keys = {item.variant_key for item in result.scalars().all()}
        variant_key = next((key for key in ["B", "C", "D", "E"] if key not in existing_keys), None)
        if not variant_key:
            raise BadRequestException("No more variant keys available")

        source_variant = None
        landing_page = None
        if clone_from_variant_id:
            result = await self.db.execute(
                select(LandingVariant).where(
                    LandingVariant.id == clone_from_variant_id,
                    LandingVariant.campaign_id == campaign_id,
                )
            )
            source_variant = result.scalar_one_or_none()
            if not source_variant:
                raise NotFoundException("Source variant")

            if source_variant.landing_page_id:
                result = await self.db.execute(
                    select(LandingPage).where(LandingPage.id == source_variant.landing_page_id)
                )
                source_page = result.scalar_one_or_none()
                if source_page:
                    landing_page = LandingPage(
                        campaign_id=campaign_id,
                        product_id=source_page.product_id,
                        selling_angle_id=source_page.selling_angle_id,
                        title=f"{source_page.title} ({variant_key})",
                        slug=f"{source_page.slug}-{variant_key.lower()}",
                        status=source_page.status,
                        version=1,
                    )
                    self.db.add(landing_page)
                    await self.db.flush()

                    result = await self.db.execute(
                        select(LandingSection).where(LandingSection.landing_page_id == source_page.id)
                    )
                    for section in result.scalars().all():
                        self.db.add(
                            LandingSection(
                                landing_page_id=landing_page.id,
                                section_type=section.section_type,
                                position=section.position,
                                content=section.content.copy() if section.content else {},
                            )
                        )
                    await self.db.flush()

        variant = LandingVariant(
            campaign_id=campaign_id,
            name=name,
            variant_key=variant_key,
            status="DRAFT",
            traffic_weight=0,
            source_variant_id=source_variant.id if source_variant else None,
            selling_angle_id=source_variant.selling_angle_id if source_variant else None,
            offer_id=source_variant.offer_id if source_variant else None,
            landing_page_id=landing_page.id if landing_page else source_variant.landing_page_id if source_variant else None,
        )
        self.db.add(variant)
        await self.db.flush()
        await self.db.refresh(variant)
        return self.serialize(variant)

    async def update_traffic(self, campaign_id: UUID, workspace_id: UUID, weights: dict[str, float]) -> dict:
        await self._get_campaign(campaign_id, workspace_id)
        total = sum(weights.values())
        if abs(total - 100) > 0.01:
            raise BadRequestException(f"Traffic weights must sum to 100, got {total}")

        result = await self.db.execute(select(LandingVariant).where(LandingVariant.campaign_id == campaign_id))
        variants = {str(item.id): item for item in result.scalars().all()}

        for variant_id, weight in weights.items():
            variant = variants.get(variant_id)
            if variant is None:
                raise NotFoundException(f"Variant {variant_id}")
            if variant.status == "ARCHIVED":
                raise BadRequestException(f"Archived variant {variant_id} cannot receive traffic")
            if weight < 0 or weight > 100:
                raise BadRequestException(f"Weight for {variant_id} must be between 0 and 100")

        resolved_weights: dict[str, float] = {}
        for variant_id, variant in variants.items():
            if variant.status == "ARCHIVED":
                continue
            weight = float(weights.get(variant_id, 0))
            variant.traffic_weight = weight
            if weight > 0 and variant.status in {"DRAFT", "PAUSED"}:
                variant.status = "ACTIVE"
            elif weight == 0 and variant.status == "ACTIVE":
                variant.status = "PAUSED"
            resolved_weights[variant_id] = weight

        await self.db.flush()
        return {"status": "ok", "weights": resolved_weights}

    async def update(self, campaign_id: UUID, variant_id: UUID, workspace_id: UUID, data) -> dict:
        await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
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

        await self.db.flush()
        await self.db.refresh(variant)
        return self.serialize(variant)

    async def delete(self, campaign_id: UUID, variant_id: UUID, workspace_id: UUID) -> None:
        await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
            select(LandingVariant).where(
                LandingVariant.id == variant_id,
                LandingVariant.campaign_id == campaign_id,
            )
        )
        variant = result.scalar_one_or_none()
        if not variant:
            raise NotFoundException("Variant")
        await self.db.delete(variant)
        await self.db.flush()
