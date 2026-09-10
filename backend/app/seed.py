"""Seed script for Velnio"""
import asyncio
import uuid
from datetime import datetime, timezone
from app.db.session import async_session
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from app.models.store import Store, StorePlatform, StoreStatus
from app.models.product import Product, ProductStatus, SourceType, ImageSourceType, ImagePurpose, ProductImage
from app.models.campaign import Campaign, CampaignStatus
from app.models.analysis import ProductAnalysis
from app.models.angle import SellingAngle
from app.models.landing import LandingPage, LandingSection, LandingStatus
from app.models.offer import Offer, OfferType
from app.models.enrichment import ProductEnrichment
from app.models.visual_direction import CampaignVisualDirection
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from sqlalchemy import select, text


async def seed():
    async with async_session() as db:
        try:
            await db.execute(text("SELECT 1"))
            print("Database connected successfully")
        except Exception as e:
            print(f"Database connection failed: {e}")
            return

        result = await db.execute(select(Plan).limit(1))
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        print("Seeding database...")

        plans = [
            Plan(id=uuid.uuid4(), code="FREE", name="Free", monthly_price=0, included_credits=10, max_stores=1, max_products_per_month=2),
            Plan(id=uuid.uuid4(), code="LAUNCH", name="Starter", monthly_price=29, included_credits=100, max_stores=1, max_products_per_month=10),
            Plan(id=uuid.uuid4(), code="GROWTH", name="Growth", monthly_price=79, included_credits=400, max_stores=3, max_products_per_month=30),
            Plan(id=uuid.uuid4(), code="SCALE", name="Scale", monthly_price=149, included_credits=1200, max_stores=10, max_products_per_month=100),
        ]
        for p in plans:
            db.add(p)
        await db.flush()

        user = User(
            id=uuid.uuid4(),
            email="demo@velnio.local",
            password_hash=hash_password("Demo12345!"),
            first_name="Demo",
            last_name="User",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        workspace = Workspace(id=uuid.uuid4(), name="Velnio Demo Store", owner_id=user.id)
        db.add(workspace)
        await db.flush()

        member = WorkspaceMember(id=uuid.uuid4(), workspace_id=workspace.id, user_id=user.id, role=MemberRole.OWNER)
        db.add(member)

        growth_plan = [p for p in plans if p.code == "GROWTH"][0]
        sub = Subscription(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            plan_id=growth_plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
            provider="MOCK",
        )
        db.add(sub)

        wallet = CreditWallet(id=uuid.uuid4(), workspace_id=workspace.id, balance=500, lifetime_credits=500)
        db.add(wallet)
        await db.flush()

        tx = CreditTransaction(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=500,
            transaction_type=TransactionType.ALLOCATION,
            description="Demo credits allocation",
        )
        db.add(tx)

        store = Store(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            name="Demo Shopify Store",
            shop_domain="demo-store.myshopify.com",
            platform=StorePlatform.SHOPIFY,
            status=StoreStatus.CONNECTED,
            access_token_encrypted="mock_token",
            country="US",
            currency="USD",
        )
        db.add(store)
        await db.flush()

        products_data = [
            {
                "name": "Portable Car Vacuum",
                "description": "Compact, powerful car vacuum cleaner for quick cleanups. Removes pet hair, crumbs, and dust easily.",
                "supplier_price": 12.99,
                "selling_price": 34.99,
                "status": ProductStatus.READY,
                "target_country": "US",
                "target_language": "en",
            },
            {
                "name": "Pet Hair Remover",
                "description": "Reusable lint roller for removing pet hair from furniture, clothing, and car seats.",
                "supplier_price": 7.99,
                "selling_price": 24.99,
                "status": ProductStatus.ANALYZED,
                "target_country": "US",
                "target_language": "en",
            },
            {
                "name": "Neck Massager",
                "description": "Electric neck massager with heat therapy for pain relief and relaxation.",
                "supplier_price": 15.99,
                "selling_price": 49.99,
                "status": ProductStatus.DRAFT,
                "target_country": "US",
                "target_language": "en",
            },
        ]

        product_ids = []
        for pdata in products_data:
            product = Product(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                source_type=SourceType.MANUAL,
                country="US",
                target_country=pdata["target_country"],
                target_language=pdata["target_language"],
                currency="USD",
                **{k: v for k, v in pdata.items() if k not in ("target_country", "target_language")},
            )
            db.add(product)
            await db.flush()
            product_ids.append(product.id)

        # Add images to first product
        db.add(ProductImage(
            id=uuid.uuid4(), product_id=product_ids[0], source_type=ImageSourceType.UPLOADED,
            image_url="https://images.unsplash.com/photo-1558317374-067fb5f30001?w=800",
            purpose=ImagePurpose.MAIN, sort_order=0,
        ))
        db.add(ProductImage(
            id=uuid.uuid4(), product_id=product_ids[0], source_type=ImageSourceType.UPLOADED,
            image_url="https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=800",
            purpose=ImagePurpose.GALLERY, sort_order=1,
        ))

        # Analysis for first product
        analysis = ProductAnalysis(
            id=uuid.uuid4(), product_id=product_ids[0], overall_score=87.0,
            demand_score=90, visual_score=85, problem_score=88, margin_score=92,
            saturation_score=75, ad_potential_score=90, impulse_score=82, return_risk_score=70,
            strengths=["Strong profit margin", "Solves a clear pain point", "Highly demonstrable"],
            risks=["Competitive niche", "Requires strong creative differentiation"],
            summary="Strong product opportunity with excellent margins and visual ad potential.",
        )
        db.add(analysis)

        # Create a campaign for the first product
        campaign = Campaign(
            id=uuid.uuid4(), workspace_id=workspace.id, product_id=product_ids[0],
            name="Car Vacuum - US Launch", target_country="US", target_language="en",
            currency="USD", selling_price=34.99, supplier_price=12.99,
            status=CampaignStatus.OFFER_READY,
        )
        db.add(campaign)
        await db.flush()

        # Selling angles
        angles_data = [
            ("Pet Hair Problem", "Pet owners", "Stop fighting pet hair in your car", "problem_solution", 92),
            ("60-Second Clean", "Busy professionals", "A spotless car before your next meeting", "convenience", 88),
            ("Family Mess", "Parents", "Kids make the mess. This cleans it fast.", "problem_solution", 85),
        ]
        angle_ids = []
        for idx, (name, audience, hook, angle_type, score) in enumerate(angles_data):
            angle = SellingAngle(
                id=uuid.uuid4(), product_id=product_ids[0], campaign_id=campaign.id,
                name=name, target_audience=audience, pain_point="Car interior gets dirty fast",
                desire="Keep the car clean effortlessly", core_benefit="Powerful portable cleaning",
                hook=hook, proof_idea="Before/after demonstration", angle_type=angle_type,
                score=score, rank=idx + 1, is_selected=idx == 0,
            )
            db.add(angle)
            angle_ids.append(angle.id)
        await db.flush()

        campaign.selected_angle_id = angle_ids[0]

        offer = Offer(
            id=uuid.uuid4(), campaign_id=campaign.id, product_id=product_ids[0],
            offer_type=OfferType.PERCENTAGE_DISCOUNT, headline="20% OFF Today Only",
            subheadline="Get a spotless car in minutes — without the car wash.",
            cta_text="Get Mine Now", regular_price=44.99, sale_price=34.99,
            discount_percentage=22, urgency_text="Limited stock available",
            guarantee_text="30-day money-back guarantee",
        )
        db.add(offer)
        await db.flush()
        campaign.offer_id = offer.id

        # Landing page
        landing = LandingPage(
            id=uuid.uuid4(), product_id=product_ids[0], campaign_id=campaign.id,
            title="Portable Car Vacuum — Clean Smarter", theme="modern", status=LandingStatus.DRAFT,
        )
        db.add(landing)
        await db.flush()
        sections = [
            ("HERO", 0, {"headline": "Your Car. Spotless. In 60 Seconds.", "subheadline": "Powerful suction. Cordless freedom. Zero excuses.", "cta": "Get 20% OFF"}),
            ("BENEFITS", 1, {"title": "Why Drivers Love It", "items": ["Powerful 120W suction", "Cordless & rechargeable", "Washable HEPA filter", "Fits in your glove box"]}),
            ("PROBLEM_SOLUTION", 2, {"headline": "Pet Hair. Crumbs. Dust. Gone.", "body": "Stop paying for car washes every week. Clean any mess in minutes."}),
            ("SOCIAL_PROOF", 3, {"headline": "Join 10,000+ Happy Drivers", "rating": 4.8, "reviews": 2341}),
            ("FINAL_CTA", 4, {"headline": "Ready for a Cleaner Car?", "cta": "Get Yours — 20% OFF", "urgency": "Limited stock available"}),
        ]
        for section_type, order, content in sections:
            db.add(LandingSection(
                id=uuid.uuid4(), landing_page_id=landing.id, section_type=section_type,
                sort_order=order, content=content,
            ))

        campaign.landing_page_id = landing.id

        enrichment = ProductEnrichment(
            id=uuid.uuid4(), product_id=product_ids[0],
            features=["120W motor", "Cordless", "Washable HEPA filter", "USB-C charging"],
            benefits=["Clean anywhere", "No tangled cords", "Reusable filter", "Fast charging"],
            use_cases=["Car interiors", "Office desks", "Small spaces"],
            suggested_audiences=["Pet owners", "Parents", "Rideshare drivers", "Car enthusiasts"],
            short_description="A compact cordless vacuum built for fast car cleanups.",
            enriched_description="The Portable Car Vacuum combines strong suction with cordless convenience for effortless everyday cleaning.",
        )
        db.add(enrichment)

        visual = CampaignVisualDirection(
            id=uuid.uuid4(), campaign_id=campaign.id,
            visual_style="Clean, premium automotive lifestyle",
            tone="Modern, confident, practical",
            color_palette=["#0f172a", "#4263eb", "#ffffff", "#e2e8f0"],
            photography_style="Natural lighting, close-up product demonstrations, clean car interiors",
            composition_notes="High contrast product shots with visible before/after results",
        )
        db.add(visual)

        await db.commit()
        print("Seed complete.")
        print("Demo login: demo@velnio.local / Demo12345!")


if __name__ == "__main__":
    asyncio.run(seed())
