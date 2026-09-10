from typing import Sequence
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadGatewayException,
    BadRequestException,
    InsufficientCreditsException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.models.angle import SellingAngle
from app.models.campaign import CampaignStatus
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.product import Product
from app.modules.campaigns.infrastructure import CampaignRepository
from app.services.ai import get_ai_provider
from app.services.knowledge.context_builder import KnowledgeContextBuilder

logger = get_logger(__name__)


class CampaignAngleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)

    async def list(self, campaign_id: UUID, workspace_id: UUID) -> Sequence[SellingAngle]:
        campaign = await self.campaigns.get_for_workspace(campaign_id, workspace_id)
        if campaign is None:
            raise NotFoundException("Campaign")
        result = await self.db.execute(
            select(SellingAngle).where(SellingAngle.campaign_id == campaign_id).order_by(SellingAngle.position)
        )
        return result.scalars().all()

    async def generate(self, campaign_id: UUID, workspace_id: UUID) -> Sequence[SellingAngle]:
        campaign = await self.campaigns.get_for_workspace(campaign_id, workspace_id)
        if campaign is None:
            raise NotFoundException("Campaign")

        product_result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = product_result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")

        wallet_result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None or wallet.balance < settings.PLAN_ANGLES_COST:
            raise InsufficientCreditsException()

        try:
            knowledge_context = await KnowledgeContextBuilder().build(
                db=self.db,
                product_id=product.id,
                campaign_id=campaign.id,
                workspace_id=workspace_id,
            )
            angles_data = await get_ai_provider().generate_selling_angles_for_campaign(
                product, campaign, knowledge_context
            )

            existing_result = await self.db.execute(select(SellingAngle).where(SellingAngle.campaign_id == campaign_id))
            for old_angle in existing_result.scalars().all():
                await self.db.delete(old_angle)
            await self.db.flush()

            created_angles = []
            for i, angle_data in enumerate(angles_data):
                angle = SellingAngle(
                    campaign_id=campaign_id,
                    product_id=product.id,
                    name=angle_data["name"],
                    target_audience=angle_data["target_audience"],
                    pain_point=angle_data["pain_point"],
                    main_promise=angle_data["main_promise"],
                    hook=angle_data["hook"],
                    description=angle_data["description"],
                    score=angle_data["score"],
                    position=i + 1,
                    selected=False,
                )
                self.db.add(angle)
                created_angles.append(angle)

            wallet.balance -= settings.PLAN_ANGLES_COST
            self.db.add(CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_ANGLES_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate selling angles",
                reference_type="selling_angles",
                reference_id=campaign_id,
            ))
            if campaign.status == CampaignStatus.DRAFT:
                campaign.status = CampaignStatus.ANGLE_READY

            await self.db.flush()
            for angle in created_angles:
                await self.db.refresh(angle)
            return created_angles
        except (InsufficientCreditsException, BadGatewayException):
            raise
        except Exception as exc:
            logger.error("Angle generation failed type=%s", type(exc).__name__)
            raise BadRequestException("Angle generation failed. Please try again.") from exc

    async def select(self, campaign_id: UUID, angle_id: UUID, workspace_id: UUID) -> SellingAngle:
        campaign = await self.campaigns.get_for_workspace(campaign_id, workspace_id)
        if campaign is None:
            raise NotFoundException("Campaign")

        angle_result = await self.db.execute(
            select(SellingAngle).where(SellingAngle.id == angle_id, SellingAngle.campaign_id == campaign_id)
        )
        angle = angle_result.scalar_one_or_none()
        if angle is None:
            raise NotFoundException("Angle")

        await self.db.execute(
            sa_update(SellingAngle).where(SellingAngle.campaign_id == campaign_id).values(selected=False)
        )
        angle.selected = True
        if campaign.status in [CampaignStatus.DRAFT, CampaignStatus.ANALYZING]:
            campaign.status = CampaignStatus.ANGLE_READY

        await self.db.flush()
        await self.db.refresh(angle)
        return angle
