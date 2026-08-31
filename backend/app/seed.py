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
            Plan(id=uuid.uuid4(), code="LAUNCH", name="Launch", monthly_price=19, included_credits=100, max_stores=1, max_products_per_month=10),
            Plan(id=uuid.uuid4(), code="GROWTH", name="Growth", monthly_price=49, included_credits=400, max_stores=3, max_products_per_month=30),
            Plan(id=uuid.uuid4(), code="SCALE", name="Scale", monthly_price=99, included_credits=1200, max_stores=10, max_products_per_month=100),
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
            p = Product(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                store_id=store.id,
                **pdata,
            )
            db.add(p)
            product_ids.append(p.id)
        await db.flush()

        analysis = ProductAnalysis(
            id=uuid.uuid4(),
            product_id=product_ids[0],
            overall_score=84,
            demand_score=8.5,
            visual_score=9.2,
            problem_score=9.0,
            margin_score=8.1,
            saturation_score=5.8,
            ad_potential_score=9.4,
            impulse_score=8.7,
            return_risk_score=6.2,
            summary="Strong product with excellent visual marketing potential. The portable car vacuum solves a real, recurring problem for car owners. High impulse purchase potential.",
            strengths=["High demand in automotive accessories", "Strong visual appeal for social media", "Clear problem-solution product", "Good profit margins"],
            risks=["Moderate market saturation", "Shipping time sensitivity"],
            recommended_price_min=24.99,
            recommended_price_max=44.99,
            generated_at=datetime.now(timezone.utc),
        )
        db.add(analysis)

        angles = [
            SellingAngle(id=uuid.uuid4(), product_id=product_ids[0], name="Pet Hair Problem", target_audience="Pet owners who drive", pain_point="Dog and cat hair gets everywhere in the car and is nearly impossible to remove.", main_promise="Keep your car spotless in minutes without expensive detailing.", hook="Your pet loves riding shotgun. The hair doesn't have to stay.", description="Target pet owners tired of fur on car seats.", score=92, position=1, selected=True),
            SellingAngle(id=uuid.uuid4(), product_id=product_ids[0], name="Busy Parents", target_audience="Parents with young children", pain_point="Kids create constant messes in the car.", main_promise="Restore your car to showroom clean after every trip.", hook="Kids will be kids. Your car doesn't have to show it.", description="Appeals to parents maintaining a clean family vehicle.", score=86, position=2, selected=False),
            SellingAngle(id=uuid.uuid4(), product_id=product_ids[0], name="Rideshare Drivers", target_audience="Uber and Lyft drivers", pain_point="Between rides, the car accumulates dirt affecting ratings.", main_promise="Maintain a 5-star interior between every ride.", hook="Every ride is a new passenger. Keep your rating up.", description="Targets gig economy drivers needing cleanliness.", score=81, position=3, selected=False),
        ]
        for a in angles:
            db.add(a)
        await db.flush()

        landing = LandingPage(
            id=uuid.uuid4(),
            product_id=product_ids[0],
            selling_angle_id=angles[0].id,
            title="Portable Car Vacuum - Official Store",
            slug="portable-car-vacuum",
            status=LandingStatus.READY,
            version=1,
        )
        db.add(landing)
        await db.flush()

        sections = [
            LandingSection(id=uuid.uuid4(), landing_page_id=landing.id, section_type="HERO", position=0, content={"headline": "Your pet loves riding shotgun. The hair doesn't have to stay.", "subheadline": "Keep your car spotless in minutes.", "cta_text": "Get yours today", "image_url": None}),
            LandingSection(id=uuid.uuid4(), landing_page_id=landing.id, section_type="PROBLEM", position=1, content={"title": "The Problem", "description": "Pet hair gets everywhere in your car and standard vacuums can't reach it.", "items": ["Standard vacuums can't reach car seats", "Lint rollers barely make a dent", "Professional detailing is expensive"]}),
            LandingSection(id=uuid.uuid4(), landing_page_id=landing.id, section_type="BENEFITS", position=2, content={"title": "Why Portable Car Vacuum", "items": [{"title": "Powerful Suction", "description": "Removes embedded pet hair and debris.", "icon": "zap"}, {"title": "Compact Design", "description": "Fits in your glove compartment.", "icon": "star"}, {"title": "Cordless", "description": "Wireless convenience for any vehicle.", "icon": "check"}]}),
            LandingSection(id=uuid.uuid4(), landing_page_id=landing.id, section_type="OFFER", position=3, content={"title": "Special Launch Offer", "original_price": "34.99", "discount_price": "24.49", "savings": "10.50", "bonus": "Free shipping", "urgency": "Limited time offer"}),
            LandingSection(id=uuid.uuid4(), landing_page_id=landing.id, section_type="FAQ", position=4, content={"title": "Frequently Asked Questions", "items": [{"question": "How long does shipping take?", "answer": "3-5 business days within the US."}, {"question": "What is your return policy?", "answer": "Full 30-day money-back guarantee."}, {"question": "Is there a warranty?", "answer": "1-year manufacturer warranty."}]}),
        ]
        for s in sections:
            db.add(s)

        campaign = Campaign(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            product_id=product_ids[0],
            store_id=store.id,
            name="US Pet Owners - Summer Launch",
            status=CampaignStatus.LANDING_READY,
            target_country="US",
            target_language="en",
            currency="USD",
            selling_price=34.99,
            supplier_price=12.99,
            target_audience="Pet owners who drive, ages 25-45",
            payment_strategy="COD",
            shipping_strategy="Free standard shipping",
            notes="Primary campaign targeting pet owners in the US market",
        )
        db.add(campaign)
        await db.flush()

        campaign_angles = [
            SellingAngle(id=uuid.uuid4(), campaign_id=campaign.id, product_id=product_ids[0], name="Pet Hair Problem", target_audience="Pet owners who drive", pain_point="Dog and cat hair gets everywhere in the car and is nearly impossible to remove.", main_promise="Keep your car spotless in minutes without expensive detailing.", hook="Your pet loves riding shotgun. The hair doesn't have to stay.", description="Target pet owners tired of fur on car seats.", score=92, position=1, selected=True),
            SellingAngle(id=uuid.uuid4(), campaign_id=campaign.id, product_id=product_ids[0], name="Busy Parents", target_audience="Parents with young children", pain_point="Kids create constant messes in the car.", main_promise="Restore your car to showroom clean after every trip.", hook="Kids will be kids. Your car doesn't have to show it.", description="Appeals to parents maintaining a clean family vehicle.", score=86, position=2, selected=False),
            SellingAngle(id=uuid.uuid4(), campaign_id=campaign.id, product_id=product_ids[0], name="Rideshare Drivers", target_audience="Uber and Lyft drivers", pain_point="Between rides, the car accumulates dirt affecting ratings.", main_promise="Maintain a 5-star interior between every ride.", hook="Every ride is a new passenger. Keep your rating up.", description="Targets gig economy drivers needing cleanliness.", score=81, position=3, selected=False),
        ]
        for a in campaign_angles:
            db.add(a)
        await db.flush()

        offer = Offer(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            headline="Get Your Car Pro-Level Clean for Just $24.49",
            offer_type=OfferType.STANDARD,
            primary_price=24.49,
            compare_at_price=34.99,
            discount_percentage=30,
            free_shipping=True,
            cash_on_delivery=False,
            guarantee_days=30,
            urgency_text="Limited time offer - ends tonight!",
            bonus_text="Free microfiber cleaning cloth included",
        )
        db.add(offer)

        campaign_landing = LandingPage(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            product_id=product_ids[0],
            selling_angle_id=campaign_angles[0].id,
            title="Portable Car Vacuum - Official Store",
            slug="portable-car-vacuum-pet-owners",
            status=LandingStatus.READY,
            version=1,
        )
        db.add(campaign_landing)
        await db.flush()

        campaign_sections = [
            LandingSection(id=uuid.uuid4(), landing_page_id=campaign_landing.id, section_type="HERO", position=0, content={"headline": "Your pet loves riding shotgun. The hair doesn't have to stay.", "subheadline": "Keep your car spotless in minutes.", "cta_text": "Get yours today", "image_url": None}),
            LandingSection(id=uuid.uuid4(), landing_page_id=campaign_landing.id, section_type="PROBLEM", position=1, content={"title": "The Problem", "description": "Pet hair gets everywhere in your car and standard vacuums can't reach it.", "items": ["Standard vacuums can't reach car seats", "Lint rollers barely make a dent", "Professional detailing is expensive"]}),
            LandingSection(id=uuid.uuid4(), landing_page_id=campaign_landing.id, section_type="BENEFITS", position=2, content={"title": "Why Portable Car Vacuum", "items": [{"title": "Powerful Suction", "description": "Removes embedded pet hair and debris.", "icon": "zap"}, {"title": "Compact Design", "description": "Fits in your glove compartment.", "icon": "star"}, {"title": "Cordless", "description": "Wireless convenience for any vehicle.", "icon": "check"}]}),
            LandingSection(id=uuid.uuid4(), landing_page_id=campaign_landing.id, section_type="OFFER", position=3, content={"title": "Special Launch Offer", "original_price": "34.99", "discount_price": "24.49", "savings": "10.50", "bonus": "Free shipping + microfiber cloth", "urgency": "Limited time offer - ends tonight!"}),
            LandingSection(id=uuid.uuid4(), landing_page_id=campaign_landing.id, section_type="FAQ", position=4, content={"title": "Frequently Asked Questions", "items": [{"question": "How long does shipping take?", "answer": "3-5 business days within the US."}, {"question": "What is your return policy?", "answer": "Full 30-day money-back guarantee."}, {"question": "Is there a warranty?", "answer": "1-year manufacturer warranty."}]}),
        ]
        for s in campaign_sections:
            db.add(s)

        # V0.3: Enrichment for first product
        enrichment = ProductEnrichment(
            id=uuid.uuid4(),
            product_id=product_ids[0],
            features=[
                "Powerful suction for deep cleaning",
                "Compact cordless design",
                "HEPA filtration system",
                "Multiple attachment heads",
                "Rechargeable battery",
            ],
            benefits=[
                "Keep your car spotless in minutes",
                "No expensive detailing needed",
                "Remove pet hair effortlessly",
                "Professional-grade清洁 results at home",
                "Works on all vehicle types",
            ],
            use_cases=[
                "Pet owners cleaning car interiors",
                "Rideshare drivers maintaining ratings",
                "Parents cleaning up after kids",
                "Daily car maintenance",
            ],
            suggested_audiences=[
                "Pet owners who drive",
                "Uber/Lyft drivers",
                "Parents with young children",
            ],
            short_description="Compact, powerful car vacuum for quick cleanups. Removes pet hair, crumbs, and dust easily.",
            enriched_description="The Portable Car Vacuum is a compact, high-suction cleaning tool designed for quick and thorough car interior cleaning. Featuring HEPA filtration and multiple attachment heads, it easily removes pet hair, crumbs, and dust from seats, carpets, and hard-to-reach areas. Cordless and rechargeable, it's the perfect solution for pet owners, rideshare drivers, and anyone who wants to maintain a spotless vehicle without expensive detailing services.",
        )
        db.add(enrichment)

        # V0.3: Visual direction for campaign
        visual_direction = CampaignVisualDirection(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            visual_style="Modern, clean, conversion-optimized for US market",
            tone="Professional yet approachable, trust-building",
            color_notes="Clean whites, product accent colors, high contrast for mobile",
            background_style="Clean studio or lifestyle context",
            photography_style="High-quality product photography with natural lighting",
            audience_context="Tailored for pet owners who drive, ages 25-45",
            additional_instructions="Focus on Portable Car Vacuum key benefits. Show pet hair removal in action.",
        )
        db.add(visual_direction)

        # V0.3: 8 mock images for the campaign
        mock_images = [
            ("HERO", 0),
            ("LIFESTYLE", 1),
            ("LIFESTYLE", 2),
            ("PROBLEM", 3),
            ("SOLUTION", 4),
            ("BENEFIT", 5),
            ("BENEFIT", 6),
            ("COMPARISON", 7),
        ]
        for purpose_str, pos in mock_images:
            img = ProductImage(
                id=uuid.uuid4(),
                product_id=product_ids[0],
                campaign_id=campaign.id,
                image_url=f"/storage/mock/{purpose_str.lower()}_car_vacuum_{pos}.png",
                image_type="main",
                position=pos,
                generated_by_ai="true",
                source_type="AI_GENERATED",
                purpose=purpose_str,
                storage_key=f"mock/{purpose_str.lower()}_car_vacuum_{pos}.png",
                prompt=f"AI generated {purpose_str.lower()} image for Portable Car Vacuum",
                generation_provider="mock",
                generation_model="dall-e-3",
                width=1200,
                height=628,
                selected=(purpose_str == "HERO"),
            )
            db.add(img)

        # Update campaign status to reflect V0.3 readiness
        campaign.status = CampaignStatus.READY

        await db.commit()
        print("Seed completed successfully!")
        print(f"  User: demo@velnio.local / Demo12345!")
        print(f"  Plans: FREE, LAUNCH, GROWTH, SCALE")
        print(f"  Products: Portable Car Vacuum, Pet Hair Remover, Neck Massager")
        print(f"  Campaign: US Pet Owners - Summer Launch (Ready)")
        print(f"  V0.3: Enrichment, Visual Direction, 8 Launch Pack images")


if __name__ == "__main__":
    asyncio.run(seed())
