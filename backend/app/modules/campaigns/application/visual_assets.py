import math
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger
from app.models.angle import SellingAngle
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.offer import Offer
from app.models.product import ImagePurpose, ImageSourceType, Product, ProductImage
from app.models.visual_direction import CampaignVisualDirection
from app.services.images import get_image_provider
from app.services.images.prompts import VisualDirection, generate_visual_direction_prompt

logger = get_logger(__name__)


class CampaignVisualAssetService:
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

    async def _get_generation_context(self, campaign: Campaign):
        result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")

        result = await self.db.execute(
            select(SellingAngle).where(
                SellingAngle.campaign_id == campaign.id,
                SellingAngle.selected == True,
            )
        )
        angle = result.scalar_one_or_none()

        result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign.id))
        offer = result.scalar_one_or_none()

        result = await self.db.execute(
            select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign.id)
        )
        direction = result.scalar_one_or_none()

        visual_direction = None
        if direction:
            visual_direction = VisualDirection(
                visual_style=direction.visual_style,
                tone=direction.tone,
                color_notes=direction.color_notes,
                background_style=direction.background_style or "",
                photography_style=direction.photography_style or "",
                audience_context=direction.audience_context or "",
                additional_instructions=direction.additional_instructions or "",
            )

        return product, angle, offer, visual_direction

    async def _next_asset_position(self, campaign_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(ProductImage.position)).where(ProductImage.campaign_id == campaign_id)
        )
        current_max = result.scalar_one_or_none()
        return (current_max if current_max is not None else -1) + 1

    @staticmethod
    def _with_regeneration_instructions(
        visual_direction: Optional[VisualDirection], instructions: Optional[str]
    ) -> VisualDirection:
        direction = visual_direction or VisualDirection()
        existing = (direction.additional_instructions or "").strip()
        variation = (
            "Create a clearly distinct alternative composition for this asset while preserving "
            "the campaign message, product identity, and requested asset purpose."
        )
        if instructions:
            variation += f" Regeneration request: {instructions.strip()}"
        combined = " ".join(part for part in (existing, variation) if part)
        return VisualDirection(
            visual_style=direction.visual_style,
            tone=direction.tone,
            color_notes=direction.color_notes,
            background_style=direction.background_style,
            photography_style=direction.photography_style,
            audience_context=direction.audience_context,
            additional_instructions=combined,
        )

    async def _create_generated_asset(
        self,
        *,
        product: Product,
        campaign: Campaign,
        angle,
        offer,
        visual_direction: Optional[VisualDirection],
        purpose: ImagePurpose,
        position: int,
    ) -> ProductImage:
        provider = get_image_provider()
        generation = await provider.generate_campaign_asset(
            product,
            campaign,
            angle,
            offer,
            visual_direction,
            purpose.value,
        )
        image_url = generation.get("image_url")
        if not image_url:
            raise ValueError("Image provider returned no image_url")

        image = ProductImage(
            product_id=product.id,
            campaign_id=campaign.id,
            image_url=image_url,
            source_type=ImageSourceType.AI_GENERATED.value,
            purpose=purpose.value,
            prompt=generation.get("prompt"),
            generation_provider=generation.get("provider", settings.IMAGE_PROVIDER),
            generation_model=generation.get("model"),
            width=generation.get("width"),
            height=generation.get("height"),
            generated_by_ai="true",
            selected=False,
            position=position,
        )
        self.db.add(image)
        return image

    async def generate_visual_direction(self, campaign_id: UUID, workspace_id: UUID):
        campaign = await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")

        result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = result.scalar_one_or_none()
        if not wallet or wallet.balance < settings.PLAN_VISUAL_DIRECTION_COST:
            raise InsufficientCreditsException()

        result = await self.db.execute(
            select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await self.db.delete(existing)
            await self.db.flush()

        try:
            data = generate_visual_direction_prompt(product, campaign)
            direction = CampaignVisualDirection(
                campaign_id=campaign_id,
                visual_style=data["visual_style"],
                tone=data["tone"],
                color_notes=data.get("color_notes"),
                background_style=data.get("background_style"),
                photography_style=data.get("photography_style"),
                audience_context=data.get("audience_context"),
                additional_instructions=data.get("additional_instructions"),
            )
            self.db.add(direction)
            wallet.balance -= settings.PLAN_VISUAL_DIRECTION_COST
            self.db.add(
                CreditTransaction(
                    workspace_id=workspace_id,
                    wallet_id=wallet.id,
                    amount=-settings.PLAN_VISUAL_DIRECTION_COST,
                    transaction_type=TransactionType.USAGE,
                    description="Generate visual direction",
                    reference_type="visual_direction",
                    reference_id=campaign_id,
                )
            )
            await self.db.flush()
            await self.db.refresh(direction)
            return direction
        except InsufficientCreditsException:
            raise
        except Exception as exc:
            logger.error(f"Visual direction generation failed: {exc}")
            raise BadRequestException("Visual direction generation failed.")

    async def get_visual_direction(self, campaign_id: UUID, workspace_id: UUID):
        await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
            select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id)
        )
        direction = result.scalar_one_or_none()
        if not direction:
            raise NotFoundException("Visual direction not found")
        return direction

    async def update_visual_direction(self, direction_id: UUID, workspace_id: UUID, data):
        result = await self.db.execute(
            select(CampaignVisualDirection).join(Campaign).where(
                CampaignVisualDirection.id == direction_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        direction = result.scalar_one_or_none()
        if not direction:
            raise NotFoundException("Visual direction")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(direction, key, value)
        await self.db.flush()
        await self.db.refresh(direction)
        return direction

    async def generate_launch_pack(self, campaign_id: UUID, workspace_id: UUID) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)
        product, angle, offer, visual_direction = await self._get_generation_context(campaign)

        result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = result.scalar_one_or_none()
        if not wallet or wallet.balance < settings.PLAN_LAUNCH_PACK_COST:
            raise InsufficientCreditsException()

        purposes = [
            (ImagePurpose.HERO, 1),
            (ImagePurpose.LIFESTYLE, 2),
            (ImagePurpose.PROBLEM, 1),
            (ImagePurpose.SOLUTION, 1),
            (ImagePurpose.BENEFIT, 2),
            (ImagePurpose.COMPARISON, 1),
        ]
        total_requested = sum(count for _, count in purposes)
        position = await self._next_asset_position(campaign_id)
        created_images = []
        failures = []

        try:
            for purpose, count in purposes:
                for _ in range(count):
                    try:
                        image = await self._create_generated_asset(
                            product=product,
                            campaign=campaign,
                            angle=angle,
                            offer=offer,
                            visual_direction=visual_direction,
                            purpose=purpose,
                            position=position + len(created_images),
                        )
                        created_images.append(image)
                    except Exception as exc:
                        logger.error(f"Failed to generate {purpose.value} image: {exc}")
                        failures.append(purpose.value)

            if not created_images:
                raise BadRequestException("Launch pack generation failed: no assets were generated.")

            credits_charged = min(
                settings.PLAN_LAUNCH_PACK_COST,
                math.ceil(
                    settings.PLAN_LAUNCH_PACK_COST * len(created_images) / total_requested
                ),
            )
            if wallet.balance < credits_charged:
                raise InsufficientCreditsException()

            wallet.balance -= credits_charged
            self.db.add(
                CreditTransaction(
                    workspace_id=workspace_id,
                    wallet_id=wallet.id,
                    amount=-credits_charged,
                    transaction_type=TransactionType.USAGE,
                    description=(
                        "Generate Launch Pack"
                        if len(created_images) == total_requested
                        else f"Generate partial Launch Pack ({len(created_images)}/{total_requested})"
                    ),
                    reference_type="campaign_asset",
                    reference_id=campaign_id,
                )
            )
            await self.db.flush()
            for image in created_images:
                await self.db.refresh(image)
            return {
                "status": "generated" if not failures else "partially_generated",
                "count": len(created_images),
                "failed_count": len(failures),
                "failed_purposes": failures,
                "credits_charged": credits_charged,
                "images": [
                    {"id": str(image.id), "purpose": image.purpose, "url": image.image_url}
                    for image in created_images
                ],
            }
        except (InsufficientCreditsException, BadRequestException):
            raise
        except Exception as exc:
            logger.error(f"Launch pack generation failed: {exc}")
            raise BadRequestException("Launch pack generation failed.")

    async def regenerate_asset(
        self,
        campaign_id: UUID,
        image_id: UUID,
        workspace_id: UUID,
        instructions: Optional[str] = None,
    ) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.campaign_id == campaign_id,
            )
        )
        source_image = result.scalar_one_or_none()
        if not source_image:
            raise NotFoundException("Image")

        try:
            purpose = ImagePurpose(source_image.purpose)
        except ValueError as exc:
            raise BadRequestException("Asset purpose cannot be regenerated.") from exc

        result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = result.scalar_one_or_none()
        if not wallet or wallet.balance < settings.PLAN_IMAGE_COST:
            raise InsufficientCreditsException()

        product, angle, offer, visual_direction = await self._get_generation_context(campaign)
        regeneration_direction = self._with_regeneration_instructions(
            visual_direction, instructions
        )
        position = await self._next_asset_position(campaign_id)

        try:
            image = await self._create_generated_asset(
                product=product,
                campaign=campaign,
                angle=angle,
                offer=offer,
                visual_direction=regeneration_direction,
                purpose=purpose,
                position=position,
            )

            wallet.balance -= settings.PLAN_IMAGE_COST
            self.db.add(
                CreditTransaction(
                    workspace_id=workspace_id,
                    wallet_id=wallet.id,
                    amount=-settings.PLAN_IMAGE_COST,
                    transaction_type=TransactionType.USAGE,
                    description=f"Regenerate {purpose.value} campaign asset",
                    reference_type="campaign_asset_regeneration",
                    reference_id=image_id,
                )
            )
            await self.db.flush()
            await self.db.refresh(image)
            return {
                "status": "regenerated",
                "source_image_id": str(source_image.id),
                "credits_charged": settings.PLAN_IMAGE_COST,
                "image": {
                    "id": str(image.id),
                    "purpose": image.purpose,
                    "url": image.image_url,
                    "selected": image.selected,
                    "prompt": image.prompt,
                },
            }
        except InsufficientCreditsException:
            raise
        except Exception as exc:
            logger.error(f"Asset regeneration failed for image {image_id}: {exc}")
            raise BadRequestException("Asset regeneration failed.")

    async def select_asset(self, campaign_id: UUID, image_id: UUID, purpose: str, workspace_id: UUID) -> dict:
        await self._get_campaign(campaign_id, workspace_id)
        result = await self.db.execute(
            select(ProductImage).where(ProductImage.id == image_id, ProductImage.campaign_id == campaign_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            raise NotFoundException("Image")

        await self.db.execute(
            sa_update(ProductImage).where(
                ProductImage.campaign_id == campaign_id,
                ProductImage.purpose == purpose,
            ).values(selected=False)
        )
        image.selected = True
        image.purpose = purpose
        await self.db.flush()
        return {"status": "selected", "image_id": str(image.id), "purpose": purpose}
