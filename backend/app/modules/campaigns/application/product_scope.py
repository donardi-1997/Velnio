from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign, CampaignStatus
from app.models.landing import LandingPage, LandingSection
from app.models.product import Product
from app.modules.campaigns.application.angles import CampaignAngleService
from app.modules.campaigns.application.landings import CampaignLandingService


class ProductScopedCampaignService:
    """Compatibility application service for campaign workflows exposed under /products."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.angles = CampaignAngleService(db)
        self.landings = CampaignLandingService(db)

    async def _get_product(self, product_id: UUID, workspace_id: UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == workspace_id,
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")
        return product

    async def _get_campaign(
        self,
        product_id: UUID,
        workspace_id: UUID,
        *,
        create_default: bool,
    ) -> Campaign:
        product = await self._get_product(product_id, workspace_id)
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.product_id == product_id,
                Campaign.workspace_id == workspace_id,
            )
            .limit(1)
        )
        campaign = result.scalar_one_or_none()
        if campaign is not None:
            return campaign
        if not create_default:
            raise NotFoundException("No campaign found for this product")

        campaign = Campaign(
            workspace_id=workspace_id,
            product_id=product_id,
            name=f"Default Campaign - {product.target_country}",
            target_country=product.target_country,
            target_language=product.target_language,
            currency=product.currency,
            selling_price=product.selling_price,
            supplier_price=product.supplier_price,
            status=CampaignStatus.DRAFT,
        )
        self.db.add(campaign)
        await self.db.flush()
        return campaign

    async def list_angles(self, product_id: UUID, workspace_id: UUID):
        campaign = await self._get_campaign(product_id, workspace_id, create_default=True)
        return await self.angles.list(campaign.id, workspace_id)

    async def generate_angles(self, product_id: UUID, workspace_id: UUID):
        campaign = await self._get_campaign(product_id, workspace_id, create_default=True)
        return await self.angles.generate(campaign.id, workspace_id)

    async def select_angle(self, product_id: UUID, angle_id: UUID, workspace_id: UUID):
        campaign = await self._get_campaign(product_id, workspace_id, create_default=True)
        return await self.angles.select(campaign.id, angle_id, workspace_id)

    async def get_landing(self, product_id: UUID, workspace_id: UUID) -> LandingPage:
        campaign = await self._get_campaign(product_id, workspace_id, create_default=False)
        return await self.landings.get(campaign.id, workspace_id)

    async def generate_landing(self, product_id: UUID, workspace_id: UUID) -> LandingPage:
        await self._get_product(product_id, workspace_id)
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.product_id == product_id,
                Campaign.workspace_id == workspace_id,
            )
            .limit(1)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise BadRequestException("Create a campaign first")
        return await self.landings.generate(campaign.id, workspace_id)

    async def get_section(self, section_id: UUID, workspace_id: UUID) -> LandingSection:
        result = await self.db.execute(
            select(LandingSection)
            .join(LandingPage)
            .join(Campaign)
            .where(
                LandingSection.id == section_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        section = result.scalar_one_or_none()
        if section is None:
            raise NotFoundException("Landing section")
        return section

    async def update_section(self, section_id: UUID, content: dict, workspace_id: UUID) -> LandingSection:
        section = await self.get_section(section_id, workspace_id)
        section.content = content
        await self.db.flush()
        await self.db.refresh(section)
        return section

    async def update_landing(self, landing_id: UUID, data, workspace_id: UUID) -> LandingPage:
        result = await self.db.execute(
            select(LandingPage)
            .join(Campaign)
            .where(
                LandingPage.id == landing_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        landing = result.scalar_one_or_none()
        if landing is None:
            raise NotFoundException("Landing page")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(landing, key, value)
        await self.db.flush()
        await self.db.refresh(landing)
        return landing
