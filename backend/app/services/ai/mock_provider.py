from typing import Any, Dict, List
from app.services.ai.base import AIProvider
import hashlib
import uuid


class MockAIProvider(AIProvider):
    async def analyze_product(self, product) -> Dict[str, Any]:
        seed = int(hashlib.md5(product.name.encode()).hexdigest()[:8], 16) % 100
        base = 55 + (seed % 30)

        scores = {
            "demand_score": round(min(10, max(1, base / 10 + (seed % 30 - 15) / 10)), 1),
            "visual_score": round(min(10, max(1, 7.5 + (seed % 25 - 12) / 10)), 1),
            "problem_score": round(min(10, max(1, 7.0 + (seed % 30 - 10) / 10)), 1),
            "margin_score": round(min(10, max(1, 6.5 + (seed % 35 - 10) / 10)), 1),
            "saturation_score": round(min(10, max(1, 5.0 + (seed % 40 - 15) / 10)), 1),
            "ad_potential_score": round(min(10, max(1, 7.5 + (seed % 25 - 10) / 10)), 1),
            "impulse_score": round(min(10, max(1, 6.0 + (seed % 35 - 10) / 10)), 1),
            "return_risk_score": round(min(10, max(1, 3.0 + (seed % 30) / 10)), 1),
        }

        overall = round(sum(scores.values()) / len(scores) * 10, 0)
        overall = min(100, max(0, overall))

        name_lower = product.name.lower()

        strengths = [
            f"High demand potential in {product.target_country} market",
            "Strong visual appeal for social media advertising",
            "Good problem-solving product with clear utility",
        ]
        risks = [
            "Moderate market saturation in this category",
            "Shipping times may affect customer satisfaction",
        ]

        if "pet" in name_lower or "dog" in name_lower or "cat" in name_lower:
            strengths.append("Emotional connection with pet owners drives conversions")
            risks.append("High competition from established pet brands")

        price = product.selling_price or 29.99
        margin = price * 0.4

        return {
            "overall_score": overall,
            **scores,
            "summary": f"Strong product with solid market potential. {product.name} shows good demand indicators and visual marketing potential. The product solves a clear problem, making it ideal for direct-response advertising.",
            "strengths": strengths,
            "risks": risks,
            "recommended_price_min": round(max(price * 0.8, 9.99), 2),
            "recommended_price_max": round(price * 1.3, 2),
        }

    async def generate_selling_angles(self, product) -> List[Dict[str, Any]]:
        return await self._generate_angles(product.name, product.target_country, product.selling_price, None, None)

    async def generate_selling_angles_for_campaign(self, product, campaign, knowledge_context: str = "") -> List[Dict[str, Any]]:
        return await self._generate_angles(
            product.name,
            campaign.target_country,
            campaign.selling_price,
            campaign.target_audience,
            campaign,
        )

    async def _generate_angles(self, name: str, target_country: str, selling_price, target_audience, campaign) -> List[Dict[str, Any]]:
        name_lower = name.lower()
        price = selling_price or 29.99
        country = target_country or "US"
        audience_hint = target_audience or ""

        if "vacuum" in name_lower or "clean" in name_lower:
            return [
                {
                    "name": "Pet Hair Problem",
                    "target_audience": "Pet owners who drive",
                    "pain_point": "Dog and cat hair gets everywhere in the car and is nearly impossible to remove with regular tools.",
                    "main_promise": "Keep your car spotless in minutes without expensive detailing visits.",
                    "hook": "Your pet loves riding shotgun. The hair doesn't have to stay.",
                    "description": "Target pet owners who are tired of seeing fur on their car seats. This angle leverages the emotional frustration of constantly cleaning pet hair and positions the product as an easy, permanent solution.",
                    "score": 92,
                },
                {
                    "name": "Busy Parents",
                    "target_audience": "Parents with young children",
                    "pain_point": "Kids create constant messes in the car - food crumbs, drink spills, and dirt from shoes.",
                    "main_promise": "Restore your car to showroom clean after every family trip.",
                    "hook": "Kids will be kids. Your car doesn't have to show it.",
                    "description": "Appeals to parents who spend a lot of time in the car with children. Positions the product as a time-saving tool for maintaining a clean family vehicle.",
                    "score": 86,
                },
                {
                    "name": "Rideshare Drivers",
                    "target_audience": "Uber and Lyft drivers",
                    "pain_point": "Between rides, the car accumulates dirt and debris from passengers, affecting ratings.",
                    "main_promise": "Maintain a 5-star interior between every single ride.",
                    "hook": "Every ride is a new passenger. Keep your rating up with a clean car.",
                    "description": "Targets gig economy drivers who need to maintain cleanliness for good ratings. Positions the product as a business investment that pays for itself through better tips and ratings.",
                    "score": 81,
                },
            ]
        elif "massag" in name_lower or "neck" in name_lower or "back" in name_lower:
            return [
                {
                    "name": "Desk Worker Relief",
                    "target_audience": "Office workers and remote employees",
                    "pain_point": "Long hours at a desk cause chronic neck and shoulder tension that affects daily life.",
                    "main_promise": "Professional-quality neck relief right at your desk without scheduling appointments.",
                    "hook": "Your neck doesn't wait for the weekend. Neither should you.",
                    "description": "Targets the massive market of desk-bound workers who experience daily discomfort. Positions the massager as an essential office wellness tool.",
                    "score": 90,
                },
                {
                    "name": "Post-Workout Recovery",
                    "target_audience": "Fitness enthusiasts and athletes",
                    "pain_point": "Muscle tension and soreness after workouts slow recovery and reduce performance.",
                    "main_promise": "Speed up recovery and feel relief in minutes after any workout.",
                    "hook": "The gym works your muscles. This works out the tension.",
                    "description": "Appeals to the fitness community by positioning the massager as a recovery tool that complements their existing workout routine.",
                    "score": 85,
                },
                {
                    "name": "Chronic Pain Management",
                    "target_audience": "People with chronic neck or back pain",
                    "pain_point": "Daily pain management is expensive with frequent visits to massage therapists or chiropractors.",
                    "main_promise": "Affordable daily pain relief without recurring appointment costs.",
                    "hook": "Stop paying per session. Own your relief.",
                    "description": "Addresses the financial pain point of ongoing pain management. Positions the product as a one-time investment replacing recurring expenses.",
                    "score": 88,
                },
            ]
        else:
            return [
                {
                    "name": "Convenience Seekers",
                    "target_audience": "Busy professionals",
                    "pain_point": "Finding time to deal with everyday problems is difficult with a packed schedule.",
                    "main_promise": "Solve this problem in minutes without disrupting your day.",
                    "hook": "Life is complicated. This doesn't have to be.",
                    "description": "Targets busy people who value convenience above all. The product is positioned as a quick, efficient solution that respects their time.",
                    "score": 87,
                },
                {
                    "name": "Quality Conscious",
                    "target_audience": "Value-driven shoppers",
                    "pain_point": "Cheap alternatives break quickly, leading to repeated purchases and frustration.",
                    "main_promise": "A premium solution that lasts, saving money long-term.",
                    "hook": "Buy once. Use forever.",
                    "description": "Appeals to shoppers who have been burned by low-quality alternatives. Positions the product as the smart, long-term choice.",
                    "score": 84,
                },
                {
                    "name": "Gift Givers",
                    "target_audience": "People shopping for gifts",
                    "pain_point": "Finding unique, practical gifts that people actually want and use is incredibly difficult.",
                    "main_promise": "The gift they'll actually use every day.",
                    "hook": "Give them something they'll never put in a closet.",
                    "description": "Positions the product as a thoughtful, practical gift. Ideal for seasonal marketing around holidays and special occasions.",
                    "score": 79,
                },
            ]

    async def generate_offer(self, product, campaign, analysis, angle) -> Dict[str, Any]:
        price = campaign.selling_price or product.selling_price or 29.99
        supplier_price = campaign.supplier_price or product.supplier_price or 9.99
        currency = campaign.currency or "USD"
        discount_price = round(price * 0.7, 2)
        compare_at = round(price * 1.4, 2)
        discount_pct = 30
        margin = price - supplier_price

        offer_type = "STANDARD"
        if margin > price * 0.5:
            offer_type = "BUNDLE"
        elif margin > price * 0.3:
            offer_type = "DISCOUNT"

        return {
            "headline": angle.hook,
            "offer_type": offer_type,
            "primary_price": discount_price,
            "compare_at_price": compare_at,
            "discount_percentage": discount_pct,
            "bundle_quantity": 2 if offer_type == "BUNDLE" else None,
            "free_shipping": True,
            "cash_on_delivery": campaign.target_country in ["SA", "AE", "EG", "IN", "BR", "MX"],
            "guarantee_days": 30,
            "urgency_text": "Limited time offer - don't miss out!",
            "scarcity_text": "Only a few left in stock - order now!",
            "bonus_text": f"Order today and get free shipping to {campaign.target_country}!",
        }

    async def generate_landing(self, product, angle, analysis) -> Dict[str, Any]:
        name = product.name
        headline = angle.hook
        subheadline = angle.main_promise
        price = product.selling_price or 29.99
        discount_price = round(price * 0.7, 2)

        sections = self._build_sections(name, headline, subheadline, price, discount_price, angle, None)

        slug = name.lower().replace(" ", "-").replace("'", "")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")[:50]

        return {
            "title": f"{name} - Official Store",
            "slug": slug,
            "sections": sections,
        }

    async def generate_landing_for_campaign(self, product, campaign, angle, analysis, offer) -> Dict[str, Any]:
        name = product.name
        headline = angle.hook
        subheadline = angle.main_promise
        price = campaign.selling_price or product.selling_price or 29.99
        discount_price = offer.primary_price if offer else round(price * 0.7, 2)

        sections = self._build_sections(name, headline, subheadline, price, discount_price, angle, offer)

        slug = name.lower().replace(" ", "-").replace("'", "")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")[:50]

        return {
            "title": f"{name} - Official Store",
            "slug": slug,
            "sections": sections,
        }

    def _build_sections(self, name, headline, subheadline, price, discount_price, angle, offer):
        bonus_text = ""
        urgency_text = "Limited time offer - don't miss out"
        scarcity_text = "Only a few left in stock - order now!"
        guarantee_days = 30
        free_shipping = True
        cash_on_delivery = False

        if offer:
            bonus_text = offer.bonus_text or ""
            urgency_text = offer.urgency_text or urgency_text
            scarcity_text = offer.scarcity_text if hasattr(offer, "scarcity_text") else scarcity_text
            if hasattr(offer, "scarcity_text"):
                scarcity_text = offer.scarcity_text or scarcity_text
            guarantee_days = offer.guarantee_days or 30
            free_shipping = offer.free_shipping if hasattr(offer, "free_shipping") else True
            cash_on_delivery = offer.cash_on_delivery if hasattr(offer, "cash_on_delivery") else False

        cod_note = " • Cash on Delivery available" if cash_on_delivery else ""

        sections = [
            {
                "section_type": "HERO",
                "content": {
                    "headline": headline,
                    "subheadline": subheadline,
                    "cta_text": "Get yours today",
                    "image_url": None,
                },
            },
            {
                "section_type": "PROBLEM",
                "content": {
                    "title": "The Problem",
                    "description": angle.pain_point,
                    "items": [
                        "Most solutions are expensive and time-consuming",
                        "You've tried other products that didn't work",
                        "It only gets worse if you ignore it",
                    ],
                },
            },
            {
                "section_type": "BENEFITS",
                "content": {
                    "title": f"Why {name}",
                    "items": [
                        {"title": "Fast Results", "description": "See the difference in minutes, not hours.", "icon": "zap"},
                        {"title": "Premium Quality", "description": "Built to last with high-quality materials.", "icon": "star"},
                        {"title": "Easy to Use", "description": "No complicated setup. Works right out of the box.", "icon": "check"},
                    ],
                },
            },
            {
                "section_type": "PRODUCT_SHOWCASE",
                "content": {
                    "title": f"Introducing the {name}",
                    "description": angle.description,
                    "features": [
                        "Compact and portable design",
                        "Powerful performance",
                        "Easy to clean and maintain",
                    ],
                },
            },
            {
                "section_type": "HOW_IT_WORKS",
                "content": {
                    "title": "How it works",
                    "steps": [
                        {"step": 1, "title": "Unbox", "description": "Your product arrives ready to use."},
                        {"step": 2, "title": "Use", "description": "Follow the simple instructions."},
                        {"step": 3, "title": "Enjoy", "description": "Experience the difference immediately."},
                    ],
                },
            },
            {
                "section_type": "BEFORE_AFTER",
                "content": {
                    "title": "The transformation",
                    "before": "Constant frustration trying to solve this problem with ineffective solutions.",
                    "after": "A clean, effortless solution that works every single time.",
                },
            },
            {
                "section_type": "SOCIAL_PROOF",
                "content": {
                    "title": "What our customers say",
                    "testimonials": [
                        {"name": "Sarah M.", "text": "This changed everything for me. Highly recommend!", "rating": 5},
                        {"name": "James R.", "text": "Best purchase I've made this year. Worth every penny.", "rating": 5},
                        {"name": "Maria L.", "text": "I bought one for myself and then two more for gifts.", "rating": 5},
                    ],
                },
            },
            {
                "section_type": "OFFER",
                "content": {
                    "title": "Special Launch Offer",
                    "original_price": str(price),
                    "discount_price": str(discount_price),
                    "savings": str(round(price - discount_price, 2)),
                    "bonus": bonus_text or "Free shipping on all orders",
                    "urgency": urgency_text,
                    "scarcity": scarcity_text,
                },
            },
            {
                "section_type": "GUARANTEE",
                "content": {
                    "title": f"{guarantee_days}-Day Money-Back Guarantee",
                    "description": f"Try it risk-free for {guarantee_days} days. If you're not completely satisfied, we'll refund every penny. No questions asked.",
                    "badge": "100% Satisfaction Guaranteed",
                },
            },
            {
                "section_type": "FAQ",
                "content": {
                    "title": "Frequently Asked Questions",
                    "items": [
                        {"question": "How long does shipping take?", "answer": "Standard shipping takes 3-5 business days within the US."},
                        {"question": "What is your return policy?", "answer": f"We offer a full {guarantee_days}-day money-back guarantee, no questions asked."},
                        {"question": "Is there a warranty?", "answer": "Yes, all products come with a 1-year manufacturer warranty."},
                    ],
                },
            },
            {
                "section_type": "FINAL_CTA",
                "content": {
                    "headline": f"Ready to try the {name}?",
                    "subheadline": "Join thousands of happy customers today.",
                    "cta_text": f"Order now for ${discount_price}",
                    "guarantee_text": f"{guarantee_days}-day money-back guarantee • Free shipping{cod_note}",
                },
            },
        ]

        return sections

    async def regenerate_landing_section(self, section_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "section_type": section_type,
            "content": context.get("content", {}),
        }

    async def analyze_campaign_performance(
        self,
        campaign,
        metrics: Dict[str, Any],
        variants: List[Dict[str, Any]],
        angles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        sessions = metrics.get("sessions", 0)
        purchases = metrics.get("purchases", 0)
        revenue = metrics.get("revenue", 0)
        cvr = metrics.get("conversion_rate", 0)
        aov = metrics.get("aov", 0)

        # Analyze variant performance
        winning_pattern = None
        if variants and len(variants) >= 2:
            sorted_variants = sorted(variants, key=lambda x: x.get("conversion_rate", 0), reverse=True)
            if sorted_variants[0]["conversion_rate"] > sorted_variants[1]["conversion_rate"]:
                winning_pattern = f"Variant {sorted_variants[0].get('variant_name', 'A')} shows stronger performance with {sorted_variants[0]['conversion_rate']:.1%} CVR vs {sorted_variants[1]['conversion_rate']:.1%} CVR"

        # Identify weak points
        weak_points = []
        if cvr < 0.02:
            weak_points.append("Conversion rate is below 2% - landing page or offer may need improvement")
        if metrics.get("cta_clicks", 0) > 0 and metrics.get("add_to_carts", 0) / max(metrics.get("cta_clicks", 1), 1) < 0.3:
            weak_points.append("Low add-to-cart rate after CTA click - product page or offer presentation may need work")
        if aov < 25:
            weak_points.append("Average order value is low - consider bundling or upsell strategies")

        # Recommended actions
        recommended_actions = []
        if cvr < 0.02:
            recommended_actions.append("Test a more compelling headline or hero image")
        if metrics.get("ctr", 0) < 0.1:
            recommended_actions.append("Improve CTA visibility and copy")
        if not weak_points:
            recommended_actions.append("Consider testing a new angle to find additional winning patterns")

        # Next test recommendation
        next_test_type = "ANGLE_TEST"
        next_test_hypothesis = "Test a different selling angle against the current control to find stronger messaging"

        if cvr < 0.015:
            next_test_type = "HEADLINE_TEST"
            next_test_hypothesis = "Low conversion suggests the headline may not be resonating - test a problem-focused vs benefit-focused approach"
        elif aov > 50 and cvr < 0.02:
            next_test_type = "OFFER_TEST"
            next_test_hypothesis = "High AOV with low conversion suggests price sensitivity - test a discount or bundle offer"

        return {
            "summary": f"Campaign '{campaign.name}' has generated {sessions} sessions with {purchases} purchases (${revenue:.2f} revenue). Conversion rate is {cvr:.2%} with an AOV of ${aov:.2f}. {'Winning pattern identified: ' + winning_pattern if winning_pattern else 'No clear winner yet - more data needed.'}",
            "winning_pattern": winning_pattern,
            "weak_points": weak_points,
            "recommended_actions": recommended_actions,
            "next_test_type": next_test_type,
            "next_test_hypothesis": next_test_hypothesis,
            "confidence": 0.75 if sessions > 200 else 0.5,
        }

    async def generate_campaign_brief(
        self,
        product,
        campaign,
        knowledge_context: str,
    ) -> Dict[str, Any]:
        product_name = getattr(product, "name", "Product")
        campaign_name = getattr(campaign, "name", "Campaign") if campaign else "Campaign"
        description = getattr(product, "description", "") or ""

        target_audience = (
            f"Health-conscious adults aged 25-55 interested in {product_name.lower()}. "
            "Primarily US-based shoppers who value quality and results."
        )
        key_benefits = (
            f"High-quality {product_name.lower()} at competitive price. "
            "Fast shipping, 30-day money-back guarantee, trusted by thousands of customers."
        )
        positioning = (
            f"{product_name} solves a real problem for people looking for reliable solutions. "
            "Position as the premium yet affordable choice in the market."
        )

        if knowledge_context:
            target_audience += " Audience insights derived from uploaded knowledge sources."
            positioning += " Positioning informed by customer feedback and competitive analysis."

        return {
            "product_summary": f"{product_name}: {description[:200]}" if description else product_name,
            "target_audience": target_audience,
            "key_benefits": key_benefits,
            "tone_of_voice": "Confident, friendly, and solution-oriented",
            "pricing_strategy": "Competitive pricing with emphasis on value and risk-free guarantee",
            "positioning": positioning,
        }
